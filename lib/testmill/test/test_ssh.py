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

import testmill
import testmill.test


class TestSSH(testmill.test.UnitTest):
    """Test the "ravtest ssh" command."""

    @classmethod
    def setup_class(cls):
        super(TestSSH, cls).setup_class()
        command = testmill.MainCommand()
        # Ensure a "fedora17" application is started up.
        project = os.path.join(cls.topdir, 'examples', 'nolang')
        os.chdir(project)
        status = command.main(['-u', cls.username, '-p', cls.password,
                               '-s', cls.service_url, 'run', 'true'])
        if status != 0:
            raise SkipTest('Could not start application')
        # XXX: using too much internal information here
        cls.applications = command.sub_command.applications

    def test_openssh(self):
        openssh = testmill.util.find_openssh()
        if openssh is None:
            raise SkipTest('openssh is needed for this test')
        if sys.platform.startswith('win'):
            raise SkipTest('this test is not supported on Windows')
        try:
            import pexpect
        except ImportError:
            raise SkipTest('this test requires pexpect')
        # Fire up a new Python progress using pexpect. Pexpect will assign a
        # PTY, and therefore the child will use openssh.
        assert len(self.applications) >= 4
        for app in self.applications:
            libdir = os.path.join(self.topdir, 'lib')
            args = ['-mtestmill.main', '-u', self.username, '-p', self.password,
                    '-s', self.service_url, 'ssh', app['name']]
            child = pexpect.spawn(sys.executable, args, cwd=libdir)
            # Try to get some remote output. The interaction between Unix TTYs,
            # regular expressions, python string escapes, and shell expansions
            # make the 3 lines below a path to Zen.
            child.expect('\$')  # escape '$' regex special
            child.send("echo 'Hello from remote!'\n")  # ! = history expansion
            # eat echo, TTY changed '\n' to '\r\n', and \ + r to match \r
            child.expect(r"remote!'\r\n")
            line = child.readline()
            assert line.endswith('Hello from remote!\r\n')
            child.send('exit\n')
            child.expect([pexpect.EOF, pexpect.TIMEOUT])

    def test_paramiko(self):
        # Subprocess will fire up the child without a PTY, and therefore the
        # child will elect to use Paramiko instead of openssh.
        assert len(self.applications) >= 4
        for app in self.applications:
            libdir = os.path.join(self.topdir, 'lib')
            command =  [sys.executable, '-mtestmill.main', '-u', self.username,
                        '-p', self.password, '-s', self.service_url, 'ssh',
                        app['name']]
            # Because subprocess does not allocate a TTY, SSHCommand
            child = subprocess.Popen(command, cwd=libdir,
                    stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE)
            script = "echo 'Hello from remote!'\nexit\n"
            stdout, stderr = child.communicate(script)
            # Note: without a TTY, \n stays \n. Output is still echoed. We
            # can distinguish between the echo'd command and the actualy output
            # because the output does not contain a closing single quote (that
            # was escaped away by the remote bash.
            assert 'Hello from remote!\n' in stdout
