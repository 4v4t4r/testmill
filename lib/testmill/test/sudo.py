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

import sys
import subprocess
from testmill.test import testenv


def have_sudo():
    """This test requires sudo."""
    return not sys.platform.startswith('win')


def check_sudo_password(password):
    """Check if `password` allows us to use sudo."""
    sudo = subprocess.Popen(['sudo', '-S', '-k', 'true'],
                            stdin=subprocess.PIPE)
    sudo.communicate(password + '\n')
    return sudo.returncode == 0


def check_passwordless_sudo():
    """Check if password-less sudo is available."""
    sudo = subprocess.Popen(['sudo', '-n', 'true'],
                            stderr=subprocess.PIPE)
    sudo.communicate()
    return sudo.returncode == 0


def run_with_sudo(command):
    """Execute a command under sudo."""
    if testenv.sudo_password:
        command = ['sudo', '-S', '-k'] + command
        sudo = subprocess.Popen(command, stdin=subprocess.PIPE)
        sudo.communicate(self.sudo_password + '\n')
        returncode = sudo.returncode
    else:
        command = ['sudo'] + command
        returncode = subprocess.call(command)
    return returncode
