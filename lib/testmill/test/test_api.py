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

from nose.tools import assert_raises
from testmill import RavelloClient, RavelloError
from testmill.state import env
from testmill.test import *
from testmill.test import networkblocker


@systemtest
class TestAPI(TestSuite):
    """Test the API client."""

    def test_connect(self):
        api = RavelloClient()
        api.connect(testenv.service_url)
        api.close()

    def test_login(self):
        api = RavelloClient()
        api.connect(testenv.service_url)
        api.login(testenv.username, testenv.password)
        api.close()

    def test_login_with_invalid_password(self):
        api = RavelloClient()
        api.connect(testenv.service_url)
        assert_raises(RavelloError, api.login, 'nouser', testenv.password)
        assert_raises(RavelloError, api.login, testenv.username, 'invalid')

    @require_network_blocking
    def test_connect_fail(self):
        api = RavelloClient(retries=3, timeout=5)
        parsed = urlparse.urlsplit(testenv.service_url)
        ipaddr = socket.gethostbyname(parsed.netloc)
        with networkblocker.block_ip(ipaddr):
            assert_raises(RavelloError, api.connect, testenv.service_url)
        # RavelloClient.connect does not retry
        assert api._total_retries == 0

    @require_network_blocking
    def test_retry_fail(self):
        api = RavelloClient(retries=3, timeout=5)
        api.connect(testenv.service_url)
        api.login(testenv.username, testenv.password)
        parsed = urlparse.urlsplit(testenv.service_url)
        ipaddr = socket.gethostbyname(parsed.netloc)
        with networkblocker.block_ip(ipaddr):
            assert_raises(RavelloError, api.hello)
        assert api._total_retries >= 3

    @require_network_blocking
    def test_retry_succeed(self):
        api = RavelloClient(retries=4, timeout=5)
        api.connect(testenv.service_url)
        api.login(testenv.username, testenv.password)
        parsed = urlparse.urlsplit(testenv.service_url)
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
        api2.connect(testenv.service_url)
        api2.login(testenv.username, testenv.password)
        api2.hello()
        api2.close()

    def test_pickle_connected(self):
        api = RavelloClient()
        api.connect(testenv.service_url)
        pickled = pickle.dumps(api)
        api2 = pickle.loads(pickled)
        api2.login(testenv.username, testenv.password)
        api2.hello()
        api2.close()

    def test_pickle_logged_in(self):
        api = RavelloClient()
        api.connect(testenv.service_url)
        api.login(testenv.username, testenv.password)
        pickled = pickle.dumps(api)
        api2 = pickle.loads(pickled)
        api2.hello()
        api2.close()

    def test_hello(self):
        testenv.api.hello()

    def test_get_images(self):
        images = testenv.api.get_images()
        assert len(images) > 0
        assert isinstance(images, list)
        for image in images:
            assert isinstance(image, dict)
            assert 'id' in image
            assert isinstance(image['id'], int)
            assert 'name' in image
            assert isinstance(image['name'], (str, unicode))
