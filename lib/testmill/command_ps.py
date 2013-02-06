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
import textwrap

from testmill import console, login, manifest, keypair, util


usage = textwrap.dedent("""\
        usage: ravtest [OPTION]... ps [-a]
               ravtest ps --help
        """)

description = textwrap.dedent("""\
        List Ravello applications.
        
        Normally only applications defined by the current project are shown.
        However, if --all is provided, then all applications are shown.

        The available options are:
            -a, --all
                Show applications of all projects.
        """)


def add_args(parser):
    parser.usage = usage
    parser.description = description
    parser.add_argument('-a', '--all', action='store_true')


def do_ps(args, env):
    """The "ravello ps" command."""
    if not args.all and not manifest.manifest_exists():
        error.raise_error('Project manifest ({}) not found.\n'
                          'You can still list all applications using --all.',
                          manifest.manifest_name())

    with env.let(quiet=True):
        login.default_login()
        pubkey = keypair.default_keypair()
        manif = manifest.default_manifest()

    apps = env.api.get_applications()
    apps = sorted(apps, key=lambda app: app['name'])
    console.writeln('Currently published applications:\n')

    current_project = None
    for app in apps:
        parts = app['name'].split(':')
        if len(parts) != 3:
            continue

        project, defname, suffix = parts
        if not args.all and project != manif['project']['name']:
            continue
        if args.all and current_project != project:
            console.writeln("== Project: '{}'", project)
            current_project = project

        cloud = app.get('cloud', '')
        region = app.get('regionName', '')
        started = app.get('totalStartedVms', '')
        start_time = app.get('publishStartTime')
        if started and start_time:
            now = time.time()
            start_time = util.format_timedelta(now - start_time/1000)
        else:
            start_time = ''

        console.writeln("=== Application: '{}:{}'", defname, suffix)
        what = util.plural_noun('virtual machine', started)
        console.writeln('    {} {} running'.format(started, what))
        console.writeln('    published to {}/{}'.format(cloud, region))
        if start_time:
            console.writeln('    up for: {}'.format(start_time))
        console.writeln()
