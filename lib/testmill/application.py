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

import os
import sys
import time
import socket
import select
import struct
import errno
import textwrap
import copy
import functools

from testmill import (cache, console, keypair, util, ravello, error,
                      manifest, inflect)
from testmill.state import env


# Starting and waiting for applications and blueprints ..

vm_ordered_states = ['PUBLISHING', 'STOPPED', 'STARTING', 'STARTED']
bp_ordered_states = ['SAVING', 'DONE']


def combine_states(state1, state2, ordering):
    """Combine two states *state1* and *state2* into a single state.

    The *ordering* parameter must be a sequence containing the valid states in
    some ordering. The combined state is then the minimum state according this
    ordering. If one of *state1* or *state2* is unknown, the combined state is
    the unknown state.

    This function is useful to know the progress for objects that transition
    one or more intermediary states into a single end state.
    """
    try:
        index1 = ordering.index(state1)
    except ValueError:
        return state1
    try:
        index2 = ordering.index(state2)
    except ValueError:
        return state2
    return ordering[min(index1, index2)]


def start_application(app):
    """Start up all stopped VMs in an application."""
    vms = app['applicationLayer']['vm']
    for vm in vms:
        if vm['dynamicMetadata']['state'] == 'STOPPED':
            env.api.start_vm(app, vm)
    app = cache.get_application(app['id'], force_reload=True)
    return app


def stop_application(app):
    """Stop all started VMs in an application."""
    vms = app['applicationLayer']['vm']
    for vm in vms:
        if vm['dynamicMetadata']['state'] == 'STARTED':
            env.api.stop_vm(app, vm)
    app = cache.get_application(app['id'], force_reload=True)
    return app


def get_application_state(app):
    """Return the state of an application.
    
    The state is obtained by reducing the states of all the application VMs
    using ``combine_states()``.
    """
    vms = app['applicationLayer'].get('vm', [])
    if not vms:
        return 'DRAFT'
    combine = functools.partial(combine_states, ordering=vm_ordered_states)
    states = map(lambda vm: vm['dynamicMetadata']['state'] \
                        if vm.get('dynamicMetadata') else 'DRAFT', vms)
    state = functools.reduce(combine, states)
    return state


def get_blueprint_state(bp):
    """Return the state of a blueprint.
    
    The state is obtained by reducing the states of all the blueprint VMs
    using ``combine_states()``.
    """
    vms = bp['applicationLayer'].get('vm', [])
    if not vms:
        return 'EMPTY'
    combine = functools.partial(combine_states, ordering=bp_ordered_states)
    states = map(lambda vm: vm['loadingStatus'], vms)
    state = functools.reduce(combine, states)
    return state


def new_application_name(template):
    """Return a new application name based on *template*."""
    name = util.get_unused_name(template, cache.get_applications())
    return name


def new_blueprint_name(template):
    """Return a new blueprint name based on *template*."""
    name = util.get_unused_name(template, cache.get_blueprints())
    return name


def wait_until_application_is_in_state(app, state, timeout=None,
                                       poll_timeout=None):
    """Wait until an application is in a given state."""
    if timeout is None:
        timeout = 900
    if poll_timeout is None:
        poll_timeout = 10
    end_time = time.time() + timeout
    while True:
        if time.time() > end_time:
            break
        poll_end_time = time.time() + poll_timeout
        app = cache.get_application(app['id'], force_reload=True)
        appstate = get_application_state(app)
        if appstate == state:
            return app
        console.show_progress(appstate[0])
        time.sleep(max(0, poll_end_time - time.time()))
    error.raise_error("Application `{0}` did not reach state '{1}' within "
                      "{2} seconds.", app['name'], state, timeout)
    return app


def wait_until_blueprint_is_in_state(bp, state, timeout=None,
                                     poll_timeout=None):
    """Wait until a blueprint is in a given state."""
    if timeout is None:
        timeout = 300
    if poll_timeout is None:
        poll_timeout = 5
    end_time = time.time() + timeout
    while True:
        if time.time() > end_time:
            break
        poll_end_time = time.time() + poll_timeout
        bp = cache.get_blueprint(bp['id'], force_reload=True)
        bpstate = get_blueprint_state(bp)
        if bpstate == state:
            return bp
        time.sleep(max(0, poll_end_time - time.time()))
    error.raise_error("Blueprint `{0}` did not reach state '{1}' within "
                      "{2} seconds.", bp['name'], state, timeout)
    return bp


nb_connect_errors = set((errno.EINPROGRESS,))
if sys.platform.startswith('win'):
    nb_connect_errors.add(errno.WSAEWOULDBLOCK)

def wait_until_application_accepts_ssh(app, vms, timeout=None,
                                       poll_timeout=None):
    """Wait until an application is reachable by ssh.

    An application is reachable by SSH if all the VMs that have a public key in
    their userdata are connect()able on port 22. 
    """
    if timeout is None:
        timeout = 300
    if poll_timeout is None:
        poll_timeout = 5
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
                    err = sock.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
                except socket.error as e:
                    err = e.errno
                sock.close()
                if not err:
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
    else:
        blueprint = None
    project = env.manifest['project']
    for app in cache.get_applications():
        parts = app['name'].split(':')
        if len(parts) != 3:
            continue
        if parts[0] != project['name'] or parts[1] != appdef['name']:
            continue
        app = cache.get_application(app['id'])
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


# Ravello OUI = 2C-C2-60
_ravello_base = 0x2cc260

def get_new_mac():
    """Allocate a new Mac address."""
    if not hasattr(env, '_mac_base'):
        start = _ravello_base
        offset = struct.unpack('>i', '\x00' + os.urandom(3))[0]
        env._mac_base = (start << 24) + offset
    # Do not use a random Mac in the Ravello OUI range but instead use a
    # random offset + sequential allocation. The range is too small for
    # random Macs to have a small enough probability not to conflict.
    mac = env._mac_base
    env._mac_base += 1
    if (env._mac_base & 0xffffff) == 0xffffff:
        env._mac_base = _ravello_base
    parts = ['{:02X}'.format((mac >> ((5-i)*8)) & 0xff) for i in range(6)]
    mac = ':'.join(parts)
    return mac


def create_new_vm(vmdef):
    image = cache.get_image(name=vmdef['image'])
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
    # Set a fixed Mac. This way applications created from blueprints
    # created from these VMs will have the same Mac.
    # See also https://github.com/ravello/testmill/issues/15
    conn = vm['networkConnections'][0]
    conn['device']['mac'] = get_new_mac()
    conn['device']['useAutomaticMac'] = False
    return vm


def create_new_application(appdef, name_is_template=True):
    """Create a new application based on ``appdef``."""
    if name_is_template:
        project = env.manifest['project']
        template = '{0}:{1}'.format(project['name'], appdef['name'])
        name = util.get_unused_name(template, cache.get_applications())
    else:
        name = appdef['name']
    app = { 'name': name }
    bpname = appdef.get('blueprint')
    if bpname:
        blueprint = cache.get_blueprint(name=bpname)
        app = env.api.create_application(app, blueprint)
        app = cache.get_application(app['id'])  # update cache
    else:
        vms = []
        for vmdef in appdef.get('vms', []):
            vm = create_new_vm(vmdef)
            vms.append(vm)
        app['applicationLayer'] = { 'vm': vms }
        app = env.api.create_application(app)
        app = cache.get_application(app['id'])  # update cache
    return app


def publish_application(app, cloud='AMAZON', region=None):
    """Publish the application ``app``."""
    req = {}
    if cloud:
        req['prefferedCloud'] = cloud  # sic.
    if region:
        req['prefferedRegion'] = region
    env.api.publish_application(app, req)
    app = cache.get_application(app['id'], force_reload=True)
    return app


def remove_application(app):
    """Remove an application."""
    env.api.remove_application(app)
    cache.get_application(app['id'], force_reload=True)


def create_blueprint(bpname, app):
    """Create a new blueprint."""
    bp = env.api.create_blueprint(bpname, app)
    bp = cache.get_blueprint(bp['id'])
    return bp


def remove_blueprint(bp):
    """Remove a blueprint."""
    env.api.remove_blueprint(bp)
    bp = cache.get_blueprint(bp['id'], force_reload=True)  # expunge from cache


def appdef_from_app(app):
    """Turn an application back into ``appdef`` format."""
    appdef = { 'id': app['id'] }
    appdef['name'] = app['name']
    appdef['description'] = app.get('description') or ''
    appdef['state'] = get_application_state(app)
    appdef['cloud'] = app['cloud']
    appdef['region'] = app['regionName']
    vmdefs = appdef['vms'] = []
    for vm in app['applicationLayer'].get('vm', []):
        vmdef = { 'id': vm['id'] }
        vmdef['name'] = vm['name']
        vmdef['description'] = vm.get('description') or ''
        vmdef['smp'] = vm['numCpus']
        vmdef['memory'] = vm['memorySize']['value'] * \
                (1024 if vm['memorySize']['unit'] == 'GB' else 1)
        if vm.get('dynamicMetadata'):
            # otherwise this is a blueprint or a draft app
            vmdef['ip'] = vm['dynamicMetadata']['externalIp']
            vmdef['state'] = vm['dynamicMetadata']['state']
        svcdefs = vmdef['services'] = []
        for svc in vm.get('suppliedServices', []):
            svc = svc.get('baseService')
            if not svc:
                continue
            svcdef = { 'name': svc['name'],
                       'port': int(svc['portRange'].split('-')[0]) }
            svcdefs.append(svcdef)
        vmdefs.append(vmdef)
    return appdef


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
            app = start_application(app)
    if app is None:
        app = create_new_application(appdef)
        app = publish_application(app)
        parts = app['name'].split(':')
        console.info('Created new application `{1}:{2}`.', *parts)
        console.info('Published to {0[cloud]}/{0[regionName]}.', app)
    return app


def wait_for_application(app, vms, timeout=None):
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
    if timeout:
        timeleft = max(120, timeout)  # anything < 120 does not make sense
        start = time.time()
    else:
        timeleft = None
    if state == 'PUBLISHING':
        if timeleft:
            timeleft -= 30
        # Fudge factor. When an application is first started up, ssh needs to
        # create its ssh host keys. In theory this wait should not be necessary
        # as ssh binds to port 22 after creating the host keys. In practise,
        # something doesn't quite work our and it is needed.  Needs more
        # investigation to understand. For now, take the easy way..
        extra_sleep = 30
    else:
        extra_sleep = 0
    console.debug('State {0}, extra sleep {1}.', state, extra_sleep)
    app = wait_until_application_is_in_state(app, 'STARTED', timeleft)
    if timeleft:
        timeleft = max(0, timeleft - (time.time()-start))
    wait_until_application_accepts_ssh(app, vms, timeleft)
    console.end_progressbar('DONE')
    time.sleep(extra_sleep)
    return app


def get_vm(app, vmname):
    """Return the VM ``vmname`` from application ``application``."""
    for vm in app.get('applicationLayer', {}).get('vm', []):
        if vm.get('name') == vmname:
            return vm

def get_vms(app):
    return app.get('applicationLayer', {}).get('vm', [])


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
    apps = cache.find_applications(project, defname, instance)
    if len(apps) == 0:
        error.raise_error('No instances of application `{0}` exist.',
                          defname)
    elif len(apps) > 1:
        error.raise_error('Multiple instances of `{0}` exist.\n'
                          'Use `ravtest ps` to list the instances and then\n'
                          'specify the application with its instance id.',
                          defname)
    app = cache.get_application(apps[0]['id'])
    return app
