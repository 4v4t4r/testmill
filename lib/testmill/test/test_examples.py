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
import testmill
import testmill.test


class TestExamples(testmill.test.UnitTest):
    """Run the examples in ~/examples.

    This tests TestMill, as well as the functionality of our default images.
    """

    def test_python(self):
        command = testmill.MainCommand()
        project = os.path.join(self.topdir, 'examples', 'python')
        os.chdir(project)
        status = command.main(['-u', self.username, '-p', self.password,
                               '-s', self.service_url, 'run'])
        assert status == 0

    def test_java_maven(self):
        command = testmill.MainCommand()
        project = os.path.join(self.topdir, 'examples', 'java_maven')
        os.chdir(project)
        status = command.main(['-u', self.username, '-p', self.password,
                               '-s', self.service_url, 'run'])
        assert status == 0
