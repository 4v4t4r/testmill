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

import testmill
import testmill.test
from testmill.test import assert_raises
from testmill.ravello import RavelloClient, RavelloError

from nose import SkipTest


class TestBaseAPI(testmill.test.UnitTest):
    """Test the API client."""

    def test_connect(self):
        api = RavelloClient()
        api.connect(self.service_url)
        api.close()

    def test_login(self):
        api = RavelloClient()
        api.connect(self.service_url)
        api.login(self.username, self.password)
        api.close()

    def test_login_with_invalid_password(self):
        api = RavelloClient()
        api.connect(self.service_url)
        assert_raises(RavelloError, api.login, 'nouser', self.password)
        assert_raises(RavelloError, api.login, self.username, 'invalid')

    def test_connect_fail(self):
        self.require_ip_blocking()
        api = RavelloClient(retries=3, timeout=5)
        parsed = urlparse.urlsplit(self.service_url)
        ipaddr = socket.gethostbyname(parsed.netloc)
        with self.block_ip(ipaddr):
            assert_raises(RavelloError, api.connect, self.service_url)
        # RavelloClient.connect does not retry
        assert api._total_retries == 0

    def test_retry_fail(self):
        self.require_ip_blocking()
        api = RavelloClient(retries=3, timeout=5)
        api.connect(self.service_url)
        api.login(self.username, self.password)
        parsed = urlparse.urlsplit(self.service_url)
        ipaddr = socket.gethostbyname(parsed.netloc)
        with self.block_ip(ipaddr):
            assert_raises(RavelloError, api.hello)
        assert api._total_retries >= 3

    def test_retry_succeed(self):
        self.require_ip_blocking()
        api = RavelloClient(retries=4, timeout=5)
        api.connect(self.service_url)
        api.login(self.username, self.password)
        parsed = urlparse.urlsplit(self.service_url)
        ipaddr = socket.gethostbyname(parsed.netloc)
        def timed_block(secs):
            with self.block_ip(ipaddr):
                time.sleep(secs)
        thread = threading.Thread(target=timed_block, args=(12.5,))
        thread.start()
        # Target IP is blocked for 12.5 seconds. 3 retries of 5 seconds
        # each are done. So on the last retry, this should work.
        api.hello()
        thread.join()
        assert api._total_retries >= 2


class TestAPI(testmill.test.UnitTest):
    """Ravello API tests."""

    @classmethod
    def setup_class(cls):
        super(TestAPI, cls).setup_class()
        api = RavelloClient()
        try:
            api.connect(cls.service_url)
            api.login(cls.username, cls.password)
        except RavelloError:
            raise SkipTest('could not connect to the API')
        cls.api = api

    def test_hello(self):
        self.api.hello()
