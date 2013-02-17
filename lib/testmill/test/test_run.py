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

from testmill.main import main
from testmill.state import env
from testmill.test import *


class TestRun(SystemTestSuite):
    """Test the "ravtest run" command."""

    def test_run(self):
        args = get_common_args()
        args += ['run', '-m', 'platformtest.yml', 'platformtest', 'true']
        status = main(args)
        assert status == 0

    def test_run_failed(self):
        args = get_common_args()
        args += ['run', '-m', 'platformtest.yml', 'platformtest', 'false']
        status = main(args)
        assert status != 0

    def test_check_abort(self):
        args = get_common_args()
        args += ['run', '-m', 'check_abort.yml', 'platformtest']
        status = main(args)
        assert status != 0

    def test_check_abort_continue(self):
        args = get_common_args()
        args += ['run', '-m', 'check_abort.yml', 'platformtest', '-c']
        status = main(args)
        assert status == 0
