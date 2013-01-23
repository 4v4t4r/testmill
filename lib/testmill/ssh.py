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
import re
import sys
import tempfile
import textwrap
import subprocess

import fabric
import fabric.api as fab

from . import ravello, main, util


class SshCommand(main.SubCommand):

    name = 'ssh'
    usage = textwrap.dedent("""\
            usage: ravtest ssh <application> [<testid>]
            """)
    description = textwrap.dedent("""\
            Start an interactive session to diagnose a previous test run.

            Positional arguments:
                <application>
                    The application name. This is typically the name of a
                    VM or a Blueprint with a numeric suffix attached to it.

                <testid>
                    Optional. If specified, the sesion will start in the
                    directory of the indicated test run. Test run IDs are
                    128-bit random hexadecimal strings, and may be abbreviated
                    as long as they are unique. The default is to start in the
                    directory of the last test run.

            Examples:
                $ ravtest ssh fedora17:1
                    Connects to the application "fedora17:1" and start an
                    interactive session in the directory of the last test.

                $ ravtest ssh ubuntu1204:2 2915158503b275668f074045f3f73921
                    Connects to the application "ubutu1204.2" and start an
                    interactive session in the directory of the indicated test
                    run.

                $ ravtest ssh ubuntu1204:2 291
                    As above but with an abbreviated test ID. Test IDs may be
                    abbreviated as long as they are unique.

            """)

    def add_args(self, parser, level=None):
        parser.add_argument('application')
        parser.add_argument('testid', nargs='?', default='last')

    def run(self, args):
        """The "ravello ssh" command."""

        # See if the application exists and in a state that is usable.

        self.load_cache(applications=True)
        app = self.get_application(name=args.application)
        if app is None:
            self.error("Application '{}' not found, exiting.\n"
                            .format(args.instance))
            self.exit(1)

        app = self.get_full_application(app['id'])
        vms = app['applicationLayer']['vm']
        if len(vms) == 0:
            self.error("Error: application '{}' has not VMs? Exiting."
                            .format(app['name']))
            self.exit(1)

        state = self.get_application_state(app)
        if state not in ('PUBLISHING', 'STARTING', 'STOPPED', 'STARTED'):
            self.error(textwrap.dedent("""\
                    Error: application '{}' has a VM in unkown state '{}'.
                    Do not know how to handle this state, exiting.
                    """.format(app['name'], state)))
            self.exit(1)

        # Do we have the right key?

        pubkey = self.load_keypair()
        if pubkey is None:
            self.error(textwrap.dedent("""\
                    Error: No keypair has been created yet.
                    A keypair is created when you first start an application.
                    Unable to log in to application, exiting.
                    """))
            self.exit(1)

        keynames = []
        for vm in app['applicationLayer']['vm']:
            try:
                keypair = vm['customVmConfigurationData']['keypair']
                kid = keypair['id']
                keynames.append(keypair['name'])
            except KeyError:
                continue
            if kid == pubkey['id']:
                break
        else:
            keys = ', '.join(keynames) if keynames else 'none'
            self.error(textwrap.dedent("""\
                Application '{}' has no VM with my keypair '{}'.
                Instead, it uses the following key(s): {}
                Unable to log in, exiting.
                """.format(app['name'], pubkey['name'], keys)))
            self.exit(1)

        # If the app is not started, start it. Then wait for it.

        if state in ('PUBLISHING', 'STARTING'):
            self.info("Application '{}' is {}, waiting for it to get up.\n"
                            .format(app['name'], state.lower()))
        elif state in ('STOPPED',):
            self.info("Application '{}' is {}, starting it.\n"
                            .format(app['name'], sate.lower()))
            self.start_application(app)

        alive = self.wait_until_applications_are_up([app])
        if not alive:
            self.error('Error: application did not come up, exiting.')
            self.exit(1)

        reachable = self.wait_until_applications_accept_ssh(alive)
        if not reachable:
            self.error('Error: application not reachable by ssh, exiting.')
            self.exit(1)

        # Now run ssh. Prefer openssh but fall back to using Fabric/Paramiko.

        host = 'ravello@{}'.format(vm['dynamicMetadata']['externalIp'])

        # Unfortunately we need some shell complexity here to be able to
        # robustly change into the right directory and also support test ID
        # abbreviations. The fragment below should be portable and work on
        # the bourne shell and it derivatives. It is also written in such a way
        # that whitespace, including newlines, can be compressed to a single
        # space. This is done because it will be passed as a command-line
        # argument to openssh and therefore gives a cleaner "ps" output.

        command = textwrap.dedent("""\
                TESTID="{testid}"; export TESTID;
                test -L "$TESTID" && TESTID="`readlink $TESTID`";
                if test ! -d "$TESTID"; then
                    nm="`ls -d $TESTID* 2>/dev/null | wc -l`";
                    if test "$nm" -eq "0"; then
                        echo "Error: No such test run: $TESTID";
                        echo "Starting session in home directory";
                    elif test "$nm" -gt "1"; then
                        echo "Error: Ambiguous test run: $TESTID";
                        echo "Starting session in home directory";
                    else
                        TESTID="`ls -d $TESTID*`";
                    fi;
                fi;
                test -d "$TESTID" && cd "$TESTID";
                exec $SHELL -l;
                """.format(testid=args.testid))
        command = re.sub('\s+', ' ', command)

        openssh = util.find_openssh()
        interactive = os.isatty(sys.stdin.fileno())

        if interactive and openssh:
            if not sys.platform.startswith('win'):
                # On Unix use execve(). This is the most efficient.
                argv = ['ssh', '-i', self.privkey_file,
                        '-o', 'UserKnownHostsFile=/dev/null'
                        '-o', 'StrictHostKeyChecking=no',
                        '-o', 'LogLevel=quiet',
                        '-t', host, command]
                os.execve(openssh, argv, os.environ)
            else:
                # Windows has execve() but for some reason it does not work
                # well with arguments with spaces in it. So use subprocess
                # instead.
                command = [openssh, '-i', self.privkey_file,
                           '-o', 'UserKnownHostsFile=NUL',
                           '-o', 'StrictHostKeyChecking=no',
                           '-o', 'LogLevel=quiet',
                           '-t', host, command]
                ssh = subprocess.Popen(command)
                ret = ssh.wait()
                self.exit(ret)

        # TODO: should also support PuTTY on Windows

        self.info(textwrap.dedent("""\
                Warning: no local openssh installation found.
                Falling back to Fabric/Paramiko for an interactive shell.
                However, please note:

                * CTRL-C and terminal resize signals may not work.
                * Output of programs that repaint the screen may
                  be garbled (e.g. progress bars).
                """))

        fab.env.host_string = host
        fab.env.key_filename = self.privkey_file
        fab.env.disable_known_hosts = True
        fab.env.remote_interrupt = True
        fab.env.output_prefix = None
        fabric.state.output.running = None
        fabric.state.output.status = None

        ret = fab.run(command, warn_only=True, combine_stderr=True, shell=True)
        self.exit(ret.return_code)
