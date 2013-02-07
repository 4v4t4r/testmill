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
import textwrap
from testmill import console, login, util


usage = textwrap.dedent("""\
        usage: ravtest [OPTION]... login [<username>]
               ravtest login --help
        """)

description = textwrap.dedent("""\
        Log in to the Ravello Service.
        
        A token granting temporary access to the Ravello API will be stored
        in your home directory ({config_dir}).
        """.format(config_dir=util.get_human_readable_config_dir()))


def add_args(parser):
    """Add command-line options for "ravello login"."""
    parser.usage = usage
    parser.description = description
    parser.add_argument('username', nargs='?')


def do_login(args, env):
    """The "ravello login" command."""
    username = args.username or args.user
    password = args.password
    if username is None:
        console.writeln('Enter your Ravello credentials.')
    if username is None:
        username = console.prompt('Username: ')
    if password is None:
        password = console.getpass('Password: ')
    with env.let(username=username, password=password):
        login.password_login()
        login.store_token()
    console.info('Successfully logged in.')
    return 0
