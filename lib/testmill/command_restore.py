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
        usage: ravtest [OPTION]... restore <blueprint>
               revtest restore --help
        """)

description = textwrap.dedent("""\
        Restore an application from a blueprint.
        """)


def add_args(parser):
    parser.usage = usage
    parser.description = description
    parser.add_argument('blueprint')


def do_restore(args, env):
    """The "ravello restore" command."""

    with env.let(quiet=True):
        login.default_login()
        keypair.default_keypair()
        manif = manifest.default_manifest(required=False)

    bpname = args.blueprint
    parts = bpname.split(':')
    if len(parts) in (1, 2) and manif is None:
        error.raise_error('No manifest found ({0}).\n'
                          'Please specify the fully qualified blueprint name.\n'
                          "Use 'ravtest ps -ba' for a list.",
                          manifest.manifest_name())
    if len(parts) in (1, 2):
        project = env.manifest['project']['name']
        console.info('Project name is `{0}`.', project)
        defname = parts[0]
        instance = parts[1] if len(parts) == 2 else None
    elif len(parts) == 3:
        project, defname, instance = parts
    else:
        error.raise_error('Illegal blueprint name: `{0}`.', appname)

    bps = cache.get_blueprints(project, defname, instance)
    if len(bps) == 0:
        error.raise_error('No instances of blueprint `{0}` exist.',
                          defname)
    elif len(bps) > 1:
        error.raise_error('Multiple instances of `{0}` exist.\n'
                          'Use `ravtest ps -b` to list the blueprints and then\n'
                          'specify the blueprint with its instance id.',
                          defname)
    bp = cache.get_full_blueprint(bps[0]['id'])
    project, defname, instance = bp['name'].split(':')

    template = '{0}:{1}'.format(project, defname)
    appname = util.get_unused_name(template, cache.get_applications())
    parts = appname.split(':')

    console.info('Restoring application as `{0}:{1}`.', parts[1], parts[2])

    app = { 'name': appname }
    app = env.api.create_application(app, bp)
    app = cache.get_full_application(app['id'])
    for vm in application.get_vms(app):
        vm.setdefault('customVmConfigurationData', {})
        vm['customVmConfigurationData']['keypair'] = env.public_key
    env.api.publish_application(app)

    console.info('Application restore process started.')
    console.info("Use 'ravtest ps' to monitor progress.")
