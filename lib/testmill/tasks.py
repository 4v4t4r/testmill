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
import time
import stat
import tarfile
import hashlib
import multiprocessing
import traceback

import fabric.state
import fabric.tasks
import fabric.network
import fabric.api as fab

import testmill
from testmill import console, versioncontrol, util, error, inflect, console
from testmill.state import env

if sys.version_info[0] == 3:
    import io
else:
    import StringIO as io


def run_all_tasks(app, vms):
    """Run the runbook for an application ``app``."""
    hosts = []
    host_info = {}
    appname = app['name'].split(':')[1]
    for appdef in env.manifest['applications']:
        if appdef['name'] == appname:
            break
    else:
        error.raise_error('Application definition not found?')

    for vm in app['applicationLayer']['vm']:
        if vm['name'] not in vms:
            continue
        ipaddr = vm['dynamicMetadata']['externalIp']
        hosts.append(ipaddr)
        host_info[ipaddr] = vm['name']

    env.test_id = os.urandom(16).encode('hex')
    console.info('Starting run `{0}`.', env.test_id)
    env.host_info = host_info
    env.start_time = int(time.time())
    env.lock = multiprocessing.Lock()
    manager = multiprocessing.Manager()
    env.shared_state = manager.dict()
    for vmname in vms:
        vmstate = {}
        vmstate['exited'] = False
        vmstate['completed_tasks'] = {}
        vmstate['shell_env_update'] = {}
        env.shared_state[vmname] = vmstate
    env.appdef = appdef
    env.application = app
    env.vms = vms

    fab.env.user = 'ravello'
    fab.env.key_filename = env.private_key_file
    fab.env.disable_known_hosts = True
    fab.env.remote_interrupt = True
    fab.env.hosts = hosts
    fab.env.parallel = True
    fab.env.output_prefix = env.debug
    fabric.state.output.running = env.debug
    fabric.state.output.output = True
    fabric.state.output.status = env.debug

    # This is where it all happens...
    noun = inflect.plural_noun('virtual machine', len(vms))
    console.info('Executing tasks on {0} {1}...', len(vms), noun)

    fabric.tasks.execute(run_tasklist, env)

    errors = set()
    for vmname in vms:
        vmstate = env.shared_state[vmname]
        for taskname,status in vmstate['completed_tasks'].items():
            if status != 0:
                errors.add('`{0}` on `{1}`'.format(taskname, vmname))

    if not errors:
        console.info('All tasks were executed succesfully!')
    else:
        what = inflect.plural_noun('task', len(errors))
        errapps = ', '.join(errors)
        console.error('The following {0} failed: {1}', what, errapps)

    fabric.network.disconnect_all()
    return len(errors)


def preinit():
    """Prepare the VM before any tasks are run."""
    packagedir = testmill.packagedir()
    fname = os.path.join(packagedir, 'preinit.sh')
    with file(fname) as fin:
        script = fin.read()
    shutdown_urls = []
    url_template = '{0}/deployment/app/{1}/vm/{2}/stop'
    app = env.application
    myself_last = sorted(app['applicationLayer']['vm'],
                         key=lambda vm: vm['id'] != env.vm['id'])
    for vm in myself_last:
        url = url_template.format(env.api.url, app['id'], vm['id'])
        shutdown_urls.append(url)
    shutdown_urls = ' '.join(map(util.shell_escape, shutdown_urls))
    keepalive = env.appdef.get('keepalive', 50)
    script = script.format(test_id=env.test_id, keepalive=keepalive,
                           api_cookie=env.api._cookie,
                           shutdown_urls=shutdown_urls)
    script_name = '{0}.preinit'.format(env.test_id)
    fab.put(io.StringIO(script), script_name)
    command = 'exec $SHELL {0}'.format(script_name)
    fab.run(command, shell=False, pty=True, quiet=not env.debug)


def show_output(task):
    """Show output for a completed task."""
    if task.interactive:
        return
    if task.quiet and not env.debug:
        return
    output = task.stdout
    if (not output or output.isspace()) and not env.debug:
        return
    console.writeln('\n== Output for task `{0}` on VM `{1}`:\n',
                    task.name, env.vm['name'])
    console.writeln(output)
    console.writeln()


def synchronize_on_task(taskname, timeout=600):
    """Wait until all instances of ``taskname`` have completed.
    Returns a dictionary with the shared state of the VMs that
    were waited for.
    """
    waitfor = set()
    for vmdef in env.appdef['vms']:
        if vmdef['name'] not in env.vms:
            continue
        for taskdef in vmdef['tasks']:
            if taskdef['name'] == taskname:
                waitfor.add(vmdef['name'])
    state = {}
    end_time = time.time() + timeout
    while True:
        for vmdef in env.appdef['vms']:
            vmname = vmdef['name']
            vmstate = env.shared_state[vmname]  # resync
            if vmstate['exited']:
                state[vmname] = vmstate
                break
            if vmname not in waitfor:
                continue
            if taskname in vmstate['completed_tasks']:
                waitfor.remove(vmname)
                state[vmname] = vmstate
        if vmstate['exited'] or not waitfor:
            break
        console.debug('Waiting for %s' % repr(waitfor))
        time.sleep(5)
        if time.time() > end_time:
            error.raise_error("Timeout waiting for task `{0}`.", taskname)
    return state


@fab.task
def run_tasklist(passed_env):
    """Run the task list for the current host.

    This function runs in a separate process, that is spawned by the
    ``multiprocessing`` module that Fabric uses for its parallel execution.

    The ``passed_env`` argument is the environment as it was passed through by
    our parent. This is required for Windows that does not have ``fork()`` and
    therefore we need to re-initialize the environment.
    """
    env.update(passed_env)
    host = fab.env.host_string
    fab.env.hosts = [host]
    fab.env.parallel = False
    vmname = env.host_info[host]
    appname = env.appdef['name']

    for vmdef in env.appdef['vms']:
        if vmdef['name'] == vmname:
            break
    for vm in env.application['applicationLayer']['vm']:
        if vm['name'] == vmname:
            break

    env.vm = vm
    shell_env = env.shell_env = {}
    shell_env['RAVELLO_TEST_ID'] = env.test_id
    shell_env['RAVELLO_TEST_USER'] = 'ravello'
    shell_env['RAVELLO_APP_ID'] = env.application['id']
    shell_env['RAVELLO_APP_NAME'] = env.application['name']
    shell_env['RAVELLO_APPDEF_NAME'] = env.appdef['name']
    shell_env['RAVELLO_PROJECT'] = env.api._project
    shell_env['RAVELLO_SERVICE_URL'] = env.api.url
    shell_env['RAVELLO_SERVICE_COOKIE'] = env.api._cookie
    shell_env['RAVELLO_VM_ID'] = vm['id']
    shell_env['RAVELLO_VM_NAME'] = vm['name']

    def debug(message, *args, **kwargs):
        message = message.format(*args, **kwargs)
        console.debug('[VM {0}] {1}', vmname, message)

    debug('Running task list for `{0}`', host)

    try:
        debug('Pre-initialize VM')
        preinit()

        sync_task = None
        for taskdef in vmdef['tasks']:
            debug('Running task `{0}`.', taskdef['name'])
            env.shell_env['RAVELLO_TASK_NAME'] = taskdef['name']

            clsname = taskdef.get('class', 'testmill.tasks.Task')
            cls = util.load_class(clsname)
            task = cls(**taskdef)

            vmstate = env.shared_state[vmname]
            vmstate['current_task'] = task.name
            env.shared_state[vmname] = vmstate  # sync shared state

            if sync_task:
                debug('Sync state on task `{0}`.', sync_task)
                completed = synchronize_on_task(sync_task)
                for name,state in completed.items():
                    if state['exited']:
                        break
                    update = state['shell_env_update'].get(sync_task)
                    if update:
                        debug('Updated {0} environment vars.', len(update))
                        env.shell_env.update(update)
                if completed and state['exited']:
                    debug('Stopping due to failed task on VM `{0}`.', name)
                    break

            task.run()

            vmstate = env.shared_state[vmname]
            vmstate['completed_tasks'][task.name] = task.return_code
            vmstate['shell_env_update'][task.name] = task.env_update
            if task.return_code != 0 and not env.args.continue_:
                vmstate['exited'] = True
            env.shared_state[vmname] = vmstate  # sync shared state

            with env.lock:
                show_output(task)
            if vmstate['exited']:
                break
            sync_task = taskdef['name']

    except Exception as e:
        with env.lock:
            console.show_exception(e)
        vmstate = env.shared_state[vmname]
        vmstate['exited'] = True
        env.shared_state[vmname] = vmstate  # sync


def create_script(taskname, commands):
    """Create the script to execute ``commands``."""
    packagedir = testmill.packagedir()
    fname = os.path.join(packagedir, 'runtask.sh')
    with file(fname) as fin:
        script = fin.read()
    lines = []
    tmpl = '{0}={1}; export {0}'
    for key,value in env.shell_env.items():
        escaped = util.shell_escape(str(value))
        lines.append(tmpl.format(key, escaped))
    shell_vars = '\n'.join(lines)
    if env.args.continue_:
        tmpl = '{0}\n'
    else:
        tmpl = '{0}\ntest "$?" -ne "0" && exit 1\n'
    shell_commands = '\n'.join([tmpl.format(cmd) for cmd in commands])
    script = script.format(shell_vars=shell_vars,
                           shell_commands=shell_commands)
    return script


def parse_env_update(contents):
    """Parse an env-update file."""
    update = {}
    for line in contents.splitlines():
        p1 = line.find(' ')
        if p1 <= 0:
            continue
        key = line[:p1]
        value = line[p1+1:]
        update[key] = value
    return update


class Task(fabric.tasks.Task):
    """A task from the manifest."""

    def __init__(self, name, **kwargs):
        super(Task, self).__init__()
        self.name = name
        self.user = kwargs.pop('user', None)
        self.commands = kwargs.pop('commands', [])
        if env.verbose:
            self.quiet = False
        else:
            self.quiet = kwargs.pop('quiet', False)
        if env.args.interactive:
            self.interactive = True
        else:
            self.interactive = kwargs.pop('interactive', False)
        for key in kwargs:
            setattr(self, key, kwargs[key])
        self.stdout = ''
        self.env_update = None
        self.return_code = None

    def run(self, commands=None, user=None):
        """Run a remote command through ``fabric.api.run()``.

        Instead of executing the commands directory, we create a script,
        upload it, and execute that. This allows us more control over
        the environment, and is also faster in case many commands are
        executed.
        """
        if commands is None:
            commands = self.commands
        script_name = 'runs/{0}/.ravello/{1}.sh'.format(env.test_id, self.name)
        script = create_script(self.name, commands)
        fab.put(io.StringIO(script), script_name)
        runargs = {'shell': False, 'pty': True, 'warn_only': True}
        show_output = env.debug or (self.interactive and not self.quiet)
        runargs['quiet'] = not show_output
        if user is None:
            user = self.user
        if user:
            invoke = 'sudo -u {user} $SHELL -l {script_name}'
        else:
            invoke = 'exec $SHELL -l {script_name}'
        invoke_args = {'user': user, 'script_name': script_name}
        command = invoke.format(**invoke_args)
        ret = fab.run(command, **runargs)
        self.stdout = ret
        update = io.StringIO()
        remote_name = 'runs/{0}/.ravello/{1}.env-update' \
                    .format(env.test_id, self.name)
        fab.get(remote_name, update)
        update = parse_env_update(update.getvalue())
        self.env_update = update
        self.return_code = ret.return_code


class SysinitTask(Task): 
    """Perform system initalization.

    This task is run exactly once per VM.
    """

    def run(self):
        md = hashlib.sha1()
        for command in self.commands:
            md.update(command + '\000')
        token = md.hexdigest()
        commands = []
        tmpl = 'test -f $RAVELLO_HOME/sysinit/{0}.done && exit 0 || true'
        commands.append(tmpl.format(token))
        commands.extend(self.commands)
        tmpl = 'touch $RAVELLO_HOME/sysinit/{0}.done'
        commands.append(tmpl.format(token))
        super(SysinitTask, self).run(commands=commands, user='root')


def create_archive():
    ravello_dir = util.get_ravello_dir()
    try:
        st = os.stat(ravello_dir)
    except OSError:
        st = None
    if st and not stat.S_ISDIR(st.st_mode):
        error.raise_error("Path `{0}` exists but is not a directory.",
                          ravello_dir)
    elif st is None:
        os.mkdir(ravello_dir)
    distfile = os.path.join(ravello_dir, 'dist.tar.gz')
    try:
        st = os.stat(distfile)
    except OSError:
        st = None
    if st and st.st_mtime >= env.start_time:
        return distfile
    archive = tarfile.TarFile.open(distfile, 'w:gz')
    repotype = env.manifest['repository']['type']
    files = versioncontrol.walk_repository('.', repotype)
    for fname in files:
        if fname.startswith(ravello_dir):
            continue
        archive.add(fname, recursive=False)
    archive.close()
    return distfile


class DeployTask(Task):
    """Deploy the project to the remote VM."""

    def copy_from_local(self):
        with env.lock:
            # Run under the lock to ensure that only one process
            # creates the archive
            distpath = create_archive()
        remote_dir = 'runs/{0}/.ravello'.format(env.test_id)
        fab.put(distpath, remote_dir)
        _, distname = os.path.split(distpath)
        command = 'tar xpfz .ravello/{0}'.format(distname)
        super(DeployTask, self).run(commands=[command])

    def remote_checkout(self, version):
        repotype = env.manifest['repository']['type']
        if not repotype:
            error.raise_error('Unknown repository type, cannot checkout.')
        url = env.manifest['repository']['url']
        commands = versioncontrol.get_checkout_command(url, version, repotype)
        super(DeployTask, self).run(commands=commands)

    def run(self):
        version = getattr(self, 'remote', None)
        if version:
            self.remote_checkout(version)
        else:
            self.copy_from_local()
