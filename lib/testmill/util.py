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

from testmill import inflect


def prettify(obj):
    """Pretty print a parsed YAML document."""
    Dumper = yaml.SafeDumper
    Dumper.ignore_aliases = lambda self, data: True
    return yaml.dump(obj, Dumper=Dumper, default_flow_style=False,
                     indent=4, width=500)


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
    pkg, cls = splitname(name, '.')
    try:
        mod = __import__(pkg)
        for subpkg in pkg.split('.')[1:]:
            mod = getattr(mod, subpkg)
        cls = getattr(mod, cls)
    except (ImportError, AttributeError):
        return
    return cls


def get_ravello_dir():
    """Get the Ravello directory. Either '.ravello' or '_ravello'."""
    if not sys.platform.startswith('win'):
        return '.ravello'
    else:
        return '_ravello'


def get_config_dir():
    """Get the local configuration directory, creating it if it doesn't
    exist."""
    homedir = os.path.expanduser('~')
    subdir = get_ravello_dir()
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


def get_human_readable_config_dir():
    """Return a human readable version of the configuration directory."""
    if not sys.platform.startswith('win'):
        return '~/.ravello'
    else:
        return '%HOME%\\_ravello'


_pathext = []

def _exists(fname):
    """Check if an executable exists at `fname`.

    On Windows, this takes into account the %PATHEXT% environment variable.
    """
    if not _pathext:
        _pathext.append('')
        if sys.platform.startswith('win'):
            pathext = os.environ.get('PATHEXT', '')
            _pathext.extend(pathext.split(os.path.pathsep))
    for ext in _pathext:
        if os.access(fname + ext, os.X_OK):
            return fname

def which(cmd):
    """Find an executable in $PATH."""
    if os.path.isabs(cmd):
        return _exists(cmd)
    elif cmd.startswith('.'):
        cwd = os.getcwd()
        fname = os.path.normpath(os.path.join(cwd, cmd))
        return _exists(fname)
    path = os.environ.get('PATH')
    if not path:
        return
    for elem in path.split(os.path.pathsep):
        fname = os.path.normpath(os.path.join(elem, cmd))
        expn = _exists(fname)
        if expn:
            return expn


def find_openssh():
    """Find an installed openssh."""
    ssh = which('ssh')
    if ssh is None:
        return
    cmd = subprocess.Popen([ssh, '-V'], stderr=subprocess.PIPE)
    _, version = cmd.communicate()
    if cmd.returncode == 0 and 'OpenSSH' in version:
        return ssh


def shell_escape(s):
    """Shell escape the string ``s``."""
    escaped =  "'" + s.replace("'", "'\"\'\"'") + "'"
    return escaped


def format_service(vm, svc):
    addr = vm['dynamicMetadata']['externalIp']
    port = svc['portRange']
    if port == '80':
        addr = 'http://{0}/'.format(addr)
    elif port == '443':
        addr = 'https://{0}/'.format(addr)
    elif port == '8080':
        addr = 'http://{0}:{1}/'.format(addr, port)
    elif port == '8443':
        addr = 'https://{0}:{1}/'.format(addr, port)
    else:
        addr = '{0} port {1}'.format(addr, port)
    return addr


def format_timedelta(t):
    t = int(t)
    if t < 5:
        return 'just now'
    elif t < 60:
        return '< 1 minute'
    elif t < 3600:
        count = t//60
        unit = inflect.plural_noun('minute', count)
        return '{0} {1}'.format(count, unit)
    elif t < 86400:
        count = t//3600
        unit = inflect.plural_noun('hour', count)
        return '{0} {1}'.format(count, unit)
    else:
        count = t//86400
        unit = inflect.plural_noun('day', count)
        return '{0} {1}'.format(count, unit)
