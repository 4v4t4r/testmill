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
import os.path
import logging
import textwrap

import fabric.colors
from . import command, ravello


class MainCommand(command.CommandBase):
    """Top-level command.
    
    This defines the command-line options that are common to every sub-command.
    """

    usage = textwrap.dedent("""\
            usage: rtm [-u <user>] [-p <password>] [-s <service_url>]
                       [-q] [-d] [-y] [-h] <command> [<args>]
                       """)
    description = textwrap.dedent("""\
        Ravello TestMill command-line interface.

        The available options are:
            -u <user>, --user <user>
                Specifies the Ravello API user name
            -p <password>, --password <password>
                Specifies the Ravello API password
            -s <service_url>, --service-url <service_url>
                Specifies the Ravello API entry point
            -q, --quiet
                Be quiet
            -d, --debug
                Show debugging information
            -y, --yes
                Do not ask for confirmation
            -h, --help
                Show help
            
        The available sub-commands are:
            login       log in to Ravello
            ps          show running applications
            run         run a remote command
        """)

    def __init__(self):
        super(MainCommand, self).__init__()
        from . import login, ps, run
        self.add_sub_command(login.LoginCommand())
        self.add_sub_command(ps.PsCommand())
        self.add_sub_command(run.RunCommand())

    def add_args(self, parser):
        super(MainCommand, self).add_args(parser)
        parser.add_argument('-u', '--user')
        parser.add_argument('-p', '--password')
        parser.add_argument('-s', '--service-url')
        parser.add_argument('-q', '--quiet', action='store_true')
        parser.add_argument('-d', '--debug', action='store_true')
        parser.add_argument('-y', '--yes', action='store_true')


class SubCommand(command.CommandBase):
    """Base class for sub-commands.

    This class provides a managed connection to the API, and caching for
    images, applications and blueprints.
    """

    def __init__(self):
        super(SubCommand, self).__init__()
        self.logger = logging.getLogger('ravello')
        self._api = None

    def error(self, message):
        # Too funky?
        super(SubCommand, self).error(fabric.colors.red(message))

    def info(self, message):
        """Write an informational message to standard output, if not in
        quiet mode."""
        if not self.args.quiet:
            self.write(message)

    def debug(self, message):
        if self.args.debug:
            self.write(message)

    def _try_password_login(self, api):
        """Try to log in with a username and password."""
        user = self.args.user
        password = self.args.password
        try:
            api.login(user, password)
        except ravello.RavelloError as e:
            self.error('Error: could not login to Ravello (%s)' % e)
            self.error('Make sure your username and password are correct.')
            self.exit(1)

    def _try_token_login(self, api):
        """Try to log in with a token."""
        homedir = os.path.expanduser('~')
        tokfile = os.path.join(homedir, '.ravello-token')
        try:
            with file(tokfile) as ftok:
                token = ftok.read()
        except IOError:
            self.error('Error: no Ravello credentials provided\n')
            self.error('Specify --user and --password, or use "ravello login\n')
            self.exit(1)
        token = token.strip()
        try:
            api.login(token=token)
        except ravello.RavelloError as e:
            self.error('Error: could not login to Ravello with token\n')
            self.error('Try "ravello login" to refresh it\n')
            self.exit(1)

    @property
    def api(self):
        if self._api is not None:
            return self._api
        args = self.args
        api = ravello.RavelloClient()
        api.connect(args.service_url)
        if args.user and args.password:
            self._try_password_login(api)
        else:
            self._try_token_login(api)
        self._api = api
        return self._api

    def load_cache(self):
        """Load a cache of all current applications and images."""
        self.images = self.api.get_images()
        self.applications = self.api.get_applications()
        self.blueprints = self.api.get_blueprints()
        self.full_applications = {}
        self.full_images = {}
        self.full_blueprints = {}

    def reload_cache(self, images=False, applications=False, blueprints=False):
        """Reload the cached applications."""
        if images:
            self.images = self.api.get_images()
        if applications:
            self.applications = self.api.get_applications()
        if blueprints:
            self.blueprints = self.api.get_blueprints()

    def get_image(self, id=None, name=None):
        """Get an image based on its id or name."""
        if not (bool(id is None) ^ bool(name is None)):
            raise ValueError('Specify either "id" or "name".')
        for img in self.images:
            if name is not None:
                if name.lower() == img['name'].lower():
                    return img
            elif id is not None:
                if img['id'] == id:
                    return img

    def get_application(self, id=None, name=None):
        """Get an application based on its id or name."""
        if not (bool(id is None) ^ bool(name is None)):
            raise ValueError('Specify either "id" or "name".')
        for app in self.applications:
            if name is not None:
                if name.lower() == app['name'].lower():
                    return app
            elif id is not None:
                if app['id'] == id:
                    return app

    def get_blueprint(self, id=None, name=None):
        """Get an application based on its id or name."""
        if not (bool(id is None) ^ bool(name is None)):
            raise ValueError('Specify either "id" or "name".')
        for bp in self.blueprints:
            if name is not None:
                if name.lower() == bp['name'].lower():
                    return bp
            elif id is not None:
                if bp['id'] == id:
                    return bp

    def get_full_image(self, id, force_reload=False):
        """Load one full image, possibly from cache."""
        img = self.full_images.get(id)
        if img is None or force_reload:
            img = self.api.get_image(id)
            self.full_images[id] = img
        return img

    def get_full_application(self, id, force_reload=False):
        """Load one full application, possibly from cache."""
        app = self.full_applications.get(id)
        if app is None or force_reload:
            app = self.api.get_application(id)
            self.full_applications[id] = app
        return app

    def get_full_blueprint(self, id, force_reload=False):
        """Load one full blueprint, possibly from cache."""
        bp = self.full_applications.get(id)
        if app is None or force_reload:
            bp = self.api.get_blueprint(id)
            self.full_blueprint[id] = bp
        return bp


def main():
    command = MainCommand()
    command.parse_args()
    command.run(command.args)

if __name__ == '__main__':
    main()
