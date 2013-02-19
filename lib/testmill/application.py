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

from __future__ import absolute_import

import sys
import time
import socket
import select
import errno
import textwrap
import copy
from functools import reduce

from testmill import (cache, console, keypair, util, ravello, error,
                      manifest, inflect)
from testmill.state import env


# Starting and waiting for applications ..

vm_ordered_states = ['PUBLISHING', 'STOPPED', 'STARTING', 'STARTED']

def combine_states(state1, state2):
    """Combine two VM states `state1` and `state2` into a single state.

    If both states are known, the combined state is the minimum state
    according to the vm_ordered_states ordering. If one state is unknown,
    it is the unknown state.
    """
    try:
        index1 = vm_ordered_states.index(state1)
    except ValueError:
        return state1
    try:
        index2 = vm_ordered_states.index(state2)
    except ValueError:
        return state2
    return vm_ordered_states[min(index1, index2)]


def start_application(app):
    """Start up all stopped VMs in an application."""
    vms = app['applicationLayer']['vm']
    for vm in vms:
        if vm['dynamicMetadata']['state'] == 'STOPPED':
            env.api.start_vm(app, vm)


def get_application_state(app):
    """Return the state of an application.
    
    The state is obtained by reducing the states of all the application VMs
    using ``combine_states()``.
    """
    vms = app['applicationLayer'].get('vm', [])
    if not vms:
        return 'DRAFT'
    states = map(lambda vm: vm['dynamicMetadata']['state'] \
                        if vm.get('dynamicMetadata') else 'DRAFT', vms)
    state = reduce(combine_states, states)
    return state


def wait_until_application_is_up(app, timeout=900, poll_timeout=10):
    """Wait until an application is UP.

    An application is up if all its VMs are in the 'STARTED' state. 
    """
    end_time = time.time() + timeout
    while True:
        if time.time() > end_time:
            break
        poll_end_time = time.time() + poll_timeout
        app = cache.get_full_application(app['id'], force_reload=True)
        state = get_application_state(app)
        if state == 'STARTED':
            return
        console.show_progress(state[0])
        time.sleep(max(0, poll_end_time - time.time()))
    error.raise_error("Application `{0}` did not come up within {1} seconds.",
                      app['name'], timeout)


nb_connect_errors = set((errno.EINPROGRESS,))
if sys.platform.startswith('win'):
    nb_connect_errors.add(errno.WSAEWOULDBLOCK)

def wait_until_application_accepts_ssh(app, vms, timeout=300, poll_timeout=5):
    """Wait until an application is reachable by ssh.

    An application is reachable by SSH if all the VMs that have a public key in
    their userdata are connect()able on port 22. 
    """
    waitaddrs = set((vm['dynamicMetadata']['externalIp']
                     for vm in app['applicationLayer']['vm']
                     if vm['name'] in vms))
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
                if e.errno not in nb_connect_errors:
                    console.debug('connect(): errno {.errno}'.format(e))
                    continue
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
                console.debug('select(): errno {.errno}'.format(e))
                raise
            for fd in wfds:
                assert fd in waitfds
                sock, addr = waitfds[fd]
                try:
                    error = sock.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
                except socket.error as e:
                    error = e.errno
                sock.close()
                if not error:
                    aliveaddrs.add(addr)
                    waitaddrs.remove(addr)
                del waitfds[fd]
            if not waitfds:
                break
        if not waitaddrs:
            return
        console.show_progress('C')  # 'C' = Connecting
        time.sleep(max(0, poll_end_time - time.time()))
    unreachable = set((vm['name'] for vm in app['applicationLayer']['vm']
                       if vm['dynamicMetadata']['externalIp'] in waitaddrs))
    noun = inflect.plural_noun('VM', len(unreachable))
    vmnames = '`{0}`'.format('`, `'.join(sorted(unreachable)))
    error.raise_error('{0} `{1}` did not become reachable within {2} seconds.',
                      noun, vmnames, timeout)


vm_reuse_states = ['STARTED', 'STARTING', 'STOPPED', 'PUBLISHING']

def reuse_existing_application(appdef):
    """Try to re-use an existing application."""
    candidates = []
    pubkey = env.public_key
    if appdef.get('blueprint'):
        blueprint = cache.get_blueprint(name=appdef['blueprint'])
        blueprint = cache.get_full_blueprint(blueprint['id'])
    else:
        blueprint = None
    project = env.manifest['project']
    for app in cache.get_applications():
        parts = app['name'].split(':')
        if len(parts) != 3:
            continue
        if parts[0] != project['name'] or parts[1] != appdef['name']:
            continue
        app = cache.get_full_application(app['id'])
        vms = app['applicationLayer'].get('vm', [])
        if not vms:
            continue
        state = get_application_state(app)
        if state not in vm_reuse_states:
            continue
        if blueprint and blueprint['name'] != app.get('blueprintName'):
            continue
        vmsfound = []
        for vmdef in appdef['vms']:
            for vm in vms:
                if vm['name'] == vmdef['name']:
                    break
            if not blueprint:
                image = cache.get_image(name=vmdef['image'])
                if not image:
                    continue
                if vm['shelfVmId'] != image['id']:
                    continue
            userdata = vm.get('customVmConfigurationData', {})
            keypair = userdata.get('keypair')
            if keypair.get('id') != pubkey['id']:
                continue
            vmsfound.append(vmdef['name'])
        if len(vmsfound) != len(appdef['vms']):
            continue
        candidates.append((state, app))
    if not candidates:
        return
    candidates.sort(key=lambda x: vm_reuse_states.index(x[0]))
    return candidates[0][1]


def create_new_vm(vmdef):
    image = cache.get_image(name=vmdef['image'])
    image = cache.get_full_image(image['id'])
    image = copy.deepcopy(image)
    vm = ravello.update_luids(image)
    vm['name'] = vmdef['name']
    vm['customVmConfigurationData'] = { 'keypair': env.public_key }
    vm['hostname'] = [ vmdef['name'] ]
    vm['numCpus'] = vmdef['smp']
    vm['memorySize'] = { 'unit': 'MB', 'value': vmdef['memory'] }
    vm.setdefault('suppliedServices', [])
    for svcdef in vmdef.get('services', []):
        if isinstance(svcdef, int):
            port = str(svcdef)
            svcdef = 'port-{0}'.format(svcdef)
        else:
            port = socket.getservbyname(svcdef)
        svc = { 'globalService': True, 'id': ravello.random_luid(),
                'ip': None, 'name': svcdef, 'portRange': port,
                'protocol': 'ANY_OVER_TCP' }
        vm['suppliedServices'].append({'baseService': svc})
    return vm


def create_new_application(appdef):
    """Create a new application based on ``appdef``."""
    project = env.manifest['project']
    template = '{0}:{1}'.format(project['name'], appdef['name'])
    name = util.get_unused_name(template, cache.get_applications())
    app = { 'name': name }
    bpname = appdef.get('blueprint')
    if bpname:
        blueprint = cache.get_blueprint(name=bpname)
        app = env.api.create_application(app, blueprint)
        app = cache.get_full_application(app['id'])
        for vm in get_vms(app):
            vm.setdefault('customVmConfigurationData', {})
            vm['customVmConfigurationData']['keypair'] = env.public_key
    else:
        vms = []
        for vmdef in appdef.get('vms', []):
            vm = create_new_vm(vmdef)
            vms.append(vm)
        app['applicationLayer'] = { 'vm': vms }
        app = env.api.create_application(app)
    req = { 'prefferedCloud': 'AMAZON' }  # sic.
    env.api.publish_application(app, req)
    app = cache.get_full_application(app['id'], force_reload=True)
    return app


def create_or_reuse_application(appdef, force_new):
    """Create a new application or re-use a suitable existing one."""
    app = None
    if not force_new:
        app = reuse_existing_application(appdef)
        if app is not None:
            state = get_application_state(app)
            parts = app['name'].split(':')
            console.info('Re-using {0} application `{1}:{2}`.',
                         state.lower(), parts[1], parts[2])
            start_application(app)
    if app is None:
        app = create_new_application(appdef)
        parts = app['name'].split(':')
        console.info('Created new application `{1}:{2}`.', *parts)
        console.info('Published to {0[cloud]}/{0[regionName]}.', app)
    return app


def wait_for_application(app, vms):
    """Wait until an is UP and connectable over ssh."""
    console.start_progressbar(textwrap.dedent("""\
        Waiting until application is ready...
        Progress: 'P' = Publishing, 'S' = Starting, 'C' = Connecting
        ===> """))
    # XXX: At first boot cloud-init deploys our authorized keys file.
    # This process can finish after ssh has started up. The images
    # need to be fixed to ensure cloud-init has finished before ssh
    # starts up.
    state = get_application_state(app)
    extra_sleep = 30 if state == 'PUBLISHING' else 0
    console.debug('State {0}, extra sleep {1}.', state, extra_sleep)
    wait_until_application_is_up(app)
    app = cache.get_full_application(app['id'])
    wait_until_application_accepts_ssh(app, vms)
    console.end_progressbar('DONE')
    app = cache.get_full_application(app['id'])
    time.sleep(extra_sleep)
    return app


def get_vm(application, vmname):
    """Return the VM ``vmname`` from application ``application``."""
    for vm in application.get('applicationLayer', {}).get('vm', []):
        if vm.get('name') == vmname:
            return vm

def get_vms(application):
    return application.get('applicationLayer', {}).get('vm', [])


def default_application(appname):
    """The default application loading function."""
    parts = appname.split(':')
    if len(parts) in (1, 2) and env.manifest is None:
        error.raise_error('No manifest found ({0}).\n'
                          'Please specify the fully qualified app name.\n'
                          "Use 'ravtest ps -a' for a list.",
                          manifest.manifest_name())
    if len(parts) in (1, 2):
        project = env.manifest['project']['name']
        console.info('Project name is `{0}`.', project)
        defname = parts[0]
        instance = parts[1] if len(parts) == 2 else None
    elif len(parts) == 3:
        project, defname, instance = parts
    else:
        error.raise_error('Illegal application name: `{0}`.', appname)

    apps = cache.get_applications(project, defname, instance)
    if len(apps) == 0:
        error.raise_error('No instances of application `{0}` exist.',
                          defname)
    elif len(apps) > 1:
        error.raise_error('Multiple instances of `{0}` exist.\n'
                          'Use `ravtest ps` to list the instances and then\n'
                          'specify the application with its instance id.',
                          defname)
    app = cache.get_full_application(apps[0]['id'])
    return app
