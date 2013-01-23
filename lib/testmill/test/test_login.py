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

import testmill
import testmill.test


class TestLogin(testmill.test.UnitTest):

    def test_login(self):
        command = testmill.MainCommand()
        status = command.main(['-p', self.password, '-s', self.service_url,
                               'login', self.username])
        assert status == 0

    def test_failed_login(self):
        command = testmill.MainCommand()
        status = command.main(['-u', self.username, '-p', 'invalid',
                               '-s', self.service_url, 'login'])
        assert status != 0
