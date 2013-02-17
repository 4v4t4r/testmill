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
import mock
from nose import SkipTest

from testmill import compat
from testmill.main import main
from testmill.state import env
from testmill.test import *


class TestPS(SystemTestSuite):
    """Test the "ravtest ps" command."""

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
        args = get_common_args()
        args += ['-m', 'platformtest.yml', 'save', appname, '-y']
        with env.new():
            status = main(args)
            if status != 0:
                raise SkipTest('Could not create blueprint.')
            project, defname, instance = env.blueprint['name'].split(':')
            bpname = '{}:{}'.format(defname, instance)
        cls.bpname = bpname

    @classmethod
    def teardown_class(cls):
        args = get_common_args()
        args += ['-m', 'platformtest.yml', '-y', 'clean', '-b']
        with env.new():
            main(args)

    def test_ps(self):
        stdout = compat.StringIO()
        args = get_common_args()
        args += ['-m', 'platformtest.yml', 'ps']
        with mock.patch('sys.stdout', stdout):
            status = main(args)
        assert status == 0
        parsed = parse_ps_output(stdout.getvalue())
        for project,app,vms in parsed:
            if project is None and app.startswith('platformtest:') \
                        and vms > 0:
                break
        else:
            assert False, 'Application not found.'

    def test_ps_a(self):
        stdout = compat.StringIO()
        args = get_common_args()
        args += ['ps', '-a']
        with mock.patch('sys.stdout', stdout):
            status = main(args)
        assert status == 0
        parsed = parse_ps_output(stdout.getvalue())
        for project,app,vms in parsed:
            if project == 'testmilltest' and app.startswith('platformtest:') \
                        and vms > 0:
                break
        else:
            assert False, 'Application not found.'

    def test_ps_b(self):
        stdout = compat.StringIO()
        args = get_common_args()
        args += ['-m', 'platformtest.yml', 'ps', '-b']
        with mock.patch('sys.stdout', stdout):
            status = main(args)
        assert status == 0
        parsed = parse_ps_output(stdout.getvalue())
        for project,bp,_ in parsed:
            if project is None and bp == self.bpname:
                break
        else:
            assert False, 'Blueprint not found.'

    def test_ps_a_b(self):
        stdout = compat.StringIO()
        args = get_common_args()
        args += ['ps', '-a', '-b']
        with mock.patch('sys.stdout', stdout):
            status = main(args)
        assert status == 0
        parsed = parse_ps_output(stdout.getvalue())
        for project,bp,_ in parsed:
            if project == 'testmilltest' and bp == self.bpname:
                break
        else:
            assert False, 'Blueprint not found.'
