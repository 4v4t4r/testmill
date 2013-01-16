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

import os
import sys
import os.path
import subprocess

import testmill
from nose import SkipTest


# Python 2.x / 3.x compatiblity
try:
    import configparser
except ImportError:
    import ConfigParser as configparser


class UnitTest(object):

    @classmethod
    def setup_class(cls):
        path = os.path.abspath(__file__)
        for i in range(4):
            path, rest = os.path.split(path)
        fname = os.path.join(path, 'setup.py')
        if not os.access(fname, os.R_OK):
            m = 'Tests need to be run from a source repository.'
            raise RuntimeError(m)
        cls.topdir = path
        fname = os.path.join(path, 'setup.cfg')
        config = cls.config = configparser.ConfigParser()
        config.read([fname])
        try:
            cls.username = config.get('test', 'username')
            cls.password = config.get('test', 'password')
        except (configparser.NoSectionError, configparser.NoOptionError):
            m = "Specify both 'username' and 'password' under [test] in setup.cfg."
            raise RuntimeError(m)
        try:
            cls.service_url = config.get('test', 'service_url')
        except configparser.NoOptionError:
            cls.service_url = testmill.ravello.RavelloClient.default_url
        try:
            cls.sudo_password = config.get('test', 'sudo_password')
        except configparser.NoOptionError:
            cls.sudo_password = None

    def require_sudo(self):
        """This test requires sudo."""
        if sys.platform.startswith('win'):
            raise SkipTest('sudo is not available no Windows')
        if self.sudo_password:
            # If a sudo password is configured, make sure it is correct.
            sudo = subprocess.Popen(['sudo', '-S', '-k', 'true'],
                                    stdin=subprocess.PIPE)
            sudo.communicate(self.sudo_password + '\n')
            if sudo.returncode != 0:
                m = 'incorrect sudo_password under [test] in setup.cfg'
                raise SkipTest(m)
        else:
            # Otherwise, see if we are able to run sudo with a password.
            sudo = subprocess.Popen(['sudo', '-n', 'true'],
                                    stderr=subprocess.PIPE)
            sudo.communicate()
            if sudo.returncode != 0:
                m = 'no sudo_password in setup.cfg and sudo needs a password'
                raise SkipTest(m)

    def sudo(self, command):
        """Execute a command under sudo. Raise an exception on error."""
        if self.sudo_password:
            command = ['sudo', '-S', '-k'] + command
            sudo = subprocess.Popen(command, stdin=subprocess.PIPE)
            sudo.communicate(self.sudo_password + '\n')
            returncode = sudo.returncode
        else:
            command = ['sudo'] + command
            returncode = subprocess.call(command)
        if returncode != 0:
            raise subprocess.CalledProcessError(returncode, ' '.join(command))

    if sys.platform == 'darwin':

        class blocker(object):
            """Context manager that block IP traffic to a certain IP."""

            def __init__(self, suite, ipaddr):
                self.suite = suite
                self.ipaddr = ipaddr

            def __enter__(self):
                # Divert return traffic to the local discard port.
                rule = 'add 2000 divert 9 tcp from {} to any' \
                        .format(self.ipaddr)
                self.suite.sudo(['ipfw', '-q'] + rule.split())

            def __exit__(self, *exc):
                rule = 'del 2000'
                self.suite.sudo(['ipfw', '-q'] + rule.split())

    else:
        blocker = None

    def require_ip_blocking(self):
        """This test requires IP blocking."""
        if self.blocker is None:
            raise SkipTest('IP blocking is required for this test')
        self.require_sudo()

    def block_ip(self, ipaddr):
        """Return a context manager that blocks 'ipaddr'."""
        assert self.blocker is not None
        return self.blocker(self, ipaddr)


# redirect stderr to stdout to that nose will capture it
sys.stderr = sys.stdout

def mock(self, read=None, getpass=None):
    """Mock up a command for unit testing."""
    if isinstance(read, str):
        def mock_read(prompt):
            return read
        self.read = mock_read
    elif read is not None:
        self.read = read
    if isinstance(getpass, str):
        def mock_getpass(prompt):
            return getpass
        self.getpass = mock_getpass
    elif getpass is not None:
        self.getpass = getpass
    for subcmd in self.sub_commands:
        subcmd.mock(self.read, self.getpass)
    self.stderr = self.stdout

testmill.CommandBase.mock = mock


def assert_raises(exc_type, func, *args, **kwds):
    try:
        func(*args, **kwds)
    except Exception as exc:
        pass
    else:
        exc = None
    assert isinstance(exc, exc_type)
    return exc
