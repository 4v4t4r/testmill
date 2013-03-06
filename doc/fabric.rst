**************************
Using TestMill from Fabric
**************************

.. py:currentmodule:: testmill.fabric

TestMill allows you to provision multi-vm applications in the Ravello Cloud and
run workflows on them. It uses the Ravello API to provision applications, and
Fabric for its remote execution. Its functionality is exposed through the
``ravtest`` command-line utility, which uses the ``.ravello.yml`` manifest to
store application and workflow definitions.

As an alternative to using the ``ravtest`` frontend, you may want to use Fabric
directly through its ``fab`` command and the ``fabfile.py``.  This is useful if
you are already familiar with Fabric, if you have already developed automation
for your project using it, or if you want the full and total flexibility that
Fabric gives you. Fortunately, TestMill makes this really easy to do. This
section explains how to use Ravello directly from Fabric using TestMill as a
library.

Getting Started
===============

The module ``testmill.fabric`` defines a publicly available API that is useful
for integrating with Fabric. You are recommended to import it as follows:

.. code-block:: python

    from testmill import fabric as ravello

so you can refer to it simply as ``ravello`` in your code.

Using the API is pretty straightforward. The example below defines a Fabric
task that creates a new Ravello application with two virtual machines. Note
that in context of Ravello, the term *application* means something very
specific: it refers to a set of virtual machines connected by a private L2
network that run somewhere in one of the supported clouds. In this case, both
machines in the application are based on Ubuntu 12.04. One system is a web
server with two publicly availble services, the other server is a database
server.

.. code-block:: python
    :linenos:

    @task
    def provision(name):
        vms = [{'name': 'db', 'image': 'ubuntu1204', 'memory': 2048},
               {'name': 'web', 'image': 'ubuntu1204', 'memory': 1024,
                'services': ['http', 'https']}]
        app = ravello.create_application(name, vms=vms)
        env.hosts = ravello.lookup(name)

The function :func:`create_application` creates a new Ravello application.
The call will wait until the application has been created, published to a
cloud, and until all its VMs have started up and are available over ssh.

The assigment in line 7 will set Fabric's ``env.hosts`` string to point to both
virtual machines. This allows you to target these systems with Fabric like you
would do with any other system, for example using the Fabric commands ``run()``
or ``sudo()``.

Also note that there is no code to set up ssh keys! TestMill will automatically
generate a new ssh key for you the first time one is needed, store it in your
home directory, and configure the VMs that it creates to use that key.

Usually the task above will take about 5 minutes to complete, depending on
which cloud the application is provisioned to. This time is only need the first
time when an application is created. Once the application is running, you can
access it later using :func:`get_application`. You can also stop it with
:func:`stop_application`, start it again using :func:`start_application` and
save it with :func:`create_blueprint`.

API Authentication
------------------

For most operations, TestMill needs a connection to the Ravello API. The API
credentials can be provided through the ``env.ravello_api_user`` and
``env.ravello_api_password`` configuration variables. If these variables are
not set, TestMill will prompt for them the first time they are needed.

Once you are logged on, a cookie is stored in your home directory that will
give you 2 hours of password-less access to the API.

Other Examples
--------------

A more complete example on how to use TestMill with Fabric can be see in the
`examples/fabric 
<https://github.com/ravello/testmill/tree/master/examples/fabric>`_ directory
of the testmill source tree.

API Reference
=============

.. automodule:: testmill.fabric
    :members:

.. _vm-defs:

VM and Application Definitions
==============================

The function :func:`create_application` needs a list of VM definitions
describing the VMs is needs to create. Each VM is described by a dictionary.
The format is identical to the one used in the TestMill manifest. The possible
keys are described in: :ref:`vm-ref`.

The functions :func:`create_application` and :func:`get_application` return an
application definition. This is a dictionary containing application metadata
including the VM definitions. The format is again identical to the one used in
the TestMill manifest and is described in :ref:`application-ref`.
