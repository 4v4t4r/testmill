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
import textwrap
import hashlib
import yaml

from . import main, ravello, util

import fabric
import fabric.api as fab

DEFAULT_TASKS = frozenset(('pack', 'renew', 'sysinit', 'copy', 'unpack',
        'prepare', 'execute', 'cleanup'))


def get_task(name, manifest, host):
    """Load a task from a manifest."""
    envname = fab.env.host_info[host][4]
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
        fab.sudo("atrm `atq | awk '{print $1}'` 2>/dev/null || true")


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
        fab.run('mkdir %s' % fab.env.testid)
        for glob in self.files:
            fab.put(glob, fab.env.testid)


class UnpackTask(Task):
    """Unpack the project into the current working directory."""

    def run(self):
        with fab.cd(fab.env.testid):
            super(UnpackTask, self).run()


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
        ret = fab.run('test -f {}'.format(name), warn_only=True, quiet=True)
        if ret.succeeded:
            return
        super(SysinitTask, self).run(sudo=True)
        fab.run('touch {}'.format(name))


class PrepareTask(Task):
    """Prepare a VM for running the tests."""

    def run(self):
        with fab.cd(fab.env.testid):
            super(PrepareTask, self).run()


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
        vmid, _, appid, _, envname = fab.env.host_info[fab.env.host]
        # TODO: shutdown multi-vm apps
        delay = min(90, self.manifest[envname]['keep'])
        url = '%s/deployment/app/%d/vm/%s/stop' % (fab.env.api_url, appid, vmid)
        cmd = 'curl --cookie %s --request POST %s; ' % (fab.env.api_cookie, url)
        cmd += 'shutdown -h now'
        cmd = 'echo "%s" | at "now + %d minutes"' % (cmd, delay)
        fab.sudo(cmd, quiet=True)

    def run(self):
        self.schedule_shutdown()
        with fab.cd(fab.env.testid):
            super(ExecuteTask, self).run()


class CleanupTask(Task):
    """Finalize the run."""


class RunCommand(main.SubCommand):
    """The "ravello run" command."""

    name = 'run'
    usage = textwrap.dedent("""\
            usage: ravtest [OPTION]... run [<command>]
            """)
    description = textwrap.dedent("""\
            Run a command in one or more Ravello applications.  The
            applications are specified in the  manifest (.ravello.yml) .

            The available options are:
                -E <environments>, --environments <envlist>
                    Only run the command on these applications.
                    <envlist> is a comma-separated list of names
                -c, --continue
                    Continue running even after an error
                --new
                    Never re-use existing applications
                --dump
                    Dump the manifest and exit
            """)

    def add_args(self, parser, level=None):
        parser.add_argument('--environments', '-E')
        parser.add_argument('--continue', '-c', action='store_true',
                            dest='continue_')
        parser.add_argument('--new', action='store_true')
        parser.add_argument('--dump', action=parser.store_and_abort,
                            nargs=0, default=False, const=True)
        parser.add_argument('command', nargs='?')

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
        if 'language_defaults' in manifest:
            del manifest['language_defaults']
        return manifest

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

    def _reuse_existing_application(self, envdef):
        """Try to re-use an existing application."""
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
        if state == 'STOPPED':
            self.api.start_vm(app, vm)
        return app

    def _create_new_application(self, envdef):
        """Create a new application."""
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
        return app

    def start_applications(self, manifest, force_new=False):
        """Start up all applications."""
        apps = []
        for name in manifest['environments']:
            envdef = manifest[name]
            vmname = envdef['vm']
            app = None
            if not force_new:
                app = self._reuse_existing_application(envdef)
                if app is not None:
                    state = self.get_application_state(app)
                    self.info("Re-using {} application '{}' for '{}'."
                                .format(state.lower(), app['name'],
                                        envdef['name']))
            if app is None:
                app = self._create_new_application(envdef)
                if app is not None:
                    self.info("Created new application '{}' for '{}'."
                                .format(app['name'], envdef['name']))
            if app is not None:
                apps.append(app)
        self.applications = apps
        return apps

    def setup_fabric(self):
        """Set up a default fabric configuration."""
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
        fab.env.command = self.args.command
        # Remote distribution directory.
        testid = os.urandom(16).encode('hex')
        fab.env.testid = testid
        # Export API connection info (to schedule in-guest shutdown)
        fab.env.api_url = self.api.url
        fab.env.api_cookie = self.api._cookie

    def run(self, args):
        """The "ravello run" command."""
        
        # Get a manifest

        manifest = self.load_manifest()
        self.detect_language(manifest)
        manifest = self.check_and_explode_manifest(manifest)

        # Some more argument parsing

        if args.dump:
            self.stdout.write(util.prettify(manifest))
            self.exit(0)

        if args.environments:
            envs = [env.lower() for env in args.environments.split(',')]
            manifest['environments'] = [env for env in manifest['environments']
                                        if env.lower() in envs]
        if not manifest['environments']:
            self.error('No environments defined, exiting.')
            self.exit(1)

        self.load_cache()
        self.check_referenced_entities_in_manifest(manifest)

        # Start applications and wait until they are UP and reachable via ssh.

        names = ', '.join(manifest['environments'])
        self.info('Environments to run: {0}.'.format(names))

        self.check_keypair()
        apps = self.start_applications(manifest)

        self.start_progress_bar(textwrap.dedent("""\
            Waiting until applications are ready...
            Progress: 'P' = Publishing, 'S' = Starting, 'C' = Connecting
            ===> """))

        alive = self.wait_until_applications_are_up(apps)
        if len(alive) == 0:
            self.error('Error: no application could be started up, exiting.')
            self.exit(1)
        if len(alive) < len(apps):
            aliveids = [ app['id'] for app in alive ]
            failed = [util.splitname(app['name'])[0]
                        for app in apps
                            if app['id'] not in aliveids]
            self.error(textwrap.dedent("""\
                    Error: Could not start {} out of {} applications.
                    Continue without failed applications: {}."""
                        .format(len(failed), len(apps), ', '.join(failed))))

        reachable = self.wait_until_applications_accept_ssh(alive)
        if len(reachable) == 0:
            self.errro('Error: No applications can be reached, exiting.')
            self.exit(1)
        if len(reachable) < len(alive):
            reachableids = [ app['id'] for app in reachable ]
            unreachable = [util.splitname(app['name'])[0]
                            for app in apps
                                if app['id'] not in reachableids]
            self.error(textwrap.dedent("""\
                    Error: Could not start {0} out of {1} applications.
                    Continue without unreachable applications: {}."""
                        .format(len(unreachable), len(alive),
                                ', '.join(unreachable))))

        self.end_progress_bar('DONE')

        # Now run the tasks...
        
        hosts = []
        host_info = {}
        for app in reachable:
            for vm in app['applicationLayer']['vm']:
                try:
                    keypair = vm['customVmConfigurationData']['keypair']
                except KeyError:
                    continue
                ipaddr = vm['dynamicMetadata']['externalIp']
                hosts.append(ipaddr)
                host_info[ipaddr] = (vm['id'], vm['name'],
                                     app['id'], app['name'],
                                     util.splitname(app['name'])[0])
        self.setup_fabric()
        fab.env.hosts = hosts
        fab.env.host_info = host_info

        # pack is local only
        anyhost = [hosts[0]]
        fabric.tasks.execute(run_task, 'pack', manifest, hosts=anyhost)

        # Start parallel processing. Minimize forks by running as many actions
        # in a single composite task.
        #fab.env.parallel = len(fab.env.hosts) > 1 and not args.debug
        fab.env.parallel = False
        init_actions = ('renew', 'sysinit', 'copy', 'unpack', 'prepare')
        fabric.tasks.execute(run_tasks, init_actions, manifest)
        # Communicate new working directory..
        #fab.env.cwd = fab.env.testid

        # The main command is run serially so that we can show output in a
        # sensible way.
        fabric.state.output.output = True
        for host in fab.env.hosts:
            task = get_task('execute', manifest, host)
            envname = host_info[host][4]
            if len(task.commands) > 1:
                command = '{}; ...'.format(tasks.commands[0])
            else:
                command = task.commands[0]
            self.stdout.write("\n== Output for '{}' on '{}':\n\n"
                              .format(command, envname))
            fabric.tasks.execute(task, hosts=[host])
            self.stdout.write('\n')

        # cleanup + shutdown: in parallel again
        #fabric.state.output.output = False
        #close_actions = ('cleanup', 'free')
        #fabric.tasks.execute(run_tasks, close_actions, manifest)

        fabric.network.disconnect_all()
        self.exit(0)
