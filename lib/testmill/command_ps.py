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
                      inflect, application, error)


usage = textwrap.dedent("""\
        usage: ravtest [OPTION]... ps [-a] [-f] [-b]
               ravtest ps --help
        """)

description = textwrap.dedent("""\
        List Ravello applications.
        
        Normally only applications defined by the current project are shown.
        However, if --all is provided, then all applications are shown.

        The available options are:
            -a, --all
                Show applications of all projects.
            -f, --full
                Show more details for each application.
            -b, --blueprint
                Show blueprints instead of applications.
        """)


def add_args(parser):
    parser.usage = usage
    parser.description = description
    parser.add_argument('-a', '--all', action='store_true')
    parser.add_argument('-f', '--full', action='store_true')
    parser.add_argument('-b', '--blueprint', action='store_true')


def do_ps(args, env):
    """The "ravello ps" command."""
    with env.let(quiet=True):
        login.default_login()
        pubkey = keypair.default_keypair()
        manif = manifest.default_manifest(required=False)

    if manif is None and not args.all:
        error.raise_error('Project manifest ({0}) not found.\n'
                          "Use 'ravtest ps -a' to list all applications.",
                          manifest.manifest_name())
    if args.all:
        project = None
    else:
        project = manif['project']['name']
        console.info('Project name is `{0}`.', project)
    
    if args.blueprint:
        apps = cache.get_blueprints(project)
        what = 'blueprint'
    else:
        apps = cache.get_applications(project)
        what = 'application'

    apps = sorted(apps, key=lambda app: app['name'])
    objs = inflect.plural_noun(what)
    console.writeln('Currently available {0}:\n', objs)

    current_project = None
    for app in apps:
        parts = app['name'].split(':')
        if parts[0] != project and not args.all:
            continue
        if args.all and current_project != parts[0]:
            console.writeln("== Project: `{0}`", parts[0])
            current_project = parts[0]
        if args.full and not args.blueprint:
            app = cache.get_full_application(app['id'])

        cloud = app.get('cloud')
        region = app.get('regionName')
        started = app.get('totalStartedVms')
        start_time = app.get('publishStartTime')
        if started and start_time:
            now = time.time()
            start_time = util.format_timedelta(now - start_time/1000)
        else:
            start_time = ''
        creation_time = app.get('creationTime')
        if creation_time:
            stt = time.localtime(creation_time/1000)
            creation_time = time.strftime('%Y-%m-%d %H:%M:%S', stt)

        if args.full and not args.blueprint:
            vms = [ vm['name'] for vm in application.get_vms(app) ]
            vms = '`{0}`'.format('`, `'.join(vms))
            state = application.get_application_state(app)
        else:
            state = app.get('state') or ''

        console.writeln('=== {0}: `{1}:{2}`', what.title(), parts[1], parts[2])
        what2 = inflect.plural_noun('VM', started)
        if state:
            console.writeln('    state: {0}', state)
        if started is not None:
            console.writeln('    {0} {1} running', started, what2)
        if cloud is not None:
            console.writeln('    published to {0}/{1}', cloud, region)
        if start_time:
            console.writeln('    up for: {0}', start_time)
        elif creation_time:
            console.writeln('    created: {0}', creation_time)
        if args.full and not args.blueprint:
            console.writeln('    VMs: {0}', vms)
        console.writeln()
