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
import stat
import time
import logging
import textwrap
import subprocess
import select
import socket
import errno

import fabric.colors
from . import command, ravello, util


class MainCommand(command.CommandBase):
    """Top-level command.
    
    This defines the command-line options that are common to every sub-command.
    """

    usage = textwrap.dedent("""\
            usage: ravtest [-u <user>] [-p <password>] [-s <service_url>]
                           [-q] [-d] [-y] [-h] <command> [<arg>]...
                       """)
    description = textwrap.dedent("""\
        Ravello TestMill, a system test driver for Ravello.

        The available options are:
            -u <user>, --user <user>
                Specifies the Ravello user name
            -p <password>, --password <password>
                Specifies the Ravello password
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
            
        The available commands are:
            login       log in to Ravello
            ps          show running applications
            run         run a remote command
            ssh         connect to an application

        Use 'ravtest <command> --help' to get help for a command.
        """)

    def __init__(self):
        super(MainCommand, self).__init__()
        from . import login, ps, run, ssh
        self.add_sub_command(login.LoginCommand(parent=self))
        self.add_sub_command(ps.PsCommand(parent=self))
        self.add_sub_command(run.RunCommand(parent=self))
        self.add_sub_command(ssh.SshCommand(parent=self))

    def add_args(self, parser, level=0):
        super(MainCommand, self).add_args(parser, level)
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

    def __init__(self, parent):
        super(SubCommand, self).__init__(parent)
        self.logger = logging.getLogger('ravello')
        self._api = None
        self.progress_bar_started = False
        self.progress_bar_text = None
        self.images = []
        self.applications = []
        self.blueprints = []
        self.full_images = {}
        self.full_applications = {}
        self.full_blueprints = {}

    def error(self, message):
        """Write an error message to standard output."""
        if self.progress_bar_started:
            self.end_progress_bar('ERROR')
        if not sys.platform.startswith('win'):
            message = fabric.colors.red(message)
        super(SubCommand, self).error(message)

    def info(self, message):
        """Write an informational message to standard output, if not in
        quiet mode."""
        if self.args.quiet:
            return
        self.stdout.write(message)
        self.stdout.write('\n')

    def debug(self, message):
        """Show a debugging message, if debugging is enabled."""
        if not self.args.debug:
            return
        self.stdout.write(message)
        self.stdout.write('\n')

    def start_progress_bar(self, text):
        """Start a new progress bar with `text`."""
        self.progress_bar_text = text

    def show_progress(self, progress):
        """Show progress. Normally `progress` is a single character."""
        if self.args.quiet or not self.progress_bar_text:
            return
        if not self.progress_bar_started:
            self.stdout.write(self.progress_bar_text)
            self.stdout.flush()
            self.progress_bar_started = True
        self.stdout.write(progress)
        self.stdout.flush()

    def end_progress_bar(self, text):
        """End a progress bar with "text"."""
        if self.progress_bar_started:
            self.stdout.write(' {}\n'.format(text))
        self.progress_bar_text = None
        self.progress_bar_started = False
 
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
        cfgdir = util.get_config_dir()
        tokfile = os.path.join(cfgdir, 'api-token')
        try:
            with file(tokfile) as ftok:
                token = ftok.read()
        except IOError:
            self.error('Error: no Ravello credentials provided')
            self.error('Specify --user and --password, or use "ravello login.')
            self.exit(1)
        token = token.strip()
        try:
            api.login(token=token)
        except ravello.RavelloError as e:
            self.error('Error: could not login to Ravello with token')
            self.error('Try "ravello login" to refresh it.')
            self.exit(1)

    @property
    def api(self):
        """Return a connection to the Ravello API."""
        if self._api is not None:
            return self._api
        args = self.args
        api = ravello.RavelloClient(service_url=args.service_url)
        if args.user and args.password:
            self._try_password_login(api)
        else:
            self._try_token_login(api)
        self._api = api
        return self._api

    def load_cache(self, **kwds):
        """Load a cache of all current applications and images."""
        if not kwds or kwds.get('images'):
            self.images = self.api.get_images()
        if not kwds or kwds.get('applications'):
            self.applications = self.api.get_applications()
        if not kwds or kwds.get('blueprints'):
            self.blueprints = self.api.get_blueprints()

    def get_image(self, id=None, name=None):
        """Get an image based on its id or name."""
        if not (bool(id is None) ^ bool(name is None)):
            raise ValueError('Specify either "id" or "name".')
        for img in self.images:
            if name is not None:
                name1 = 'testmill:{0}'.format(name.lower()) \
                            if img['public'] else name.lower()
                if name1 == img['name'].lower():
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

    # Keypairs ...

    def load_keypair(self):
        """Try to load a keypair that exists in ~/.ravello."""
        cfgdir = util.get_config_dir()
        privname = os.path.join(cfgdir, 'id_ravello')
        try:
            st = os.stat(privname)
        except OSError:
            return
        if not stat.S_ISREG(st.st_mode):
            m = 'Error: private key {0} exists but is not a regular file'
            self.error(m.format(privname, pubname))
            return
        pubname = privname + '.pub'
        try:
            st = os.stat(pubname)
        except OSError:
            st = None
        if st is None or not stat.S_ISREG(st.st_mode):
            m = "Error: {0} exists but {1} doesn't or isn't a regular file"
            self.error(m.format(privname, pubname))
            return
        with file(pubname) as fin:
            pubkey = fin.read()
        keyparts = pubkey.strip().split()
        pubkeys = self.api.get_pubkeys()
        for pubkey in pubkeys:
            if pubkey['name'] == keyparts[2]:
                self.pubkey = pubkey
                self.privkey_file = privname
                return pubkey
        return

    def create_new_keypair(self):
        """Create a new keypair and upload it to Ravello."""
        # First try to generate it locallly (= more privacy)
        cfgdir = util.get_config_dir()
        privname = os.path.join(cfgdir, 'id_ravello')
        pubname = privname + '.pub'
        keyname = 'ravello@%s' % socket.gethostname()
        try:
            self.info("Generating keypair using 'ssh-keygen'...")
            subprocess.call(['ssh-keygen', '-q', '-t', 'rsa', '-C', keyname,
                             '-b', '2048', '-N', '', '-f', privname])
        except OSError:
            self.info('Failed (ssh-keygen not found).')
            pubkey = None
        except subprocess.CalledProcessError as e:
            m = 'Error: ssh-keygen returned with error status {0}'
            self.error(m.format(e.returncode))
        else:
            with file(pubname) as fin:
                pubkey = fin.read()
            keyparts = pubkey.strip().split()
        # If that failed, have the API generate one for us
        if pubkey is None:
            keyname = 'ravello@api-generated'
            self.info('Requesting a new keypair via the API...')
            keypair = self.api.create_keypair()
            with file(privname, 'w') as fout:
                fout.write(keypair['privateKey'])
            with file(pubname, 'w') as fout:
                fout.write(keypair['publicKey'].rstrip())
                fout.write(' {0} (generated remotely)\n'.format(keyname))
            pubkey = keypair['publicKey'].rstrip()
            keyparts = pubkey.split()
            keyparts[2:] = [keyname]
        # Create the pubkey in the API under a unique name
        pubkeys = self.api.get_pubkeys()
        keyname = util.get_unused_name(keyname, pubkeys)
        keyparts[2] = keyname
        keydata = '{0} {1} {2}\n'.format(*keyparts)
        pubkey = ravello.Pubkey(name=keyname)
        pubkey['publicKey'] = keydata
        pubkey = self.api.create_pubkey(pubkey)
        with file(pubname, 'w') as fout:
            fout.write(keydata)
        self.pubkey = pubkey
        self.privkey_file = privname
        return pubkey

    def check_keypair(self):
        """Check if we have a keypair. If not, create it."""
        if not self.load_keypair():
            self.create_new_keypair()

    # Starting and waiting for applications ..

    VM_ORDERED_STATES = ['PUBLISHING', 'STOPPED', 'STARTING', 'STARTED']

    def combine_states(self, state1, state2):
        """Combine two VM states `state1` and `state2` into a single state.

        If both states are known, the combined state is the minimum state
        according to the VM_ORDERED_STATES ordering. If one state is unknown,
        it is the unknown state.
        """
        try:
            index1 = self.VM_ORDERED_STATES.index(state1)
        except ValueError:
            return state1
        try:
            index2 = self.VM_ORDERED_STATES.index(state2)
        except ValueError:
            return state2
        return self.VM_ORDERED_STATES[min(index1, index2)]

    def get_application_state(self, app):
        """Return the state of an application.

        The state of an application is defined as the minimum state of its
        VMs.
        """
        vms = app['applicationLayer']['vm']
        if not vms:
            return
        app_state = vms[0]['dynamicMetadata']['state']
        for vm in vms[1:]:
            vm_state = vm['dynamicMetadata']['state']
            app_state = self.combine_states(app_state, vm_state)
        return app_state

    def start_application(self, app):
        """Start up all VMs in an application."""
        vms = app['applicationLayer']['vm']
        for vm in vms:
            if vm['dynamicMetadata']['state'] == 'STOPPED':
                self.api.start_vm(app, vm)

    def wait_until_applications_are_up(self, apps, timeout=900,
                                       poll_timeout=10):
        """Wait until a set of applications is up.

        The applications are given by the `apps` argument. An application is up
        if all its VMs are in the 'STARTED' state.

        The applications are polled sequentially for their state, one after the
        other. If not all applications are up yet, a delay of `poll_timeout`
        seconds taken into account before trying again. Applications that are
        up are not checked again.

        This function returns when all applications are up, or when `timeout`
        seconds have elapsed, whichever occurs sooner.

        The return value is a list of applications that are up.
        """
        alive = []
        waitapps = set((app['id'] for app in apps))
        end_time = time.time() + timeout
        while True:
            if time.time() > end_time:
                break
            min_state = 'STARTED'
            for appid in list(waitapps):  # updating
                app = self.get_full_application(appid, force_reload=True)
                app_state = self.get_application_state(app)
                if app_state == 'STARTED':
                    alive.append(app)
                    waitapps.remove(appid)
                elif app_state not in ('PUBLISHING', 'STARTING'):
                    waitapps.remove(appid)
                    continue
                min_state = self.combine_states(min_state, app_state)
            if not waitapps:
                break
            self.show_progress(min_state[0])
            time.sleep(poll_timeout)
        return alive

    if not sys.platform.startswith('win'):
        EINPROGRESS = errno.EINPROGRESS
    else:
        EINPROGRESS = errno.WSAEWOULDBLOCK

    def wait_until_applications_accept_ssh(self, apps, timeout=300,
                                           poll_timeout=5):
        """Wait until a set of applications is reachable by ssh.

        An application is reachable by SSH if all the VMs that have a public
        key userdata set are connect()able on port 22.

        All VMs are polled in parallel. If a connect() operation for an address
        completes within `poll_timeout` seconds.
        
        This call returns whenn all applications are reachable by ssh, or 
        when `timeout` seconds have passed, whichever occurs first.

        The return value is the list of reachable applications.
        """
        waitapps = set((app['id'] for app in apps))
        def has_keypair(vm):
            return 'keypair' in vm.get('customVmConfigurationData', {})
        waitaddrs = set((vm['dynamicMetadata']['externalIp']
                        for app in apps
                            for vm in app['applicationLayer']['vm']
                                if has_keypair(vm)))
        aliveaddrs = set()
        end_time = time.time() + timeout
        # For the intricate details on non-blocking connect()'s, see Stevens,
        # UNIX network programming, volume 1, chapter 16.3 and following.
        while True:
            if time.time() > end_time:
                break
            waitfds = {}
            for addr in waitaddrs:
                sock = socket.socket()
                sock.setblocking(False)
                try:
                    sock.connect((addr, 22))
                except socket.error as e:
                    if e.errno != self.EINPROGRESS:
                        self.error('connect(): errno {.errno}'.format(e))
                        raise
                waitfds[sock.fileno()] = (sock, addr)
            poll_end_time = time.time() + poll_timeout
            while True:
                timeout = poll_end_time - time.time()
                if timeout < 0:
                    for fd in waitfds:
                        sock, _ = waitfds[fd]
                        sock.close()
                    break
                try:
                    wfds = list(waitfds)
                    _, wfds, _ = select.select([], wfds, [], timeout)
                except select.error as e:
                    if e.args[0] == errno.EINTR:
                        continue
                    else:
                        self.error('select(): errno {.errno}'.format(e))
                        raise
                for fd in wfds:
                    assert fd in waitfds
                    sock, addr = waitfds[fd]
                    try:
                        error = sock.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
                    except socket.error as e:
                        error = e.errno
                    # TODO: are there any terminal errors here?
                    sock.close()
                    if not error:
                        aliveaddrs.add(addr)
                        waitaddrs.remove(addr)
                    del waitfds[fd]
                if not waitfds:
                    break
            if not waitaddrs:
                break
            self.show_progress('C')  # 'C' = Connecting
            timeout = poll_end_time - time.time()
            if timeout > 0:
                time.sleep(timeout)
        alive = [ app for app in apps
                    if all([vm['dynamicMetadata']['externalIp'] in aliveaddrs
                        for vm in app['applicationLayer']['vm']]) ]
        return alive


def main():
    command = MainCommand()
    command.main()

if __name__ == '__main__':
    main()
