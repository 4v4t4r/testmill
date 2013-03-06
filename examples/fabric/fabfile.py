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

# This is an example fabfile.py that illustrates how to use TestMill as a
# library with Fabric.

from fabric.api import *
from fabric.state import env, output
from fabric.tasks import execute

from testmill import fabric as ravello

# The following line enables debugging (both for Fabric and TestMill)
#output.debug = True
output.output = False

@task
def provision(name):
    app = ravello.get_application(name)
    if app:
        print('Application `{0}` already exists, making sure it is started.'
                .format(name))
        ravello.start_application(name, wait=True)
    else:
        vms = []
        vms.append({'name': 'db', 'image': 'ubuntu1204', 'memory': 2048})
        vms.append({'name': 'web', 'image': 'ubuntu1204', 'memory': 1024,
                    'services': ['http', 'https']})
        print('Creating new application `{0}`.'.format(name))
        app = ravello.create_application(name, vms=vms)
    env.hosts = ravello.lookup(name)
    env.application_name = name
    print('Application `{0}` is running in {1}/{2} ({3} VMs).'
                .format(name, app['cloud'], app['region'], len(app['vms'])))


@task
@parallel
def update():
    # This will grab env.hosts that was set by provision(). Note that no
    # SSH key management is needed (it's all done automatically).
    sudo('apt-get update', quiet=True)
    sudo('apt-get -y upgrade', quiet=True)


@task
@parallel
def setup():
    # Illustrates how you can use the reverse_lookup() to get the host
    # and application name from env.host. Note: on the remote host you
    # can also use the output of `hostname`. The standard testmill images
    # use cloud-init to configure the host name to the "name" set in the
    # VM definition in the provision step.
    put('scripts')
    appname, vmname = ravello.reverse_lookup(env.host)
    with cd('scripts'):
        sudo('sh setup-{0}.sh'.format(vmname))

@task
@ravello.only_on('web')
def push():
    # Illustrates how to use the @ravello.only_on() decorator to ensure a task
    # only runs on the indicated VM.
    # Just an example. In the real world you would use something a lot
    # more robust than this. Usually some kind of Git based deployment, and
    # you'd run the server using a supervisor.
    put('hello.py')
    sudo('killall gunicorn', quiet=True)
    sudo('nohup gunicorn -D --bind 0.0.0.0:80 hello:hello_app')
    env.web_host = env.host


@task(default=True)
def deploy(name='production'):
    execute(provision, name)
    execute(update)
    execute(setup)
    execute(push)
    print('\nApplication `{0}` is now available at http://{1}/.'
                .format(env.application_name, env.web_host))
