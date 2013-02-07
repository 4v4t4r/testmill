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
import tempfile
import shutil
import argparse

from nose import SkipTest
from testmill import *
from testmill.state import env, _Environment
testenv = _Environment()

from testmill.test import networkblocker, sudo
from testmill.test.mock_api import MockRavelloClient

if sys.version_info[0] == 3:
    import configparser
else:
    import ConfigParser as configparser


__all__ = ('testenv', 'topdir', 'unittest', 'systemtest',
           'require_sudo', 'require_network_blocking', 'TestSuite')


_topdir = None
_testdir = None

def topdir():
    global _topdir
    if _topdir is None:
        _topdir = testdir()
        for i in range(3):
            _topdir, _ = os.path.split(_topdir)
    return _topdir

def testdir():
    global _testdir
    if _testdir is None:
        _testdir, _ = os.path.split(os.path.abspath(__file__))
    return _testdir


# Create an environment based on ~/test.cfg.

def create_environment():
    fname = os.path.join(topdir(), 'test.cfg')
    if not os.access(fname, os.R_OK):
        m = 'Tests need to be run from a checked out source repository.'
        raise RuntimeError(m)
    config = configparser.ConfigParser()
    config.read([fname])
    def config_var(name, default=None):
        try:
            return config.get('test', name)
        except (configparser.NoSectionError, configparser.NoOptionError):
            return default
    testenv.username = config_var('username')
    testenv.password = config_var('password')
    testenv.service_url = config_var('service_url') or RavelloClient.default_url
    testenv.network_blocking = config_var('network_blocking')
    testenv.sudo_password = config_var('sudo_password')
    testenv.quiet = False
    testenv.debug = True
    testenv.verbose = True
    testenv.always_confirm = True
    testenv.args = argparse.Namespace()
    testenv.api = None


# suite decorators

def unittest(obj):
    obj.unittest = 1
    return obj

def systemtest(obj):
    obj.systemtest = 1
    return obj


# method decorators

def require_sudo(func):
    def wrapped(*args, **kwds):
        if not sudo.have_sudo():
            raise SkipTest('sudo is not available')
        if testenv.sudo_password:
            if not sudo.check_sudo_password(testenv.sudo_password):
                raise SkipTest('incorrect sudo_password in test.cfg')
        elif not sudo.check_passwordless_sudo():
            raise SkipTest('sudo_password not set in test.cfg')
        return func(*args, **kwds)
    wrapped.__name__ = func.__name__
    return wrapped

def require_network_blocking(func):
    def wrapped(*args, **kwds):
        if not networkblocker.have_blocker():
            raise SkipTest('network blocking is not available')
        if not testenv.network_blocking:
            raise SkipTest('network blocking disabled in test.cfg')
        return require_sudo(func)(*args, **kwds)
    wrapped.__name__ = func.__name__
    return wrapped


# Base class for suites

class TestSuite(object):

    @classmethod
    def setup_class(cls):
        create_environment()
        cls._tmpdirs = [tempfile.mkdtemp()]
        cls._saved_stderr = sys.stderr 
        sys.stderr = sys.stdout  # Have nose capture stderr too
        if getattr(cls, 'systemtest', False):
            if not testenv.username or not testenv.password:
                m = 'Please specify username and password in test.cfg'
                raise SkipTest(m)
            api = RavelloClient()
            try:
                api.connect(testenv.service_url)
                api.login(testenv.username, testenv.password)
            except RavelloError:
                raise SkipTest('could not connect to the API')
        else:
            api = MockRavelloClient()
        testenv.api = api

    @classmethod
    def teardown_class(cls):
        testenv.api.close()
        def paranoia_check(dname):
            if '/..' in dname or '\\..' in dname:
                return False
            return '/tmp/' in dname or '\\temp\\' in dname
        for dname in cls._tmpdirs:
            # Refuse to remove directories that are not in a common temp
            # directory. This check is just for peace of mind, it should
            # never fail. In platforms with uncommon temp directories this
            # check may result in a temp directory not being cleaned up.
            if paranoia_check(dname):
                shutil.rmtree(dname)
        del cls._tmpdirs[:]
        sys.stderr = cls._saved_stderr

    def tempfile(self, contents=None):
        fd, fname = tempfile.mkstemp(dir=self._tmpdirs[0])
        if contents:
            os.write(fd, contents)
        os.close(fd)
        return fname

    def tempdir(self, contents=None):
        dname = tempfile.mkdtemp()
        self._tmpdirs.append(dname)
        def write_directory(cwd, contents):
            for name,value in contents.items():
                fullname = os.path.join(cwd, name)
                if isinstance(value, str):
                    with file(fullname, 'w') as fout:
                        fout.write(value)
                elif isinstance(value, dict):
                    os.mkdir(fullname)
                    write_directory(fullname, value)
        if contents:
            write_directory(dname, contents)
        return dname
