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
import os.path
import sys

import fabric.api
import testmill
import testmill.ravello


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
            cls.service_url = None

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
