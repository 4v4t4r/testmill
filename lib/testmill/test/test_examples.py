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
import urllib
from nose.tools import nottest

from testmill.state import env
from testmill.main import main
from testmill.test import *


@nottest  # Skip temporarily as this test is too slow.
@systemtest
class TestExamples(TestSuite):
    """Run the examples in ~/examples.

    This tests TestMill, as well as the functionality of our default images.
    """

    def test_python(self):
        project = os.path.join(testenv.topdir, 'examples', 'python')
        os.chdir(project)
        status = main(['-u', testenv.username, '-p', testenv.password,
                       '-s', testenv.service_url, 'run', 'platformtest'])
        assert status == 0

    def test_maven(self):
        project = os.path.join(testenv.topdir, 'examples', 'maven')
        os.chdir(project)
        status = main(['-u', testenv.username, '-p', testenv.password,
                       '-s', testenv.service_url, 'run', 'platformtest'])
        assert status == 0

    def test_clojure(self):
        project = os.path.join(testenv.topdir, 'examples', 'clojure')
        os.chdir(project)
        status = main(['-u', testenv.username, '-p', testenv.password,
                       '-s', testenv.service_url, 'run', 'platformtest'])
        assert status == 0

    def test_multivm_unittest(self):
        project = os.path.join(testenv.topdir, 'examples', 'multivm')
        os.chdir(project)
        with env.new():
            status = main(['-u', testenv.username, '-p', testenv.password,
                           '-s', testenv.service_url, 'run', 'unittest'])
        assert status == 0

    def test_multivm_acceptance(self):
        project = os.path.join(testenv.topdir, 'examples', 'multivm')
        os.chdir(project)
        status = main(['-u', testenv.username, '-p', testenv.password,
                       '-s', testenv.service_url, 'run', 'acceptance'])
        for vm in env.application['vms']:
            if vm['name'] == 'web':
                break
        assert vm['name'] == 'web'
        ipaddr = vm['dynamicMetadata']['externalIp']
        for svc in vm['suppliedServices']:
            basesvc = svc['baseService']
            if basesvc['name'].startswith('http'):
                port = basesvc['portRange']
                break
        assert basesvc['name'].startswith('http')
        assert status == 0
        url = 'http://{0}:{1}/FrontPage'.format(ipaddr, port)
        fin = urllib.urlopen(url)
        page = fin.read()
        fin.close()
        assert 'Pyramid tutorial wiki' in page
