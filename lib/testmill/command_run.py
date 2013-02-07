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

import argparse
import textwrap

from testmill import (console, manifest, keypair, login, error,
                      application, tasks, util)
from testmill.state import env


usage = textwrap.dedent("""\
        usage: ravtest [OPTION]... run [-i] [-c] [--new] [-V <vmlist>]
                       <application> [<command>]
               ravtest run --help
        """)

description = textwrap.dedent("""\
        Run automated tasks in a Ravello application.
        
        The application defined by <application> is loaded from the manifest
        (.ravello.yml). It is then created if it doesn't exist yet, and the
        runbook defined in the manifest is run.

        If --new is specified, a new application instance is always created,
        even if one exists already.

        The available options are:
            -i, --interactive
                Run in interactive mode. All tasks are run directly
                connected to the console. In case of multiple virtual
                machines, output will be interleaved and may be hard
                to understand.
            -c, --continue
                Continue running even after an error.
            --new
                Never re-use existing applications.
            -V <vms>, --vms <vmlist>
                Execute tasks only on these virtual machines, instead of on
                all virtual machines in the application. <vmlist> is a
                comma-separated list of VMs.
        """)


def add_args(parser):
    parser.usage = usage
    parser.description = description
    parser.add_argument('-i', '--interactive', action='store_true')
    parser.add_argument('-c', '--continue', action='store_true',
                        dest='continue_')
    parser.add_argument('--new', action='store_true')
    parser.add_argument('-V', '--vms')
    parser.add_argument('application')
    parser.add_argument('command', nargs='?')


def do_run(args, env):
    """The "ravello run" command."""
    login.default_login()
    keypair.default_keypair()
    manif = manifest.default_manifest()

    appname = args.application
    for appdef in manif.get('applications', []):
        if appdef['name'] == appname:
            break
    else:
        error.raise_error("Unknown application '{}'.", appname)

    vms = appdef.get('vms', [])

    vms = set((vm['name'].lower() for vm in appdef['vms']))
    if args.vms:
        only = set((name.lower() for name in args.vms.split(',')))
        if not only <= vms:
            unknown = [name for name in only if name not in vms]
            what = util.plural_noun('virtual machine', len(unknown))
            error.raise_error("Unknown {}: {}", ', '.join(unknown), what)
        vms = [name for name in vms if name in only]
    if not vms:
        error.raise_error('No virtual machines in application.')

    if args.command:
        for vm in appdef['vms']:
            vm['tasks'] = [{'name': 'execute', 'commands': [args.command]}]

    what = util.plural_noun('virtual machine', len(vms))
    console.info('Running tasks on {} {}.', len(vms), what)

    app = application.create_or_reuse_application(appdef, args.new)
    app = application.wait_for_application(app, vms)

    ret = tasks.run_all_tasks(app, vms)

    console.info('\n== The following services will be available for {} minutes:\n',
                 appdef['keepalive'])

    for vm in app['applicationLayer']['vm']:
        if vm['name'] not in vms:
            continue
        svcs = vm.get('suppliedServices')
        if not svcs:
            continue
        console.info("On virtual machine '{}':", vm['name'])
        for svc in svcs:
            svc = svc['baseService']
            addr = util.format_service(vm, svc)
            console.info('    * {}: {}', svc['name'], addr)
        console.info('')

    return error.EX_OK if ret == 0 else error.EX_SOFTWARE
