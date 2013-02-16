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

import mock

from testmill.main import main
from testmill.state import env
from testmill.test import *


class TestLogin(SystemTestSuite):

    def test_login(self):
        status = main(['-u', testenv.username, '-p', testenv.password,
                       '-s', testenv.service_url, 'login'])
        assert status == 0

    def test_login_prompt(self):
        with mock.patch.multiple('testmill.console',
                                 prompt=lambda *args: testenv.username,
                                 getpass=lambda *args: testenv.password):
            status = main(['-s', testenv.service_url, 'login'])
        assert status == 0

    def test_login_with_positional_username(self):
        status = main(['-p', testenv.password, '-s', testenv.service_url,
                       'login', testenv.username])
        assert status == 0

    def test_login_failed(self):
        status = main(['-u', testenv.username, '-p', 'invalid',
                       '-s', testenv.service_url, 'login'])
        assert status != 0
