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
import socket
import urlparse
import threading
import pickle

from nose import SkipTest
from nose.tools import assert_raises
from testmill import RavelloClient, RavelloError
from testmill.state import env
from testmill.test import *
from testmill.test import networkblocker


@integrationtest
class TestAPI(TestSuite):
    """Test the API client."""

    def test_connect(self):
        api = RavelloClient()
        api.connect(env.service_url)
        api.close()

    def test_login(self):
        api = RavelloClient()
        api.connect(env.service_url)
        api.login(env.username, env.password)
        api.close()

    def test_login_with_invalid_password(self):
        api = RavelloClient()
        api.connect(env.service_url)
        assert_raises(RavelloError, api.login, 'nouser', env.password)
        assert_raises(RavelloError, api.login, env.username, 'invalid')

    @require_network_blocking
    def test_connect_fail(self):
        api = RavelloClient(retries=3, timeout=5)
        parsed = urlparse.urlsplit(env.service_url)
        ipaddr = socket.gethostbyname(parsed.netloc)
        with networkblocker.block_ip(ipaddr):
            assert_raises(RavelloError, api.connect, env.service_url)
        # RavelloClient.connect does not retry
        assert api._total_retries == 0

    @require_network_blocking
    def test_retry_fail(self):
        api = RavelloClient(retries=3, timeout=5)
        api.connect(env.service_url)
        api.login(env.username, env.password)
        parsed = urlparse.urlsplit(env.service_url)
        ipaddr = socket.gethostbyname(parsed.netloc)
        with networkblocker.block_ip(ipaddr):
            assert_raises(RavelloError, api.hello)
        assert api._total_retries >= 3

    @require_network_blocking
    def test_retry_succeed(self):
        api = RavelloClient(retries=4, timeout=5)
        api.connect(env.service_url)
        api.login(env.username, env.password)
        parsed = urlparse.urlsplit(env.service_url)
        ipaddr = socket.gethostbyname(parsed.netloc)
        def timed_block(secs):
            with networkblocker.block_ip(ipaddr):
                time.sleep(secs)
        thread = threading.Thread(target=timed_block, args=(12.5,))
        thread.start()
        # Target IP is blocked for 12.5 seconds. 3 retries of 5 seconds
        # each are done. So on the last retry, this should work.
        api.hello()
        thread.join()
        assert api._total_retries >= 2

    def test_pickle_not_connected(self):
        api = RavelloClient()
        pickled = pickle.dumps(api)
        api2 = pickle.loads(pickled)
        api2.connect(env.service_url)
        api2.login(env.username, env.password)
        api2.hello()
        api2.close()

    def test_pickle_connected(self):
        api = RavelloClient()
        api.connect(env.service_url)
        pickled = pickle.dumps(api)
        api2 = pickle.loads(pickled)
        api2.login(env.username, env.password)
        api2.hello()
        api2.close()

    def test_pickle_logged_in(self):
        api = RavelloClient()
        api.connect(env.service_url)
        api.login(env.username, env.password)
        pickled = pickle.dumps(api)
        api2 = pickle.loads(pickled)
        api2.hello()
        api2.close()

    def test_hello(self):
        env.api.hello()

    def test_get_image(self):
        images = env.api.get_images()
        if not images:
            raise SkipTest('No images present.')
        imgid = images[0]['id']
        image = env.api.get_image(imgid)
        assert isinstance(image, dict)
        assert 'id' in image
        assert isinstance(image['id'], int)

    def test_get_image_nonexistent(self):
        image = env.api.get_image(0)
        assert image is None

    def test_get_images(self):
        images = env.api.get_images()
        assert len(images) > 0
        assert isinstance(images, list)
        for image in images:
            assert isinstance(image, dict)
            assert 'id' in image
            assert isinstance(image['id'], int)

    def test_get_application(self):
        applications = env.api.get_applications()
        if not applications:
            raise SkipTest('No applications present.')
        appid = applications[0]['id']
        application = env.api.get_application(appid)
        assert isinstance(application, dict)
        assert 'id' in application
        assert isinstance(application['id'], int)

    def test_get_application_nonexistent(self):
        application = env.api.get_application(0)
        assert application is None

    def test_get_applications(self):
        applications = env.api.get_applications()
        assert isinstance(applications, list)
        for application in applications:
            assert isinstance(application, dict)
            assert 'id' in application
            assert isinstance(application['id'], int)

    def test_get_blueprint(self):
        blueprints = env.api.get_blueprints()
        if not blueprints:
            raise SkipTest('No blueprints present.')
        bpid = blueprints[0]['id']
        blueprint = env.api.get_blueprint(bpid)
        assert isinstance(blueprint, dict)
        assert 'id' in blueprint
        assert isinstance(blueprint['id'], int)

    def test_get_blueprint_nonexistent(self):
        blueprint = env.api.get_blueprint(0)
        assert blueprint is None

    def test_get_blueprints(self):
        blueprints = env.api.get_blueprints()
        assert isinstance(blueprints, list)
        for blueprint in blueprints:
            assert isinstance(blueprint, dict)
            assert 'id' in blueprint
            assert isinstance(blueprint['id'], int)
