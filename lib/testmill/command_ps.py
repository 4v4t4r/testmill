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

from testmill import (console, login, manifest, keypair, util, cache,
                      inflect, application)


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
    parser.add_argument('-f', '--full', action='store_true')


def do_ps(args, env):
    """The "ravello ps" command."""
    with env.let(quiet=True):
        login.default_login()
        pubkey = keypair.default_keypair()

    if manifest.manifest_exists():
        with env.let(quiet=True):
            manif = manifest.default_manifest()
    else:
        manif = None

    if manif is None and not args.all:
        error.raise_error('Project manifest ({0}) not found.\n'
                          'Use `ravtest ps --all` to list all applications.',
                          manifest.manifest_name())
    if args.all:
        project = None
    else:
        project = manif['project']['name']
        console.info('Project name is `{0}`.', project)
    apps = cache.get_applications(project)
    apps = sorted(apps, key=lambda app: app['name'])
    console.writeln('Currently published applications:\n')

    current_project = None
    for app in apps:
        parts = app['name'].split(':')
        if parts[0] != project and not args.all:
            continue
        if args.all and current_project != parts[0]:
            console.writeln("== Project: `{0}`", parts[0])
            current_project = parts[0]
        if args.full:
            app = cache.get_full_application(app['id'])

        cloud = app.get('cloud', '')
        region = app.get('regionName', '')
        started = app.get('totalStartedVms', '')
        start_time = app.get('publishStartTime')
        if started and start_time:
            now = time.time()
            start_time = util.format_timedelta(now - start_time/1000)
        else:
            start_time = ''
        if args.full:
            vms = [ vm['name'] for vm in application.get_vms(app) ]
            vms = '`{0}`'.format('`, `'.join(vms))

        console.writeln('=== Application: `{0}:{1}`', parts[1], parts[2])
        what = inflect.plural_noun('VM', started)
        console.writeln('    {0} {1} running', started, what)
        console.writeln('    published to {0}/{1}', cloud, region)
        if start_time:
            console.writeln('    up for: {0}', start_time)
        if args.full:
            console.writeln('    VMs: {0}', vms)
        console.writeln()
