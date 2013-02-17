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
from nose import SkipTest

from testmill.main import main
from testmill.state import env
from testmill.test import *


class TestSave(SystemTestSuite):
    """Test the "ravtest save" command."""

    @classmethod
    def setup_class(cls):
        args = get_common_args()
        args += ['-m', 'platformtest.yml', 'run', 'platformtest', '--dry-run']
        with env.new():  # do not pollute test-global env
            status = main(args)
            if status != 0:
                raise SkipTest('Could not start platformtest app.')
            project, defname, instance = env.application['name'].split(':')
            appname = '{}:{}'.format(defname, instance)
            vms = [vm['name'] for vm in env.appdef['vms']]
        cls.appname = appname
        cls.vms = vms

    def test_save(self):
        args = get_common_args()
        args += ['-m', 'platformtest.yml', 'save', self.appname, '-y']
        status = main(args)
        assert status == 0
        # Re-use the API that main() has created.
        blueprint = env.api.get_blueprint(env.blueprint['id'])
        assert blueprint is not None
        assert blueprint['id'] == env.blueprint['id']
        assert blueprint['name'] == env.blueprint['name']
        assert blueprint['state'] in ('PENDING', 'SAVING', 'DONE')
        assert len(blueprint['applicationLayer']['vm']) == len(self.vms)

    @classmethod
    def teardown_class(cls):
        args = get_common_args()
        args += ['-m', 'platformtest.yml', '-y', 'clean', '-b']
        with env.new():
            main(args)
