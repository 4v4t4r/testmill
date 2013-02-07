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
                      error, util, console)


usage = textwrap.dedent("""\
        usage: ravtest [OPTION]... ssh <application> <vm> [<test_id>]
        """)

description = textwrap.dedent("""\
        Start an interactive session to diagnose a previous test run.

        Positional arguments:
            <application>
                The application name, as displayed by "ravtest run".
                This will be the application name as defined in the
                manifest, with a ":N" instance identifier.

            <vm>
                The name of the virtual machine.

            <test_id>
                Optional. If specified, the sesion will start in the
                directory of the indicated test run. Test run IDs are
                128-bit random hexadecimal strings, and may be abbreviated
                as long as they are unique. The default is to start in the
                directory of the last test run.

        Examples:
            $ ravtest ssh platformtest:1 fedora17
                Connects to the VM "fedora17" in application
                "platformtest:1".  The interactive session is started in
                the directory of the last test.

            $ ravtest ssh platformtest:1 ubuntu1204 291
                Connects to the VM "ubuntu1204" of the application
                "platformtest:1" and start an interactive session in the
                directory of the test run starting with "291". The test ID
                is abbreviated, which is allowed as long as the abbreviation
                is unique.

        """)


def add_args(parser):
    parser.usage = usage
    parser.description = description
    parser.add_argument('application')
    parser.add_argument('vm', nargs='?')
    parser.add_argument('test_id', nargs='?', default='last')


def do_ssh(args, env):
    """The "ravello ssh" command."""
    with env.let(quiet=True):
        login.default_login()
        keypair.default_keypair()
        manif = manifest.default_manifest()

    appname = '{}:{}'.format(manif['project']['name'], args.application)
    app = cache.get_application(name=appname)
    if not app:
        error.raise_error("Application '{}' not found.", appname)
    app = cache.get_full_application(app['id'])

    vmname = args.vm
    vms = app['applicationLayer'].get('vm', [])
    for vm in vms:
        if vm['name'] == vmname:
            break
    else:
        error.raise_error("Application '{}' has no VM '{}'.", appname, vmname)

    # Start up the application and wait for it if we need to.

    state = application.get_application_state(app)
    if state not in ('PUBLISHING', 'STARTING', 'STOPPED', 'STARTED'):
        error.raise_error("VM '{}' is in an unknown state.", vmname)

    userdata = vm.get('customVmConfigurationData', {})
    vmkey = userdata.get('keypair', {})

    if vmkey.get('id') != env.public_key['id']:
        error.raise_error("Unknown public key '{}'.", vmkey.get('name'))

    application.start_application(app)
    application.wait_for_application(app, [vmname])

    # Now run ssh. Prefer openssh but fall back to using Fabric/Paramiko.

    host = 'ravello@{}'.format(vm['dynamicMetadata']['externalIp'])
    command = '~/bin/run {}'.format(args.test_id)

    openssh = util.find_openssh()
    interactive = os.isatty(sys.stdin.fileno())

    if interactive and openssh:
        if not sys.platform.startswith('win'):
            # On Unix use execve(). This is the most efficient.
            argv = ['ssh', '-i', env.private_key_file,
                    '-o', 'UserKnownHostsFile=/dev/null',
                    '-o', 'StrictHostKeyChecking=no',
                    '-o', 'LogLevel=quiet',
                    '-t',  host, command]
            console.debug('Starting {}', ' '.join(argv))
            os.execve(openssh, argv, os.environ)
        else:
            # Windows has execve() but for some reason it does not work
            # well with arguments with spaces in it. So use subprocess
            # instead.
            command = [openssh, '-i', env.private_key_file,
                       '-o', 'UserKnownHostsFile=NUL',
                       '-o', 'StrictHostKeyChecking=no',
                       '-o', 'LogLevel=quiet',
                       '-t', host, command]
            ssh = subprocess.Popen(command)
            ret = ssh.wait()
            error.exit(ret)

    # TODO: should also support PuTTY on Windows

    console.info(textwrap.dedent("""\
            Warning: no local openssh installation found.
            Falling back to Fabric/Paramiko for an interactive shell.
            However, please note:

            * CTRL-C and terminal resize signals may not work.
            * Output of programs that repaint the screen may
              be garbled (e.g. progress bars).
            """))

    fab.env.host_string = host
    fab.env.key_filename = env.private_key_file
    fab.env.disable_known_hosts = True
    fab.env.remote_interrupt = True
    fab.env.output_prefix = None
    fabric.state.output.running = None
    fabric.state.output.status = None

    ret = fab.run(command, warn_only=True)
    return ret.return_code
