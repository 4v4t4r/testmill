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
import sys
import subprocess
import textwrap

import fabric
import fabric.api as fab

from testmill import (login, cache, keypair, manifest, application,
                      error, util, console, inflect)


usage = textwrap.dedent("""\
        usage: ravtest [OPTION]... save <application>
               revtest save --help
        """)

description = textwrap.dedent("""\
        Save an application to a blueprint.

        The application may be either running or stopped. If the application is
        running a confirmation will be required.
        """)


def add_args(parser):
    parser.usage = usage
    parser.description = description
    parser.add_argument('application')


def do_save(args, env):
    """The "ravello save" command."""

    with env.let(quiet=True):
        login.default_login()
        keypair.default_keypair()
        manif = manifest.default_manifest(required=False)

    app = application.default_application(args.application)
    appname = app['name']
    project, defname, instance = appname.split(':')

    state = application.get_application_state(app)
    if state not in ('STOPPED', 'STARTED'):
        error.raise_error('Application `{0}:{1}` is currently in state {2}.\n'
                          'Can only create blueprint when STOPPED or STARTED.',
                          defname, instance, state)

    if state == 'STARTED' and not env.always_confirm:
        console.info('Application `{0}:{1}` is currently running.',
                     defname, instance)
        result = console.confirm('Do you want to continue with a live snapshot')
        if not result:
            console.info('Not confirmed.')
            return error.EX_OK

    template = '{0}:{1}'.format(project, defname)
    bpname = util.get_unused_name(template, cache.get_blueprints())
    parts = bpname.split(':')

    console.info('Saving blueprint as `{0}:{1}`.', parts[1], parts[2])

    blueprint = env.api.create_blueprint(bpname, app)
    env.blueprint = blueprint  # for tests

    console.info('Blueprint creation process started.')
    console.info("Use 'ravtest ps -b' to monitor progress.")

    return error.EX_OK
