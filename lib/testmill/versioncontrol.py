# Copyright 2012-2013 Ravello Systems, Inc.
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#    http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, print_function

import os
import re
import stat
import fnmatch
import subprocess

from testmill import error


MATCH_INVERSE = 1
MATCH_END_WITH_DIRECTORY = 2


def detect_git_repository(repodir='.'):
    """Detect if ``repodir`` is a git repository."""
    for fname in os.listdir(repodir):
        if fname == '.git':
            fullname = os.path.join(repodir, fname)
            st = os.stat(fullname)
            if stat.S_ISDIR(st.st_mode):
                return True
    return False


def parse_gitignore(fin):
    """Parse a .gitignore file. The format is described in gitignore(5).

    The result is a list of (ignore, pattern, flags) tuples. The ignore field
    indicates whether the matching sense is regular (ignore matching files,
    ignore=True) or inverted (re-include previously excluded matching files,
    ignore=False). The pattern field is a list of regular expressions, one for
    each path component in the pattern. The flags field contains a bitwise OR
    of optional flags (currently only MATCH_END_WITH_DIRECTORY).
    """
    parsed = []
    if hasattr(fin, 'readlines'):
        lines = fin.readlines()
    elif hasattr(fin, 'splitlines'):
        lines = fin.splitlines()
    else:
        raise TypeError('Expecting a file-like object or a string')

    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue

        flags = 0
        if line.startswith('!'):
            flags |= MATCH_INVERSE
            line = line[1:]
        elif line.startswith('\!'):
            line = line[1:]
        elif line.startswith('\#'):
            line = line[1:]
        line = re.sub('/+', '/', line)
        if line.startswith('/'):
            line = line[1:]
        if line.endswith('/'):
            flags |= MATCH_END_WITH_DIRECTORY
            line = line[:-1]

        pattern = [re.compile(fnmatch.translate(part))
                   for part in line.split('/')]
        parsed.append((pattern, flags))

    return parsed


def match_gitignore(path):
    """Match a path that contains .gitignore files at multiple levels.

    Git's matching algorithm is described in gitignore(5).
    """
    elem = path[-1][0]  # path = [(name, parsed_ignore_file, mode_or_ignore)]
    is_directory = stat.S_ISDIR(path[-1][2])
    if len(path) > 1:
        ignored = path[-2][2]
    else:
        ignored = False

    for i in range(len(path)):
        parsed_ignore_file = path[i][1]
        if not parsed_ignore_file:
            continue
        for pattern,flags in parsed_ignore_file:
            sense = not bool(flags & MATCH_INVERSE)

            # A pattern without a '/' matches everywhere
            if len(pattern) == 1:
                if pattern[0].match(elem):
                    if not flags & MATCH_END_WITH_DIRECTORY or is_directory:
                        ignored = sense

            # A pattern with a '/' matches from the start
            elif len(pattern) == len(path)-i:
                for j in range(len(pattern)):
                    if not pattern[j].match(path[i+j][0]):
                        break
                else:
                    if not flags & MATCH_END_WITH_DIRECTORY or is_directory:
                        ignored = sense
    return ignored


def _walk_repository(repodir, ignore_file=None, parse_ignore=None,
                    match_ignore=None, path=None, depth=0):
    """Do the actual repository walking, using repository specific parse and
    match functions.

    The `ignore_file` argument specifies the name of the repository specific
    ignore file (e.g. '.gitignore' for git).

    The `parse_ignore` argument is a function that can parse the ignore file.
    Prototype: `parse_ignore(input)` with `input` a file like object or a
    string.

    The `match_ignore` argument is a function that is used to match individual
    files and directories against a hierarchy of ignore files. Prototype:
    `match_ignore(path)` where path is a list of `(name, parsed_ignore_file,
    ignore_or_mode)`. The path contains one element per path component.
    The `name` field the name of the path component.  The `parsed_ignore_file`
    field is the parsed ignore file file for that level, if any.  The `ignore`
    field is a boolean that indicates the result of a previous `match_ignore()`
    invocation for the level. This field is set for all but the final level. In
    the final level, this field is multiplexed and instead indicates whether
    the final path component is a file or directory.
    """

    if path is None:
        path = []
    parsed_ignore_file = None

    if ignore_file is not None:
        fullname = os.path.join(repodir, ignore_file)
        try:
            st = os.stat(fullname)
        except OSError:
            pass
        else:
            if stat.S_ISREG(st.st_mode):
                with file(fullname) as fin:
                    parsed_ignore_file = parse_ignore(fin)

    path.append(None)
    contents = os.listdir(repodir)

    # For each file and directory in the tree, keep track of a path
    # containing (name, parsed_ignore, ignore) tuples for every path
    # element up till the top of the tree.

    for fname in contents:
        fullname = os.path.join(repodir, fname)
        try:
            st = os.stat(fullname)
        except OSError:
            continue

        # Always ignore the .git directory

        if fname == '.git' and stat.S_ISDIR(st.st_mode):
            continue

        if stat.S_ISREG(st.st_mode):
            path[depth] = (fname, parsed_ignore_file, st.st_mode)
            if not match_ignore or not match_ignore(path):
                yield os.path.join(*(p[0] for p in path))

        elif stat.S_ISDIR(st.st_mode):
            path[depth] = (fname, parsed_ignore_file, st.st_mode)
            ignore = match_ignore(path) if match_ignore else False
            path[depth] = (fname, parsed_ignore_file, ignore)
            path_yielded = False
            for elem in _walk_repository(fullname, ignore_file, parse_ignore,
                                         match_ignore, path, depth+1):
                if not path_yielded:
                    yield os.path.join(*(p[0] for p in path[:depth+1]))
                    path_yielded = True
                yield elem

        # Ignore anything that is not a file or directory.
    del path[-1]


def walk_git_repository(repodir='.'):
    """Walk a git repository."""
    return _walk_repository(repodir, '.gitignore', parse_gitignore,
                            match_gitignore)


def get_git_origin(repodir='.'):
    """Get the URL of the remote tracking branch "origin"."""
    git = subprocess.Popen(['git', 'remote', '-v'], cwd=repodir,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = git.communicate()
    if git.returncode != 0:
        error.raise_error("Command 'git remote' exited with status {0}.",
                          git.returncode)
    for line in stdout.splitlines():
        line = line.strip()
        name, url, direction = line.split()
        if name == 'origin' and direction == '(fetch)':
            return url


def get_git_checkout_command(url, version):
    """Get a git clone/checkout command.
    
    NOTE: slightly more complicated that "git clone" because this needs to
    support checkout out in a non-empty directory.
    """
    commands = []
    commands.append('git init .')
    commands.append('git remote add origin {0}'.format(url))
    commands.append('git fetch origin')
    commands.append('git checkout {0}'.format(version))
    return commands


def detect_type(repodir='.'):
    """Detect the type of the repository at `repodir`.

    If the type can be detected, a string identifier is returned.
    """
    for repotype in registry:
        detect = registry[repotype][0]
        if detect(repodir):
            return repotype


def walk_repository(repodir='.', repotype='auto'):
    """Walk the version control repository at `repodir`, yielding any files
    and directories that are not excluded by version-control specific exclude
    files. The order of the files and directories is always such that diretories
    precede their contents.
    
    The repository type can be passed in with the ``repotype`` parameter. If no
    repository type is provided, it is autodetected. If a ``None`` repository``
    type is passed in, all files and directories are yielded without any
    exclusions.
    """
    if repotype is None:
        return _walk_repository(repodir)
    if repotype == 'auto':
        repotype = detect_type(repodir)
        if repotype is None:
            error.raise_error('Cannot detect repository type at {0}.', repodir)
    if repotype not in registry:
        error.raise_error("Unknown repository type '{0}'.", repodir)
    walk = registry[repotype][1]
    return walk(repodir)


def get_origin(repodir='.', repotype='auto'):
    """Return the default checkout location."""
    if repotype is 'auto':
        typ = detect_type(repodir)
        if typ is None:
            error.raise_error('Unknown repository type at {0}.', repodir)
    if repotype not in registry:
        error.raise_error("Unknown repository type '{0}'.", repotype)
    get_origin = registry[repotype][2]
    return get_origin(repodir)


def get_checkout_command(url, version, repotype):
    """Return the checkout command for a repository."""
    if repotype not in registry:
        error.raise_error("Unknown repository type '{0}'.", repodir)
    get_checkout_command = registry[repotype][3]
    return get_checkout_command(url, version)


registry = {
    'git': (detect_git_repository, walk_git_repository, get_git_origin,
            get_git_checkout_command)
}
