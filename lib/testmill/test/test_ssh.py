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
import subprocess
from nose import SkipTest

from testmill import util
from testmill.main import main
from testmill.state import env
from testmill.test import *


@systemtest
class TestSSH(TestSuite):
    """Test the "ravtest ssh" command."""

    @classmethod
    def setup_class(cls):
        args = get_common_args()
        args += ['-m', 'platformtest.yml', 'run', 'platformtest', '--dry-run']
        with env.new():  # do not pollute global test env
            status = main(args)
            if status != 0:
                raise SkipTest('Could not start platformtest app.')
            project, defname, instance = env.application['name'].split(':')
            appname = '{0}:{1}'.format(defname, instance)
            vms = [vm['name'] for vm in env.appdef['vms']]
        cls.appname = appname
        cls.vms = vms

    def test_openssh(self):
        openssh = util.find_openssh()
        if openssh is None:
            raise SkipTest('openssh is needed for this test')
        if sys.platform.startswith('win'):
            raise SkipTest('this test is not supported on Windows')
        try:
            import pexpect
        except ImportError:
            raise SkipTest('this test requires pexpect')
        # Fire up a new Python process using pexpect. Pexpect will assign a
        # PTY, and therefore the child will use openssh.
        for vm in self.vms:
            libdir = os.path.join(testenv.topdir, 'lib')
            env = os.environ.copy()
            env['PYTHONPATH'] = libdir
            args = ['-mtestmill.main']
            args += get_common_args()
            args += ['-m', 'platformtest.yml', 'ssh', self.appname, vm]
            child = pexpect.spawn(sys.executable, args, env=env)
            # Try to get some remote output. The interaction between Unix TTYs,
            # regular expressions, python string escapes, and shell expansions
            # make the 3 lines below the path to the Zen of Unix.
            child.expect('\$')  # escape '$' regex special
            child.send("echo 'Hello from remote!'\n")  # escape ! history expn
            # Skip echo, TTY changed '\n' to '\r\n', and literal \ + r and 
            # \ + n to match \r\n.
            child.expect(r'remote!\r\n')  # note: without ' so not the echo
            child.send('exit\n')
            child.expect([pexpect.EOF, pexpect.TIMEOUT])

    def test_paramiko(self):
        # Subprocess will fire up the child without a PTY, and therefore the
        # child will elect to use Paramiko instead of openssh.
        for vm in self.vms:
            libdir = os.path.join(testenv.topdir, 'lib')
            env = os.environ.copy()
            env['PYTHONPATH'] = libdir
            command =  [sys.executable, '-mtestmill.main']
            command += get_common_args()
            command += ['-m', 'platformtest.yml', 'ssh', self.appname, vm]
            child = subprocess.Popen(command, env=env, stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            script = "echo 'Hello from remote!'\nexit\n"
            stdout, stderr = child.communicate(script)
            # Note: without a TTY, \n stays \n. Output is still echoed. We
            # can distinguish between the echo'd command and the actual output
            # because the output does not contain a closing single quote (that
            # was escaped away by the remote bash.
            assert 'Hello from remote!\n' in stdout
