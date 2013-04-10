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

"""
The API for using Ravello through Fabric is defined in the ``testmill.fabric``
module. The interface is a functional interface very similar to Fabric itself.

Configuration attributes test are needed by TestMill are stored into the Fabric
``env`` global environment. The following attributes are known:

====================  =========================================================
Attribute             Description
====================  =========================================================
ravello_user          The ssh user to use when connecting to VMs in Ravello
                      applications. The default value is ``'ravello'``.  You
                      can set this to ``None`` to let Fabric determine the user
                      name.
ravello_api_user      The user for the Ravello API. If not set, you will be
                      prompted for it when a connection is needed. This is the
                      same user name that you use to log on to the Ravello web
                      interface.
ravello_api_password  The password for the Ravello API. If not set, you will be
                      prompted for it when a connection is needed. This is the
                      same password that you use to log on to the Ravello web
                      interface.
ravello_api_url       The URL to the Ravello API. The default is ``None`` which
                      uses the default API entry point.
====================  =========================================================

Most functions need a connection to the Ravello API. This connection is created
automatically for you the first time it is needed. SSH keys for the virtual
machines in Ravello applications are automaticaly set up for you as well, and
added to ``env.key_filename``. 
"""

from __future__ import absolute_import, print_function

import argparse
from functools import wraps

from testmill.state import env
from testmill import (cache, error, login, keypair, ravello, util,
                      application, main, compat, manifest, console)

from fabric import api as fab
import fabric.utils


__all__ = ['new_application_name', 'get_application', 'get_applications',
           'create_application', 'start_application', 'stop_application',
           'remove_application', 'new_blueprint_name', 'get_blueprint',
           'get_blueprints', 'create_blueprint', 'remove_blueprint',
           'lookup', 'reverse_lookup', 'hosts', 'only_on']


def _setup_testmill():
    """Set up or re-sync a TestMill "env" from a Fabric "env". Also set some
    useful defaults in the Fabric environment for using TestMill.

    In essense this is a bridge between Fabric and the TestMill package.
    """
    env.quiet = False
    env.verbose = fab.output.debug
    env.manifest = None
    env.debug = fab.output.debug
    env.always_confirm = False
    if not hasattr(fab.env, 'ravello_user'):
        fab.env.ravello_user = 'ravello'
    if not hasattr(fab.env, 'ravello_api_user'):
        fab.env.ravello_api_user = None
    if not hasattr(fab.env, 'ravello_api_password'):
        fab.env.ravello_api_password = None
    if not hasattr(fab.env, 'ravello_api_url'):
        fab.env.ravello_api_url = None
    if not hasattr(env, 'api'):
        main.setup_logging()
        env.service_url = fab.env.ravello_api_url
        env.api = ravello.RavelloClient(service_url=env.service_url)
        try:
            login.token_login()
        except error.ProgramError:
            if not fab.env.ravello_api_user:
                msg = 'Please enter your Ravello username: '
                fab.env.ravello_api_user = console.prompt(msg)
            env.username = fab.env.ravello_api_user
            if not fab.env.ravello_api_password:
                msg = 'Please enter your Ravello password: '
                fab.env.ravello_api_password = console.getpass(msg)
            env.password = fab.env.ravello_api_password
            login.password_login()
            login.store_token()
    if not hasattr(env, 'public_key'):
        keypair.default_keypair()
        key_filename = env.private_key_file
        if fab.env.key_filename is None:
            fab.env.key_filename = key_filename
        elif isinstance(fab.env, compat.str):
            fab.env.key_filename = [fab.env.key_filename, key_filename]
        elif isinstance(fab.env, list):
            fab.env.key_filename.append(key_filename)


# NOTE: functions decorated with @with_fabric should repeat there signatures on
# the first line of the docstring, otherwise they will shop up in Sphinx as
# having xxx(*args, **kwargs) signature.

def with_fabric(func):
    """Decorator that calls _setup_testmill before invokding *func*, and that
    captures TestMill errors and forwards those to Fabric."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        _setup_testmill()
        try:
            return func(*args, **kwargs)
        except ravello.RavelloError as e:
            if env.debug:
                raise
            fab.env.warn_only = False
            fabric.utils.error(str(e))
        except error.ProgramError as e:
            if env.debug:
                raise
            fab.env.warn_only = False
            fabric.utils.error(str(e))
    return wrapper


@with_fabric
def new_application_name(template='fabric'):
    """new_application_name(template='fabric')

    Return an new unique application name.

    The argument *template* specifies the base name, to which a unique numeric
    suffix is appended.
    """
    name = application.new_application_name(template)
    return name


@with_fabric
def get_application(name):
    """get_application(name)
    
    Lookup the application *name*.

    If the application exists, return the application definition for it. The
    application is be a dictionary with string keys describing the application.
    If the application is not found, return None.

    .. seealso::
       See :ref:`application-ref` for the possible keys in the application
       definition dictionary.
    """
    app = cache.get_application(name=name)
    if app is None:
        return
    return application.appdef_from_app(app)


@with_fabric
def get_applications():
    """get_applications()

    Return a list containing all applications.
    """
    applications = []
    for app in cache.get_applications():
        app = cache.get_application(app['id'])
        applications.append(application.appdef_from_app(app))
    return applications


@with_fabric
def create_application(name=None, blueprint=None, vms=None, cloud=None,
                       region=None, wait=True, show_progress=True):
    """create_application(name=None, blueprint=None, vms=None, cloud=None, \
            region=None, wait=True, show_progress=True)

    Create a new application.

    If *blueprint* is specified, then it must be the name of a blueprint from
    which the application is created. If *blueprint* is not specified, then an
    application will be created from scratch in which case *vms* needs to be
    specified containing a list of the VM definitions. The VM definitions are
    dictionaries containing string keys describing the VM. The arguments
    *cloud* and *region* specify which cloud and region to publish the
    application to.  If these are not specified, the application is published
    to the lowest cost cloud that fits the VM definitions. If *wait* is
    nonzero, then this function will wait until the application is started up
    and its VMs are accessible via ssh.  If *show_progress* is nonzero, then a
    progress bar is shown.

    The return value of this function is the application definition of the
    application that was created. In case of an error, an exception is raised.

    .. seealso::
       See :ref:`vm-ref` for the possible keys in a VM definition dictionary.
    """
    if blueprint:
        bp = cache.get_blueprint(name=blueprint)
        if bp is None:
            error.raise_error('Blueprint `{0}` not found.', blueprint)
        if name is None:
            name = new_application_name(bp['name'])
    else:
        if name is None:
            name = new_application_name()
    appdef = { 'name': name }
    if vms:
        appdef['vms'] = vms
    if blueprint:
        appdef['blueprint'] = blueprint
    manif = { 'applications': [appdef],
              'defaults': { 'vms': { 'smp': 1, 'memory': 2048 } } }
    manifest.check_manifest(manif)
    manifest.percolate_defaults(manif)
    manifest.check_manifest_entities(manif)
    app = application.create_new_application(appdef, False)
    app = application.publish_application(app, cloud, region)
    if wait:
        vms = set((vm['name'] for vm in app['vms']))
        with env.let(quiet=not show_progress):
            app = application.wait_for_application(app, vms)
    return application.appdef_from_app(app)


@with_fabric
def start_application(name, wait=True, show_progress=True, timeout=1200):
    """start_application(name, wait=True, show_progress=True, timeout=1200)

    Start up an application.

    The *name* argument must be the name of an application. If *wait* is
    nonzero, then this function will wait until the application is up and its
    VMs are accessible via ssh. If *show_progress* is nonzero then a progress
    bar is shown.  The *timeout* argument specifies the timeout in seconds.
    The default timeout is 20 minutes. Application startup times vary greatly
    between clouds, and whether or not the application has already been
    published.

    This method will start all VMs in the application that are in the 'STOPPED'
    state. If *wait* is nonzero, then all VMs must either be in the 'STOPPED'
    state (in which case they will get started), in the 'STARTED' state (in
    which case there is nothing to do), or in a state that will eventually
    transition to 'STARTED' state (currently 'STARTING' and 'PUBLISHING'). If a
    VM is in another state, then no action is taken and an exception is raised,
    because this call would just timeout without the ability to complete.

    This function has no return value, and raises an exception in case of an
    error.
    """
    app = cache.get_application(name=name)
    if app is None:
        error.raise_error("Application `{0}` does not exist.", name)
    app = application.start_application(app)
    if wait:
        state = application.get_application_state(app)
        if state not in application.vm_reuse_states:
            error.raise_error("Cannot wait for app in state '{0}'.", state)
        vms = set((vm['name'] for vm in app['vms']))
        with env.let(quiet=not show_progress):
            application.wait_for_application(app, vms, timeout)


@with_fabric
def stop_application(name, wait=True, timeout=300):
    """stop_application(name)

    Stop an application with name *name*.

    This method will stop all VMs in the application that are currently in the
    'STARTED' state. VMs other states are not touched.
    
    The application may not be fully stopped even after this call. For example,
    if a VM is in the 'STARTING' state, it will eventually transition to
    'STARTED'. But a 'STARTNG' VM cannot be stopped before it reaches the
    'STARTED' state.
    """
    app = cache.get_application(name=name)
    if app is None:
        error.raise_error("Application `{0}` does not exist.", name)
    app = application.stop_application(app)
    if wait:
        state = application.get_application_state(app)
        if state not in ('STARTED', 'STOPPING', 'STOPPED'):
            error.raise_error("Cannot wait for app in state '{0}',", state)
        application.wait_until_application_is_in_state(app, 'STOPPED', timeout)


@with_fabric
def remove_application(name):
    """remove_application(name)

    Delete the application with name *name*.

    It is not an error to delete an application that does not exist. An
    application can always be deleted no matter what in the state its VMs are.
    If the application has running VMs, those will be uncleanly shutdown.

    Deleting an application destroys all data relating to the application
    including its VMs and their disks. This operation cannot be undone.
    """
    app = cache.get_application(name=name)
    if app is None:
        return
    application.remove_application(app)


@with_fabric
def new_blueprint_name(template='fabric'):
    """new_blueprint_name(template='fabric')

    Return a new unique blueprint name.

    The argument *template* specifies the base name, to which a unique numeric
    suffix is appended.
    """
    name = application.new_blueprint_name(template)
    return name


@with_fabric
def get_blueprint(name):
    """get_blueprint(name)

    Lookup the blueprint *name*.

    If the blueprint exists, return the blueprint definition for it. The
    format is the same as the application definition that created the blueprint
    with some operational fields removed.
    """
    bp = cache.get_blueprint(name=name)
    if not bp:
        return
    return application.appdef_from_app(bp)


@with_fabric
def get_blueprints():
    """get_blueprints()

    Return a list of all blueprints.
    """
    blueprints = []
    for bp in cache.get_blueprints():
        bp = cache.get_blueprint(bp['id'])
        blueprints.append(application.appdef_from_app(bp))
    return blueprints


@with_fabric
def create_blueprint(name, bpname=None, wait=True):
    """create_blueprint(name, bpname=None)

    Create a blueprint from an application.

    The *name* argument must be an application whose VMs are either all in
    the STOPPED or in the STARTED state.  The *bpname* argument is the name
    of the blueprint. If the blueprint name is not specified, a new unique name
    will be allocated.

    The return value of this function is the name of the blueprint that was
    created.
    """
    app = cache.get_application(name=name)
    if app is None:
        error.raise_error("Application `{0}` does not exist.", name)
    state = application.get_application_state(app)
    if state not in ('STOPPED', 'STARTED'):
        error.raise_error('Application `{0}` is currently in state {1}.\n'
                          'Can only save when STOPPED or STARTED.',
                          name, state)
    if bpname is None:
        bpname = new_blueprint_name('bp-{0}'.format(name))
    bp = application.create_blueprint(bpname, app)
    if wait:
        bp = application.wait_until_blueprint_is_in_state(bp, 'DONE')
    return application.appdef_from_app(bp)


@with_fabric
def remove_blueprint(name):
    """remove_blueprint(name)

    Delete a blueprint.

    It is not an error to delete a blueprint that does not exist.
    
    Deleting a blueprint destroys all data relating to the blueprint
    including its VMs and their disks. This operation cannot be undone.
    """
    bp = cache.get_blueprint(name=name)
    if not bp:
        return
    application.remove_blueprint(bp)


@with_fabric
def lookup(appname, *vms):
    """lookup(appname, *vms)

    Lookup the addresses for virtual machines in a Ravello application.

    The *appname* parameter must be the name of the application. After this
    parameter you may pass one or multiple positional arguments containing the
    VM names. If the VMs are not specified, all VMs in the application are
    selected. The first VM argument may also be a sequence, set or mapping
    containing VM names.

    The return value is a list of Fabric host strings, and may be directly
    assigned to *env.hosts*.
    """
    app = cache.get_application(name=appname)
    if app is None:
        error.raise_error("Application `{0}` does not exist.", appname)
    if isinstance(vms, compat.str):
        vms = [vms]
    app = cache.get_application(app['id'])
    hosts = []
    for vm in app.get('vms', []):
        if vms and vm['name'] not in vms:
            continue
        host = vm['dynamicMetadata']['externalIp']
        if fab.env.ravello_user:
            host = '{0}@{1}'.format(fab.env.ravello_user, host)
        hosts.append(host)
    return hosts


@with_fabric
def reverse_lookup(host):
    """reverse_lookup(host)

    Reverse lookup an *env.host* identifier.

    This function returns an (appname, vmname) tuple. If the host is not found,
    a ``ValueError`` is raised. This function can be used inside a task to get
    the VM name you are executing on. For example::

      @task
      def mytask():
          appname, vmname = ravello.reverse_lookup(env.host)
          if vmname == 'web':
              # take actions for VM 'web'
          else:
              # take other actions

    This function is especially useful with ``@parallel``, as it allows you to
    run tasks on multiple VMs in parallel where each task can behave different
    on different machines.
    """
    # NOTE: this depends on the IP address of the host being in the cache.  But
    # without poking under the hood of this API, there is no way of getting a
    # host string without going the application ending up in the case. So
    # therefore this should be fine.
    for app in env._applications_byid.values():
        for vm in app.get('vms', []):
            addr = vm.get('dynamicMetadata', {}).get('externalIp')
            if addr == host:
                return (app['name'], vm['name'])
    raise ValueError('Not a Ravello host: {0}.'.format(host))


@with_fabric
def hosts(appname, vms=None):
    """hosts(appname, vms=None)

    Run a task on *vms* in application *appname*.

    This function should be used as a decorator on a Fabric task. For example::

      @ravello.hosts('production', 'web')
      def deploy():
          # deploy to VM 'web' here

    Which is identical to::

      @hosts(ravello.lookup('production', 'web'))
      def deploy():
          # deploy to VM 'web' here

    Note that this decorator will do the lookup at the time the decorator is
    called. This lookup requires a Ravello API connection. You must either have
    ``env.ravello_api_user`` and ``env.ravello_api_password`` set, or you
    will be prompted for the API username and password. In case you want to do
    the lookup later, use :func:`lookup` directly and assign the return value
    to ``env.hosts``.
    """
    hosts = lookup(apppname, vms)
    return fab.hosts(*hosts)


def only_on(*names):
    """Run a Fabric task only on named VMs.

    You may pass in a one or more VM names as positional arguments. The first
    element may also be a sequence, set or mapping containing names.

    This function should be used as a decorator on a task, for example::

       @ravello.only_on('db')
       def deploy():
           # deploy to VM 'db' here

    This function works as a filter and does not interfere with ``env.hosts``.
    The task will run for all hosts otherwise selected, but the task will be a
    no-op for VMs not specified.
    """
    if len(names) > 0:
        if not isinstance(names[0], compat.str):
            names = set(names[0]) + set(names[1:])
    def wrapper(func):
        @wraps(func)
        def invoke(*args, **kwargs):
            appname, vmname = reverse_lookup(fab.env.host)
            if vmname not in names:
                return
            return func(*args, **kwargs)
        return invoke
    return wrapper
