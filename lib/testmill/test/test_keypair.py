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
from nose.tools import assert_raises

import stat
from testmill.test import *
from testmill import keypair, util


@integrationtest
class TestKeypair(TestSuite):

    def test_create_local_keypair(self):
        if not util.which('ssh-keygen'):
            raise SkipTest('This test requires ssh-keygen.')
        tmphome = tempdir()
        with mock.patch('testmill.util.get_config_dir', lambda: tmphome):
            keypair.create_keypair()
        privkey = os.path.join(tmphome, 'id_ravello')
        pubkey = os.path.join(tmphome, 'id_ravello.pub')
        st = os.stat(privkey)
        assert stat.S_ISREG(st.st_mode)
        assert st.st_size > 0
        st = os.stat(pubkey)
        assert stat.S_ISREG(st.st_mode)
        assert st.st_size > 0

    def test_create_keypair_with_api(self):
        tmphome = tempdir()
        with mock.patch('testmill.util.get_config_dir', lambda: tmphome):
            with environ(PATH=''):
                assert not util.which('ssh-keygen')
                keypair.create_keypair()
        privkey = os.path.join(tmphome, 'id_ravello')
        pubkey = os.path.join(tmphome, 'id_ravello.pub')
        st = os.stat(privkey)
        assert stat.S_ISREG(st.st_mode)
        assert st.st_size > 0
        st = os.stat(pubkey)
        assert stat.S_ISREG(st.st_mode)
        assert st.st_size > 0

    def test_load_keypair(self):
        tmphome = tempdir()
        with mock.patch('testmill.util.get_config_dir', lambda: tmphome):
            keypair.create_keypair()
            pubkey = keypair.load_keypair()
        assert 'id' in pubkey
        assert 'name' in pubkey
