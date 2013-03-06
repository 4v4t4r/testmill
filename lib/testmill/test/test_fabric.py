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

import time
import mock
from nose import SkipTest
from fabric import api as fab
from fabric.state import output

from testmill import fabric, cache, compat, util
from testmill.state import env
from testmill.test import *


@systemtest
class TestFabric(TestSuite):
    """Test the testmill.fabric module."""

    @classmethod
    def setup_class(cls):
        fab.env.ravello_api_user = testenv.username
        fab.env.ravello_api_password = testenv.password
        testenv.app_name = None
        testenv.bp_name = None
        testenv.app_name_bp = None

    def _test_appdef(self, app, isblueprint=False):
        assert isinstance(app, dict)
        assert 'name' in app
        assert isinstance(app['name'], compat.str)
        assert 'description' in app
        assert isinstance(app['description'], compat.str)
        if not isblueprint:
            assert 'state' in app
            assert isinstance(app['state'], compat.str)
            if app['state'] != 'DRAFT':
                assert 'cloud' in app
                assert isinstance(app['cloud'], compat.str)
                assert 'region' in app
                assert isinstance(app['region'], compat.str)
        assert 'vms' in app
        assert isinstance(app['vms'], list)
        for vm in app['vms']:
            assert isinstance(vm, dict)
            assert 'name' in vm
            assert isinstance(vm['name'], compat.str)
            assert 'description' in vm
            assert isinstance(vm['description'], compat.str)
            assert 'memory' in vm
            assert isinstance(vm['memory'], int)
            assert 'smp' in vm
            assert isinstance(vm['smp'], int)
            if not isblueprint and app['state'] != 'DRAFT':
                assert 'ip' in vm
                assert isinstance(vm['ip'], compat.str)
                assert 'state' in vm
                assert isinstance(vm['state'], compat.str)
            assert 'services' in vm
            assert isinstance(vm['services'], list)
            for svc in vm['services']:
                assert isinstance(svc, dict)
                assert 'name' in svc
                assert isinstance(svc['name'], compat.str)
                assert 'port' in svc
                assert isinstance(svc['port'], int)

    def test_aa_create_application(self):
        vms = [{'name': 'vm1', 'image': 'ubuntu1204'},
               {'name': 'vm2', 'image': 'ubuntu1204'}]
        name = fabric.new_application_name('test')
        app = fabric.create_application(name, vms=vms)
        self._test_appdef(app)
        assert app['name'] == name
        assert app['description'] == ''
        assert app['state'] == 'STARTED'
        assert len(app['vms']) == 2
        for vm in app['vms']:
            assert vm['name'] in ('vm1', 'vm2')
            assert len(vm['services']) == 1
            assert vm['services'][0] == { 'name': 'ssh', 'port': 22 }
        testenv.app_name = name

    def test_ab_stop_application(self):
        if not testenv.app_name:
            raise SkipTest('test_create_application failed')
        name = testenv.app_name
        app = fabric.get_application(name)
        if app['state'] != 'STARTED':
            raise SkipTest('test_create_application failed')
        fabric.stop_application(name, wait=True)
        app = fabric.get_application(name)
        assert app['state'] == 'STOPPED'

    def test_ac_create_blueprint(self):
        if not testenv.app_name:
            raise SkipTest('test_create_application failed')
        appname = testenv.app_name
        bp = fabric.create_blueprint(appname)
        # XXX: aplication will be locked for just a little more. Sleep here
        # to prevent test_start_application from failing.
        time.sleep(60)
        self._test_appdef(bp, isblueprint=True)
        assert appname in bp['name']
        assert len(bp['vms']) == 2
        for vm in bp['vms']:
            assert vm['name'] in ('vm1', 'vm2')
            assert len(vm['services']) == 1
            assert vm['services'][0] == { 'name': 'ssh', 'port': 22 }
        testenv.bp_name = bp['name']

    def test_ad_start_application(self):
        if not testenv.app_name:
            raise SkipTest('test_create_application failed')
        name = testenv.app_name
        app = fabric.get_application(name)
        if app['state'] != 'STOPPED':
            raise SkipTest('test_stop_application failed')
        fabric.start_application(name, wait=True)
        app = fabric.get_application(name)
        assert app['state'] == 'STARTED'

    def test_ae_create_application_from_blueprint(self):
        if not testenv.bp_name:
            raise SkipTest('test_create_blueprint failed')
        bpname = testenv.bp_name
        app = fabric.create_application(blueprint=bpname)
        self._test_appdef(app)
        assert bpname in app['name']
        assert app['description'] == ''
        assert app['state'] == 'STARTED'
        assert len(app['vms']) == 2
        for vm in app['vms']:
            assert vm['name'] in ('vm1', 'vm2')
            assert len(vm['services']) == 1
            assert vm['services'][0] == { 'name': 'ssh', 'port': 22 }
        testenv.app_name_bp = app['name']

    def test_new_application_name(self):
        name = fabric.new_application_name()
        assert len(name) > 0
        assert isinstance(name, compat.str)
        name2 = fabric.new_application_name()
        assert name == name2  # app not created yet
        names = [app['name'] for app in cache.get_applications()]
        assert name not in names
        name = fabric.new_application_name('foo')
        assert 'foo' in name
        assert name not in names

    def test_get_application(self):
        if not testenv.app_name:
            raise SkipTest('test_create_application failed')
        app = fabric.get_application(testenv.app_name)
        self._test_appdef(app)

    def test_get_nonexistent_application(self):
        name = fabric.new_application_name()
        app = fabric.get_application(name)
        assert app is None

    def test_get_applications(self):
        if not testenv.app_name:
            raise SkipTest('test_create_application failed')
        found = False
        apps = fabric.get_applications()
        for app in apps:
            self._test_appdef(app)
            if app['name'] == testenv.app_name:
                found = True
        assert found is True

    def test_new_blueprint_name(self):
        name1 = fabric.new_blueprint_name()
        assert len(name1) > 0
        assert isinstance(name1, compat.str)
        name2 = fabric.new_blueprint_name()
        assert name1 == name2  # app not created yet
        names = [app['name'] for app in cache.get_blueprints()]
        assert name1 not in names
        name = fabric.new_blueprint_name('foo')
        assert 'foo' in name
        assert name not in names

    def test_get_blueprint(self):
        if not testenv.bp_name:
            raise SkipTest('test_create_blueprint failed')
        bp = fabric.get_blueprint(testenv.bp_name)
        self._test_appdef(bp, isblueprint=True)

    def test_get_nonexistent_blueprint(self):
        name = fabric.new_blueprint_name()
        bp = fabric.get_blueprint(name)
        assert bp is None

    def test_get_blueprints(self):
        if not testenv.bp_name:
            raise SkipTest('test_create_blueprint failed')
        found = False
        bps = fabric.get_blueprints()
        for bp in bps:
            self._test_appdef(bp, isblueprint=True)
            if bp['name'] == testenv.bp_name:
                found = True
        assert found is True
    
    def test_lookup(self):
        if not testenv.app_name:
            raise SkipTest('test_create_application failed')
        app = fabric.get_application(testenv.app_name)
        name = app['name']
        vms = [vm['name'] for vm in app['vms']]
        addrs = [vm['ip'] for vm in app['vms']]
        lut = dict(zip(vms, addrs))
        hosts = fabric.lookup(name)
        assert isinstance(hosts, list)
        for host in hosts:
            assert isinstance(host, str)
        assert len(hosts) == len(vms)
        hosts = fabric.lookup(name, vms[0])
        assert isinstance(hosts, list)
        for host in hosts:
            assert isinstance(host, str)
        assert len(hosts) == 1
        hosts = fabric.lookup(name, *vms)
        assert isinstance(hosts, list)
        for host in hosts:
            assert isinstance(host, str)
        assert len(hosts) == len(vms)
        for vm in vms:
            host = fabric.lookup(name, vm)[0]
            username, addr = host.split('@')
            assert username == fab.env.ravello_user
            assert addr == lut[vm]

    def test_reverse_lookup(self):
        if not testenv.app_name:
            raise SkipTest('test_create_application failed')
        app = fabric.get_application(testenv.app_name)
        name = app['name']
        vms = [vm['name'] for vm in app['vms']]
        addrs = [vm['ip'] for vm in app['vms']]
        lut = dict(zip(addrs, vms))
        for addr in addrs:
            appname, vmname = fabric.reverse_lookup(addr)
            assert appname == name
            assert vmname == lut[addr]

    def test_only_on(self):
        d = {}
        def func1():
            d['func1'] = True
        def func2():
            d['func2'] = True
        fab.env.host = 'host1'
        with mock.patch('testmill.fabric.reverse_lookup', lambda x: ('app', x)):
            fabric.only_on('host1')(func1)()
            fabric.only_on('host2')(func2)()
        assert d == {'func1': True}

    def test_zy_remove_blueprint(self):
        if not testenv.bp_name:
            raise SkipTest('test_create_blueprint failed')
        bpname = testenv.bp_name
        fabric.remove_blueprint(bpname)
        bp = fabric.get_blueprint(bpname)
        assert bp is None

    def test_zz_remove_application(self):
        if not testenv.app_name:
            raise SkipTest('test_create_application failed')
        appname = testenv.app_name
        fabric.remove_application(appname)
        app = fabric.get_application(appname)
        assert app is None
        if not testenv.app_name_bp:
            return
        appname = testenv.app_name_bp
        fabric.remove_application(appname)
        app = fabric.get_application(appname)
        assert app is None
