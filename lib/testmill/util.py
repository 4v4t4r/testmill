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
import sys
import stat
import yaml
import subprocess


def prettify(obj):
    """Pretty print a parsed YAML document."""
    Dumper = yaml.SafeDumper
    Dumper.ignore_aliases = lambda self, data: True
    return yaml.dump(obj, Dumper=Dumper, default_flow_style=False, indent=4)


def splitname(name, sep=':'):
    """Split a name into its base and a suffix."""
    pos = name.rfind(sep)
    if pos != -1:
        return name[:pos], name[pos+1:]
    else:
        return name, ''


def get_unused_name(name, current, sep=':'):
    """Get a new, unused name."""
    used = set()
    for obj in current:
        base, suffix = splitname(obj['name'], sep)
        if base == name and suffix:
            used.add(int(suffix))
    for i in range(1, len(used)+2):
        if i not in used:
            suffix = i
            break
    return '%s%s%d' % (name, sep, suffix)


def load_class(name):
    """Load a class specifies as package:ClassName."""
    pkg, cls = splitname(name)
    try:
        mod = __import__(pkg)
        for subpkg in pkg.split('.')[1:]:
            mod = getattr(mod, subpkg)
        cls = getattr(mod, cls)
    except (ImportError, AttributeError):
        return
    return cls


def merge(base, update):
    """Merge the dictionary `update` into `base`."""
    for key,value in update.items():
        if key not in base:
            base[key] = value
        elif isinstance(base[key], dict) and isinstance(value, dict):
            merge(base[key], value)


def get_config_dir():
    """Get the local configuration directory, creating it if it doesn't
    exist."""
    homedir = os.path.expanduser('~')
    subdir = '.ravello' if not sys.platform.startswith('win') else '_ravello'
    configdir = os.path.join(homedir, subdir)
    try:
        st = os.stat(configdir)
    except OSError:
        st = None
    if st is None:
        os.mkdir(configdir)
    elif st and not stat.S_ISDIR(st.st_mode):
        m = '{0} exists but is not a directory'
        raise OSError(m.format(configdir))
    return configdir


def which(cmd):
    """Find an executable in $PATH."""
    if os.path.isabs(cmd):
        if os.access(cmd, os.X_OK):
            return cmd
        return
    elif cmd.startswith('.'):
        cwd = os.getcwd()
        fname = os.path.normpath(os.path.join(cwd, cmd))
        if os.access(fname, os.X_OK):
            return fname
        return
    path = os.environ.get('PATH')
    if not path:
        return
    for elem in path.split(os.path.pathsep):
        fname = os.path.normpath(os.path.join(elem, cmd))
        if os.access(fname, os.X_OK):
            return fname


def find_openssh():
    """Find an installed openssh."""
    ssh = which('ssh')
    if ssh is None:
        return
    cmd = subprocess.Popen([ssh, '-V'], stderr=subprocess.PIPE)
    _, version = cmd.communicate()
    if cmd.returncode == 0 and 'OpenSSH' in version:
        return ssh

def get_devnull():
    """Return /dev/null or its equivalent."""
    if not sys.platform.startswith('win'):
        return '/dev/null'
    else:
        return 'NUL'
