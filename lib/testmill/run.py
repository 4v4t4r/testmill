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
import stat
import os.path
import getpass
import textwrap
import tempfile
import subprocess
import hashlib
import socket
import select
import errno
import copy
import time
import json
import yaml

from . import main, ravello, util

import fabric.tasks
import fabric.state
import fabric.network
from fabric import api as fab

if not sys.platform.startswith('win'):
    EINPROGRESS = errno.EINPROGRESS
else:
    EINPROGRESS = errno.WSAEWOULDBLOCK

DEFAULT_TASKS = frozenset(('pack', 'renew', 'sysinit', 'copy', 'unpack',
        'prepare', 'execute', 'cleanup'))


def get_task(name, manifest, host):
    """Load a task from a manifest."""
    env = fab.env
    envname = env.appmap[env.vmmap[env.addrmap[host]]]
    taskdef = manifest[envname][name]
    if not taskdef:
        return
    cls = util.load_class(taskdef.pop('task'))
    if not cls:
        return
    task = cls(name=name, manifest=manifest, **taskdef)
    return task

def run_task(name, manifest):
    """Run a task from a manifest and run it."""
    task = get_task(name, manifest, fab.env.host)
    # Prevent further forking and double-parallel execution
    with fab.settings(parallel=False, hosts=[fab.env.host]):
        fabric.tasks.execute(task)

def run_tasks(names, manifest):
    """Run a sequence of tasks."""
    for name in names:
        run_task(name, manifest)


class Task(fabric.tasks.Task):
    """A task from the manifest."""

    def __init__(self, name=None, manifest=None, commands=None):
        super(Task, self).__init__()
        self.name = name or self.name
        self.manifest = manifest
        self.commands = commands or []

    def run(self, local=False, sudo=False):
        for command in self.commands:
            command = command.format(env=fab.env)
            if local:
                fab.local(command)
            elif sudo:
                fab.sudo(command)
            else:
                fab.run(command)


class RenewTask(Task):
    """Re-new the lease for a VM."""

    def run(self):
        fab.sudo("atrm `atq | awk '{print $1}'` || true")


class PackTask(Task):
    """Pack the project."""

    def run(self):
        super(PackTask, self).run(local=True)


class CopyTask(Task):
    """Copy the local contents to remote."""

    def __init__(self, files=None, **kwargs):
        super(CopyTask, self).__init__(**kwargs)
        if files is None:
            files = []
        elif not isinstance(files, list):
            files = [files]
        self.files = files

    def run(self):
        fab.run('mkdir %s' % fab.env.BASEDIR)
        for glob in self.files:
            fab.put(glob, fab.env.BASEDIR)
        fab.env.cwd = fab.env.BASEDIR


class UnpackTask(Task):
    """Unpack the project into the current working directory."""


class SysinitTask(Task): 
    """Initialize a VM when it first starts.

    This uses a file in the remote user's home directory to indicates the
    command has already been run.
    """

    def run(self):
        md = hashlib.sha1()
        for cmd in self.commands:
            md.update(cmd + '\000')
        token = md.hexdigest()
        name = '~/sysinit-%s.done' % token
        ret = fab.run('test -f {0}'.format(name), warn_only=True, quiet=True)
        if ret.succeeded:
            return
        super(SysinitTask, self).run(sudo=True)
        fab.run('touch {0}'.format(name))


class PrepareTask(Task):
    """Prepare a VM for running the tests."""


class ExecuteTask(Task):
    """Execute a command.

    This task will execute the user command, but before it does that, it
    schedules a 90-minute shutdown. The reason to do the shutdown before is to
    prevent users pressing CTRL-C when the task is done.

    The shutdown does both a local shutdown as well as a shutdown via the
    Ravello API. The latter is done to work around a missing feature that would
    keep the Cloud VM occupied if the nested VM is shut down.
    """

    def schedule_shutdown(self):
        env = fab.env
        vmid = env.addrmap[env.host]
        appid = env.vmmap[vmid]
        name = env.appmap[appid]
        # TODO: shutdown multi-vm apps
        delay = min(90, self.manifest[name]['keep'])
        url = '%s/deployment/app/%d/vm/%s/stop' % (env.API_URL, appid, vmid)
        cmd = 'curl --cookie %s --request POST %s; ' % (env.API_COOKIE, url)
        cmd += 'shutdown -h now'
        cmd = 'echo "%s" | at "now + %d minutes"' % (cmd, delay)
        fab.sudo(cmd, quiet=True)

    def run(self):
        self.schedule_shutdown()
        super(ExecuteTask, self).run()


class CleanupTask(Task):
    """Finalize the run."""


class RunCommand(main.SubCommand):
    """The "ravello run" command."""

    name = 'run'
    usage = textwrap.dedent("""\
            usage: ravtest run <command>
            """)
    description = textwrap.dedent("""\
            Run a command in one or more Ravello applications.  The
            applications are specified in the  manifest (.ravello.yml) .

            The available options are:
                -A <applist>, --applications <applist>
                    Only run the command on these applications.
                    <applist> is a comma-separated list of names
                -c, --continue
                    Continue running even after an error
                --new
                    Never re-use existing applications
                --dump
                    Dump the manifest and exit
            """)

    def add_args(self, parser):
        parser.add_argument('--environments', '-E')
        parser.add_argument('--continue', '-c', action='store_true',
                            dest='continue_')
        parser.add_argument('--new', action='store_true')
        parser.add_argument('--dump', action='store_true')
        parser.add_argument('command', nargs='?')

    def _try_use_existing_keypair(self):
        """Try to use a keypair that exists in ~/.ravello."""
        cfgdir = util.get_config_dir()
        privname = os.path.join(cfgdir, 'id_ravello')
        try:
            st = os.stat(privname)
        except OSError:
            return False
        if not stat.S_ISREG(st.st_mode):
            m = 'Error: {0} exists but is not a regular file'
            self.error(m.format(privname, pubname))
            self.exit(1)
        pubname = privname + '.pub'
        try:
            st = os.stat(pubname)
        except OSError:
            st = None
        if st is None or not stat.S_ISREG(st.st_mode):
            m = "Error: {0} exists but {1} doesn't or isn't a regular file."
            self.error(m.format(privname, pubname))
            self.exit(1)
        with file(pubname) as fin:
            pubkey = fin.read()
        keyparts = pubkey.strip().split()
        pubkeys = self.api.get_pubkeys()
        for pubkey in pubkeys:
            if pubkey['name'] == keyparts[2]:
                self.pubkey = pubkey
                self.privkey_file = privname
                return True
        return False

    def _create_new_keypair(self):
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

    def check_keypair(self):
        """Check if we have a keypair. If not, create it."""
        if self._try_use_existing_keypair():
            return
        self._create_new_keypair()

    def load_manifest(self):
        """Load and parse the manifest."""
        cwd = os.getcwd()
        ymlfile = os.path.join(cwd, '.ravello.yml')
        if not os.access(ymlfile, os.R_OK):
            m = 'Error: project manifest (.ravello.yml) not found.'
            self.error(m)
            self.exit(1)
        with file(ymlfile) as fin:
            try:
                manifest = yaml.load(fin)
            except yaml.parser.ParserError as e:
                self.error('Error: illegal YAML in .ravello.yml')
                self.error('Message from parser: {0!s}'.format(e))
                self.exit(1)
        self.manifest = manifest
        dirname, rest = os.path.split(__file__)
        ymlfile = os.path.join(dirname, 'defaults.yml')
        with file(ymlfile) as fin:
            self.default_manifest = yaml.load(fin)
        return manifest

    def _detect_language(self):
        """Detect the language of a project by looking at a number of files
        that are strong indicators for a particular language."""
        cwd = os.getcwd()
        contents = os.listdir(cwd)
        for fname in contents:
            if fname == 'setup.py':
                return 'python'
            elif fname == 'project.clj':
                return 'clojure'
            elif fname == 'pom.xml':
                return 'java_maven'
            elif fname == 'build.xml':
                return 'java_ant'

    def detect_language(self, manifest):
        """Detect the language of a project in the current working directory."""
        language = manifest.get('language')
        if not language:
            language = self._detect_language()
            if language is not None:
                pretty = '/'.join((l.title() for l in language.split('_')))
                self.info('Detected a {0} project.'.format(pretty))
            manifest['language'] = language
        elif language not in self.default_manifest.get('language_defaults', {}):
            m = 'Warning: unknown language "{0}" specified in manifest.'
            self.error(m.format(language))

    def check_and_explode_manifest(self, manifest):
        """Check the manifest semantical errors and explode it at the same
        time. NOTE: updates `manifest`."""
        util.merge(manifest, self.default_manifest)
        # Explode environment definitions
        manifest.setdefault('environments', [])
        for name in manifest['environments']:
            if name not in manifest:
                manifest[name] = {}
            envdef = manifest[name]
            if 'name' not in envdef:
                envdef['name'] = name
            if 'vm' not in envdef:
                envdef['vm'] = name
            # Explode tasks
            for taskname in DEFAULT_TASKS:
                taskdef = envdef.get(taskname)
                if taskdef is None:
                    taskdef = manifest.get(taskname, {})
                    if name in taskdef:
                        taskdef = taskdef[name]
                    envdef[taskname] = taskdef
                if isinstance(taskdef, list):
                    taskdef = envdef[taskname] = { 'commands': taskdef }
                elif isinstance(taskdef, str):
                    taskdef = envdef[taskname] = { 'task': taskdef }
                elif not isinstance(taskdef, dict):
                    m = 'Error: environment "{0}": key "{1}" must be list, ' \
                          'str or dict.'
                    self.error(m.format(name, taskname))
                    self.exit(1)
        # Merge defaults into environments
        language = manifest['language']
        defaults = manifest.get('defaults', {})
        language_defaults = manifest.get('language_defaults', {}) \
                                    .get(language, {})
        for name in manifest['environments']:
            util.merge(manifest[name], language_defaults)
            util.merge(manifest[name], defaults)
            if self.args.command:
                manifest[name]['execute']['commands'] = [self.args.command]

    def check_referenced_entities_in_manifest(self, manifest):
        """Check the manifest to make sure all referenced entities exist."""
        for name in manifest['environments']:
            envdef = manifest[name]
            vmname = envdef['vm']
            image = self.get_image(name=vmname)
            if image is None:
                m = "Error: Unknown vm '{0}' in environment '{1}'"
                self.error(m.format(vmname, name))
                self.exit(1)
            bpname = envdef.get('blueprint')
            if bpname is not None:
                bp = self.get_blueprint(name=bpname)
                if bp is None:
                    m = "Error: Unknown blueprint '{0}' in environment '{1}'"
                    self.error(m.format(bpname, name))
                    self.exit(1)
            for taskname,taskdef in envdef.items():
                if isinstance(taskdef, dict) and 'task' in taskdef:
                    if not util.load_class(taskdef['task']):
                        m = "Error: task class '{0}' not found in {1}/{2}"
                        self.error(m.format(taskdef['task']), name, taskname)
                        self.exit(1)

    VM_STATE_PREFERENCES = ['STARTED', 'STARTING', 'STOPPED', 'PUBLISHING']
    VM_REUSE_STATES = ['PUBLISHING', 'STARTING', 'STARTED', 'STOPPED']

    def _reuse_single_vm_application(self, envdef):
        """Try to re-use a single VM application."""
        image = self.get_image(name=envdef['vm'])
        candidates = []
        for app in self.applications:
            base, suffix = util.splitname(app['name'])
            if base != envdef['name'] or not suffix:
                continue
            app = self.get_full_application(app['id'])
            vms = app['applicationLayer']['vm']
            if len(vms) != 1:
                continue
            vm = vms[0]
            if vm['shelfVmId'] != image['id']:
                continue
            state = vm['dynamicMetadata']['state']
            if state not in self.VM_REUSE_STATES:
                continue
            userdata = vm['customVmConfigurationData']
            if not userdata:
                continue
            keypair = userdata.get('keypair')
            if not keypair or keypair.get('id') != self.pubkey['id']:
                continue
            candidates.append((state, app, vms[0]))
        if not candidates:
            return
        candidates.sort(key=lambda x: self.VM_STATE_PREFERENCES.index(x[0]))
        state, app, vm = candidates[0]
        m = 'Re-using {0} application "{1}" for "{2}"'
        self.info(m.format(state.lower(), app['name'], envdef['name']))
        if state == 'STOPPED':
            self.api.start_vm(app, vm)
        return app['id']

    def _create_new_single_vm_application(self, envdef):
        """Create a new single VM application."""
        image = self.get_image(name=envdef['vm'])
        image = self.get_full_image(image['id'])
        vm = ravello.update_luids(image)
        vm['customVmConfigurationData'] = { 'keypair': self.pubkey }
        app = ravello.Application()
        name = util.get_unused_name(envdef['name'], self.applications)
        app['name'] = name
        app['applicationLayer'] = { 'vm': [ vm ] }
        app = self.api.create_application(app)
        self.api.publish_application(app)
        self.get_full_application(app['id'], force_reload=True)
        m = 'Created new application "{0}" for "{1}"'
        self.info(m.format(app['name'], envdef['name']))
        return app['id']

    def start_applications(self, manifest):
        """Start up all applications."""
        appmap = {}  # { appid: manifest_name }
        for name in manifest['environments']:
            envdef = manifest[name]
            vmname = envdef['vm']
            bpname = envdef.get('blueprint')
            if bpname is None:
                appid = None
                if not self.args.new:
                    appid = self._reuse_single_vm_application(envdef)
                if appid is None:
                    appid = self._create_new_single_vm_application(envdef)
            else:
                # TODO: blueprints
                continue
            appmap[appid] = name
        return appmap

    VM_WAIT_STATES = ['PUBLISHING', 'STARTING', 'STARTED']

    def wait_until_applications_are_up(self, appmap, timeout, poll_timeout):
        """Wait until all the application are started."""
        end_time = time.time() + timeout
        vmmap = {}  # { vmid: appid }
        addrmap = {}  # { host_or_ip: vmid }
        waitapps = set(appmap)
        while True:
            if time.time() > end_time:
                break
            min_state = 3
            for appid in list(waitapps):  # updating
                app = self.get_full_application(appid, force_reload=True)
                app_min_state = 3
                for status in app['cloudVmsStatusCounters']:
                    state = status['status']
                    try:
                        state = self.VM_WAIT_STATES.index(state)
                    except ValueError:
                        waitapps.remove(appid)
                        state = 3
                    app_min_state = min(app_min_state, state)
                if app_min_state == 2:
                    for vm in app['applicationLayer']['vm']:
                        addr = vm['dynamicMetadata']['externalIp']
                        addrmap[addr] = vm['id']
                        vmmap[vm['id']] = appid
                    waitapps.remove(appid)
                min_state = min(min_state, app_min_state)
            if not waitapps:
                break
            if min_state == 0:
                self.progress('P')
            elif min_state == 1:
                self.progress('S')
            time.sleep(poll_timeout)
        if len(waitapps) == len(appmap):
            self.error('Error: no application could be started up, exiting.')
            self.exit(1)
        elif len(waitapps):
            m = 'Error: Could not start {0} out of {1} applications.'
            self.error(m.format(len(waitapps), len(appmap)))
            failed = ', '.join([appmap[appid] for appid in waitapps])
            m = 'Continue without failed applications: {0}'
            self.info(m.format(failed))
        return vmmap, addrmap

    def wait_until_vms_accept_ssh(self, addrmap, timeout, poll_timeout):
        """Wait for `timeout` seconds until the IP addresses in `addrs` accept
        a connection on their ssh port.
        """
        end_time = time.time() + timeout
        addrs = set(addrmap)
        alive = []
        # For the intricate details on non-blocking connect()'s, see Stevens,
        # UNIX network programming, volume 1, chapter 16.3 and following.
        while True:
            if time.time() > end_time:
                break
            waitfds = {}
            for addr in addrs:
                sock = socket.socket()
                sock.setblocking(False)
                try:
                    sock.connect((addr, 22))
                except socket.error as e:
                    if e.errno != EINPROGRESS:
                        self.error('connect(): errno {0.errno}'.format(e))
                        raise
                waitfds[sock.fileno()] = (sock, addr)
            poll_end_time = time.time() + poll_timeout
            while True:
                timeout = poll_end_time - time.time()
                if timeout < 0:
                    for fd in waitfds:
                        sock, addr = waitfds[fd]
                        sock.close()
                    break
                try:
                    wfds = list(waitfds)
                    _, wfds, _ = select.select([], wfds, [], timeout)
                except select.error as e:
                    if e.args[0] != errno.EINTR:
                        self.error('select(): errno {0.errno}'.format(e))
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
                        alive.append(addr)
                        addrs.remove(addr)
                    del waitfds[fd]
                if not waitfds:
                    break
            if not addrs:
                break
            self.progress('C')  # 'C' = Connecting
            timeout = poll_end_time - time.time()
            if timeout > 0:
                time.sleep(timeout)
        if len(alive) != len(addrmap):
            m = 'Error: Could not start {0} out of {1} applications.'
            self.error(m.format(len(addrmap)-len(alive), len(addrmap)))
        elif len(alive) == 0:
            self.error('Error: no VM came up, exiting')
            self.exit(1)
        return alive

    def setup_fabric_environment(self, appmap, vmmap, addrmap):
        """Set up the fabric environment."""
        fab.env.appmap = appmap
        fab.env.vmmap = vmmap
        fab.env.addrmap = addrmap
        fab.env.cwd = None
        fab.env.hosts = list(addrmap)
        fab.env.user = 'ravello'
        fab.env.key_filename = self.privkey_file
        fab.env.disable_known_hosts = True
        fab.env.warn_only = self.args.continue_
        fab.env.remote_interrupt = True
        # Suppress output for most actions
        fab.env.output_prefix = self.args.debug
        fabric.state.output.running = self.args.debug
        fabric.state.output.output = self.args.debug
        fabric.state.output.status = self.args.debug
        fab.env.COMMAND = self.args.command
        # Remote distribution directory.
        basedir = os.urandom(16).encode('hex')
        fab.env.BASEDIR = basedir
        # Export API (for shutdown)
        fab.env.API_URL = self.api.url
        fab.env.API_COOKIE = self.api._cookie

    def progress(self, progress):
        if self.args.quiet:
            return
        if not getattr(self, 'progress_bar_started', False):
            self.info('Waiting until applications are ready...')
            self.info("Progress: 'P' = Publishing, 'S' = Starting, 'C' = Connecting")
            self.stdout.write('==> ')
            self.stdout.flush()
            self.progress_bar_started = True
        self.stdout.write(progress)
        self.stdout.flush()

    def run(self, args):
        """The "ravello run" command."""
        # Load the manifest and the default manifest.
        manifest = self.load_manifest()

        # Detect language, if "language" is not given.
        self.detect_language(manifest)

        # Expand from shorthand .ravello.yml notation to full notation.
        # Also check for missing or conflicting keys.
        self.check_and_explode_manifest(manifest)

        # Some more argument parsing
        if args.dump:
            util.pprint(manifest)
            self.exit(0)
        if args.environments:
            envs = [env.lower() for env in args.environments.split(',')]
            manifest['environments'] = [env for env in manifest['environments']
                                        if env.lower() in envs]
        if not manifest['environments']:
            self.error('No environments defined, exiting.')
            self.exit(1)

        # Load images, applications and blueprints
        self.load_cache()

        # Check for referenced entities that are unknown
        self.check_referenced_entities_in_manifest(manifest)

        # Ready to go...
        names = ', '.join(manifest['environments'])
        self.info('Environments to run: {0}'.format(names))

        # Ensure we have a keypair
        self.check_keypair()

        # Start up the applications.
        appmap = self.start_applications(manifest)

        # Wait until the applications are up.. And show some progress.
        vmmap, addrmap = self.wait_until_applications_are_up(appmap, 900, 10)
        alive = self.wait_until_vms_accept_ssh(addrmap, 300, 5)
        if hasattr(self, 'progress_bar_started'):
            self.progress(' DONE\n')
        addrmap = dict(((addr, addrmap[addr]) for addr in alive))

        # Now run the tasks...
        self.setup_fabric_environment(appmap, vmmap, addrmap)

        # Pack: local only
        anyhost = [fab.env.hosts[0]]
        fabric.tasks.execute(run_task, 'pack', manifest, hosts=anyhost)

        # Start parallel processing. Minimize forks by running as many actions
        # in a single composite task.
        fab.env.parallel = len(fab.env.hosts) > 1
        init_actions = ('renew', 'sysinit', 'copy', 'unpack', 'prepare')
        fabric.tasks.execute(run_tasks, init_actions, manifest)
        # Communicate new working directory..
        fab.env.cwd = fab.env.BASEDIR

        # The main command is run serially so that we can show output in a
        # sensible way.
        fabric.state.output.output = True
        for host in fab.env.hosts:
            name = appmap[vmmap[addrmap[host]]]
            task = get_task('execute', manifest, host)
            m = "\n== Output for '{0}' on '{1}':\n"
            self.write(m.format(task.commands[0], name))
            fabric.tasks.execute(task, hosts=[host])
            self.write('')

        # cleanup + shutdown: in parallel again
        #fabric.state.output.output = False
        #close_actions = ('cleanup', 'free')
        #fabric.tasks.execute(run_tasks, close_actions, manifest)

        fabric.network.disconnect_all()
        self.exit(0)
