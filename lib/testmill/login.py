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

from __future__ import absolute_import

import os
from testmill import console, error, util, ravello
from testmill.state import env


def password_login():
    """Try to log in with a username and password."""
    try:
        env.api.login(env.username, env.password)
    except ravello.RavelloError as e:
        error.raise_error('Could not login to Ravello ({!s})\n'
                          'Check your username and password.', e)


def token_login():
    """Try to log in with a token."""
    cfgdir = util.get_config_dir()
    tokfile = os.path.join(cfgdir, 'api-token')
    try:
        with file(tokfile) as ftok:
            token = ftok.read()
    except IOError:
        error.raise_error('Not logged in')
    token = token.strip()
    try:
        env.api.login(token=token)
    except ravello.RavelloError as e:
        error.raise_error('Token has expired.\n'
                          "Use 'ravtest login' to refresh.")


def store_token():
    """Store the login token."""
    cfgdir = util.get_config_dir()
    tokname = os.path.join(cfgdir, 'api-token')
    with file(tokname, 'w') as ftok:
        ftok.write(env.api._cookie)
        ftok.write('\n')
    if hasattr(os, 'chmod'):
        os.chmod(tokname, 0o600)


def remove_token():
    """Remove the login token."""
    cfgdir = util.get_config_dir()
    tokname = os.path.join(cfgdir, 'api-token')
    try:
        st = os.stat(tokname)
    except OSError:
        return
    os.unlink(tokname)


def default_login():
    """Login function. Used by most sub-commands to ensure there is a valid
    connection to the Ravello API."""
    if env.username and env.password:
        password_login()
    else:
        token_login()
