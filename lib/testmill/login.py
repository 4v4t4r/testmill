# Copyright 2012 Ravello Systems, Inc.
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

import sys
import os
import os.path
import getpass
import textwrap

from . import ravello, main, util


class LoginCommand(main.SubCommand):

    name = 'login'
    usage = textwrap.dedent("""\
            usage: ravtest login
            """)
    description = textwrap.dedent("""\
            Logs into Ravello and stores a temporary token granting access
            to your account in your home directory.
            """)

    def run(self, args):
        """The "ravello login" command."""
        self.write('Enter your Ravello credentials.')
        try:
            username = self.read('Username: ')
            password = getpass.getpass('Password: ')
        except KeyboardInterrupt:
            self.stdout.write('\n')
            self.exit(0)
        api = ravello.RavelloClient()
        api.connect(args.service_url)
        try:
            api.login(username, password)
        except ravello.RavelloError as e:
            self.error('Error: login failed ({0!s})'.format(e))
            self.exit(1)
        cfgdir = util.get_config_dir()
        tokname = os.path.join(cfgdir, 'api-token')
        with file(tokname, 'w') as ftok:
            ftok.write(api._cookie)
            ftok.write('\n')
        if hasattr(os, 'chmod'):
            os.chmod(tokname, 0600)
        # note: no api.logout()!
        api.close()
        self.write('Successfully logged in.')
