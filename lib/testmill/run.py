# Copyright 2012 Ravello Systems, Inc.
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
import os.path
import getpass
import textwrap
import tempfile
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


DEFAULT_MANIFEST = textwrap.dedent("""\
    defaults:
        keep: 90
        pack:
            local: True
        renew:
            sudo: True
            commands:
            - "atrm `atq | awk '{{print $1}}'` || true"
        sysinit:
            task: testmill.run:SysinitTask
            sudo: True
        copy:
            commands:
            - "mkdir {env.DISTBASE}"
        execute:
            task: testmill.run:ExecuteTask
            commands:
            - "{env.COMMAND}"
    language_defaults:
        python:
            pack:
                commands:
                - "python setup.py sdist --dist-dir {env.DISTDIR}"
            copy:
                task: testmill.run:CopyTask
            unpack:
                commands:
                - "mkdir dist && mv *.tar.gz dist && tar xvfz dist/*.tar.gz --strip-components=1"
            prepare:
                commands:
                - "python setup.py build"
    language: null
    applications: {}
""")

DEFAULT_TASKS = frozenset(('pack', 'renew', 'sysinit', 'copy', 'unpack',
        'prepare', 'execute', 'cleanup'))


def get_task(name, manifest, host):
    """Load a task from a manifest."""
    env = fab.env
    appname = env.appmap[env.vmmap[env.addrmap[host]]]
    taskdef = manifest['applications'][appname][name]
    if not taskdef:
        return
    cls = util.load_class(taskdef.pop('task'))
    if not cls:
        return
    task = cls(name, manifest, **taskdef)
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

    def __init__(self, name=None, manifest=None, commands=None, local=False,
                 sudo=False):
        super(Task, self).__init__()
        self.name = name or self.name
        self.manifest = manifest
        self.commands = commands or []
        self.local = local
        self.sudo = sudo

    def run(self):
        for command in self.commands:
            command = command.format(env=fab.env)
            if self.local:
                fab.local(command)
            elif self.sudo:
                fab.sudo(command)
            else:
                fab.run(command)


class SysinitTask(Task): 
    """Initialize a VM when it first starts.

    This uses a file in the remote user's home directory to indicates the
    command has already been run.
    """

    def run(self):
        ret = fab.run('test -f ~/%s.done' % self.name,
                      warn_only=True, quiet=True)
        if ret.succeeded:
            return
        super(SysinitTask, self).run()
        fab.run('touch ~/%s.done' % self.name)


class CopyTask(Task):
    """Copy the local contents from env.DISTDIR."""

    def run(self):
        fab.run('mkdir %s' % fab.env.DISTBASE)
        fab.put('%s/*' % fab.env.DISTDIR, fab.env.DISTBASE)
        fab.env.cwd = fab.env.DISTBASE


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
        delay = min(90, self.manifest['applications'][name]['keep'])
        url = '%s/deployment/app/%d/vm/%s/stop' % (env.API_URL, appid, vmid)
        cmd = 'curl --cookie %s --request POST %s; ' % (env.API_COOKIE, url)
        cmd += 'shutdown -h now'
        cmd = 'echo "%s" | at "now + %d minutes"' % (cmd, delay)
        fab.sudo(cmd, quiet=True)

    def run(self):
        self.schedule_shutdown()
        super(ExecuteTask, self).run()


class RunCommand(main.SubCommand):
    """The "ravello run" command."""

    name = 'run'
    usage = textwrap.dedent("""\
            usage: rtm run <command>
            """)
    description = textwrap.dedent("""\
            Run a command in one or more Ravello applications.  The
            applications are specified in the  manifest (.testmill.yml) .

            The available options are:
                -A <applist>, --applications <applist>
                    Only run the command on these applications.
                    <applist> is a comma-separated list of names
                --new
                    Never re-use existing applications
                --dump
                    Dump the manifest and exit
            """)

    def add_args(self, parser):
        parser.add_argument('--new', action='store_true')
        parser.add_argument('--dump', action='store_true')
        parser.add_argument('--applications', '-A')
        parser.add_argument('command')

    def load_manifest(self):
        """Load and parse the manifest."""
        cwd = os.getcwd()
        ymlfile = os.path.join(cwd, '.testmill.yml')
        if not os.access(ymlfile, os.R_OK):
            m = 'Error: project manifest (.testmill.yml) not found.\n'
            self.error(m)
            self.exit(1)
        with file(ymlfile) as fin:
            try:
                manifest = yaml.load(fin)
            except yaml.parser.ParserError as e:
                self.error('Error: illegal YAML in .testmill.yml')
                self.error('Message from parser: {0!s}'.format(e))
        self.manifest = manifest
        self.default_manifest = yaml.load(DEFAULT_MANIFEST)
        return manifest

    def _detect_language(self):
        """Detect the language of a project by looking at a number of files
        that are strong indicators for a particular language."""
        cwd = os.getcwd()
        contents = os.listdir(cwd)
        for fname in contents:
            if fname == 'setup.py':
                return 'python'

    def detect_language(self, manifest):
        """Detect the language of a project in the current working directory."""
        language = manifest.get('language')
        if not language:
            language = self._detect_language()
            if language is not None:
                self.info('Detected a "{0}" project.'.format(language))
            manifest['language'] = language
        elif language not in self.default_manifest.get('language_defaults', {}):
            m = 'Warning: unknown language "{0}" specified in manifest.'
            self.error(m.format(language))

    def check_and_explode_manifest(self, manifest):
        """Check the manifest semantical errors and explode it at the same
        time. NOTE: updates `manifest`."""
        # move application definitions under the "applications" key
        manifest.setdefault('applications', {})
        for key,value in list(manifest.items()):
            if isinstance(value, dict) and ('vm' in value
                    or 'application' in value or 'blueprint' in value):
                manifest['applications'][key] = value
                del manifest[key]
        # Explode application definitions
        for name,appdef in list(manifest['applications'].items()):
            if 'vm' not in appdef:
                m = 'Error: application "{0}" does not define key "vm"'
                self.error(m.format(name))
                self.exit(1)
            appname = appdef.get('application')
            bpname = appdef.get('blueprint')
            if appname is not None and bpname is not None:
                m = 'Error: application "{0}": cannot specify both ' \
                    '"application" and "blueprint".'
                self.error(m.format(name))
                self.exit(1)
            if appname is not None and self.args.new:
                m = 'Warning: application "{0}": ignoring --new'
                self.error(m.format(name))
            if 'name' not in appdef:
                appdef['name'] = name
            for taskname in DEFAULT_TASKS:
                taskdef = appdef.get(taskname)
                if taskdef is None:
                    taskdef = appdef[taskname] = {}
                elif isinstance(taskdef, list):
                    taskdef = appdef[taskname] = { 'commands': taskdef }
                elif isinstance(taskdef, str):
                    taskdef = appdef[taskname] = { 'task': taskdef }
                elif not isinstance(taskdef, dict):
                    m = 'Error: application "{0}": key "{1}" must be list, ' \
                        'str or dict.'
                    self.error(m.format(name, taskname))
                    self.exit(1)
        # Merge in default settings
        language = manifest['language']
        defaults = self.default_manifest.get('defaults', {})
        language_defaults = self.default_manifest.get('language_defaults', {}) \
                                    .get(language, {})
        for name,appdef in list(manifest['applications'].items()):
            util.merge(appdef, language_defaults)
            util.merge(appdef, defaults)
        # Insert global defaults
        for name,appdef in list(manifest['applications'].items()):
            for taskname in DEFAULT_TASKS:
                taskdef = appdef.get(taskname)
                taskdef.setdefault('task', 'testmill.run:Task')
                taskdef.setdefault('local', False)
                taskdef.setdefault('sudo', False)

    def check_referenced_entities_in_manifest(self, manifest):
        """Check the manifest to make sure all referenced entities exist."""
        for name,appdef in manifest['applications'].items():
            vmname = appdef['vm']
            image = self.get_image(name=vmname)
            if image is None:
                m = "Error: Unknown vm '{0}' in application '{1}'"
                self.error(m.format(vmname, name))
                self.exit(1)
            appname = appdef.get('application')
            if appname is not None:
                app = self.get_application(name=appname)
                if app is None:
                    m = 'Error: application "{0}": unknown application: {1}'
                    self.error(m.format(name, appname))
                    self.exit(1)
            bpname = appdef.get('blueprint')
            if bpname is not None:
                bp = self.get_blueprint(name=bpname)
                if bp is None:
                    m = 'Error: application "{0}": unknown blueprint: {1}'
                    self.error(m.format(name, bpname))
                    self.exit(1)
            for taskname,taskdef in appdef.items():
                if isinstance(taskdef, dict) and 'task' in taskdef:
                    if not util.load_class(taskdef['task']):
                        m = "Error: application '{0}': task '{1}' not found."
                        self.error(m.format(name, taskdef['task']))
                        self.exit(1)

    VM_STATE_PREFERENCES = ['STARTED', 'STARTING', 'STOPPED', 'PUBLISHING']

    def _reuse_single_vm_application(self, appdef):
        """Try to re-use a single VM application."""
        image = self.get_image(name=appdef['vm'])
        candidates = []
        for app in self.applications:
            base, suffix = util.splitname(app['name'])
            if base != appdef['name'] or not suffix:
                continue
            app = self.get_full_application(app['id'])
            vms = app['applicationLayer']['vm']
            if len(vms) == 1 and vms[0]['shelfVmId'] == image['id']:
                state = vms[0]['dynamicMetadata']['state']
                if state in ('PUBLISHING', 'STARTING', 'STARTED', 'STOPPED'):
                    candidates.append((state, app, vms[0]))
        if not candidates:
            return
        candidates.sort(key=lambda x: self.VM_STATE_PREFERENCES.index(x[0]))
        state, app, vm = candidates[0]
        m = 'Re-using {0} application "{1}" for "{2}"'
        self.info(m.format(state.lower(), app['name'], appdef['name']))
        if state == 'STOPPED':
            self.api.start_vm(app, vm)
        return app['id']

    def _create_new_single_vm_application(self, appdef):
        """Create a new single VM application."""
        image = self.get_image(name=appdef['vm'])
        image = self.get_full_image(image['id'])
        vm = ravello.update_luids(image)
        app = ravello.Application()
        name = util.get_unused_name(appdef['name'], self.applications)
        app['name'] = name
        app['applicationLayer'] = { 'vm': [ vm ] }
        app = self.api.create_application(app)
        self.api.publish_application(app)
        self.get_full_application(app['id'], force_reload=True)
        m = 'Created new application "{0}" for "{1}"'
        self.info(m.format(app['name'], appdef['name']))
        return app['id']

    def start_applications(self, manifest):
        """Start up all applications."""
        appmap = {}  # { appid: manifest_name }
        for name,appdef in manifest['applications'].items():
            vmname = appdef['vm']
            appname = appdef.get('application')
            bpname = appdef.get('blueprint')
            if appname is None and bpname is None:
                appid = None
                if not self.args.new:
                    appid = self._reuse_single_vm_application(appdef)
                if appid is None:
                    appid = self._create_new_single_vm_application(appdef)
            else:
                # TODO: applications and blueprints
                continue
            appmap[appid] = name
        return appmap

    def wait_until_applications_are_up(self, appmap, timeout, poll_timeout):
        """Wait until all the application are started."""
        end_time = time.time() + timeout
        states = [ 'PUBLISHING', 'STARTING', 'STARTED' ]
        vmmap = {}  # { vmid: appid }
        addrmap = {}  # { host_or_ip: vmid }
        waitapps = set(appmap)
        while True:
            if time.time() > end_time:
                break
            self.reload_cache(applications=True)
            min_state = 2
            for appid in list(waitapps):  # updating
                app = self.get_application(appid)
                app_min_state = 2
                for status in app['cloudVmsStatusCounters']:
                    state = status['status']
                    if state in states:
                        state = states.index(state)
                    else:
                        state = -1
                    app_min_state = min(app_min_state, state)
                if app_min_state == 2:
                    # Update application state here. This way we can do it
                    # while we are waiting anyway.
                    app = self.get_full_application(appid, force_reload=True)
                    for vm in app['applicationLayer']['vm']:
                        addr = vm['dynamicMetadata']['externalIp']
                        addrmap[addr] = vm['id']
                        vmmap[vm['id']] = appid
                    waitapps.remove(appid)
                min_state = min(min_state, app_min_state)
            if not waitapps:
                break
            if min_state == -1:
                self.progress('?')
            elif min_state == 0:
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
            m = 'Continue with failed applications: {0}'
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
                    if e.errno != errno.EINPROGRESS:
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
            self.error(m.format(len(addrs)-len(alive), len(addrs)))
        elif len(alive) == 0:
            self.error('Error: no VM came up, exiting')
            self.exit(1)
        return alive

    def setup_fabric_environment(self, appmap, vmmap, addrmap):
        """Set up the fabric environment."""
        fab.env.appmap = appmap
        fab.env.vmmap = vmmap
        fab.env.addrmap = addrmap
        fab.env.hosts = list(addrmap)
        # TODO: change to use pubkey based authentication
        fab.env.user = 'ravello'
        fab.env.password = 'ravelloCloud'
        # Suppress output for most actions
        fab.env.output_prefix = self.args.debug
        fabric.state.output.running = self.args.debug
        fabric.state.output.output = self.args.debug
        fabric.state.output.status = self.args.debug
        fab.env.COMMAND = self.args.command
        # Create distribution directories.
        tmpdir = tempfile.mkdtemp()
        distbase = os.urandom(16).encode('hex')
        distdir = os.path.join(tmpdir, distbase)
        os.makedirs(distdir)
        fab.env.DISTBASE = distbase
        fab.env.DISTDIR = distdir
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

        # Expand from shorthand .testmill.yml notation to full notation.
        # Also check for missing or conflicting keys.
        self.check_and_explode_manifest(manifest)

        # Some more argument parsing
        if args.dump:
            util.pprint(manifest)
            self.exit(0)
        if args.applications:
            apps = [app.lower() for app in args.applications.split(',')]
            for name in list(manifest['applications']):
                if name.lower() not in apps:
                    del manifest['applications'][name]
        if not manifest['applications']:
            self.error('No applications defined, exiting.')
            self.exit(1)

        # Load images, applications and blueprints
        self.load_cache()

        # Check for referenced entities that are unknown
        self.check_referenced_entities_in_manifest(manifest)

        # Ready to go...
        appnames = ', '.join(manifest['applications'])
        self.info('Applications to run: {0}'.format(appnames))

        # Start up the applications.
        appmap = self.start_applications(manifest)

        # Wait until the applications are up.. And show some progress.
        vmmap, addrmap = self.wait_until_applications_are_up(appmap, 600, 10)
        self.wait_until_vms_accept_ssh(addrmap, 300, 5)
        if hasattr(self, 'progress_bar_started'):
            self.progress('DONE\n')

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
        fab.env.cwd = fab.env.DISTBASE

        # The main command is run serially so that we can show output in a
        # sensible way.
        self.info('Executing command: {0}\n'.format(args.command))
        fabric.state.output.output = True
        for host in fab.env.hosts:
            name = appmap[vmmap[addrmap[host]]]
            self.write("== Output for '{0}' on '{1}'\n".format(args.command, name))
            task = get_task('execute', manifest, host)
            fabric.tasks.execute(task, hosts=[host])
            self.write('')

        # cleanup + shutdown: in parallel again
        #fabric.state.output.output = False
        #close_actions = ('cleanup', 'free')
        #fabric.tasks.execute(run_tasks, close_actions, manifest)

        fabric.network.disconnect_all()
        self.exit(0)
