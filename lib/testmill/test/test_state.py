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

from nose.tools import assert_raises

from testmill.state import _Environment
from testmill.test import *


class TestState(TestSuite):

    def test_set(self):
        env = _Environment()
        env.foo = 10
        assert env.foo == 10

    def test_update(self):
        env = _Environment()
        env2 = _Environment()
        env2.foo = 10
        env.update(env2)
        assert env.foo == 10

    def test_scoping_rules(self):
        env = _Environment()
        env.foo = 10
        with env.let(foo=20):
            assert env.foo == 20
            env.foo = 30  # goes to global scope
            assert env.foo == 20
        assert env.foo == 30

    def test_disallow_let_static(self):
        env = _Environment()
        env._foo = 10
        assert_raises(RuntimeError, env.let, _foo=10)
