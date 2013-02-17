************
The Manifest
************

The core of TestMill is to create single or multi-vm applications on the fly,
and then run workflows in them. This is basically what the ``ravtest run``
command does. The configuration on how to construct the applications and what
workflows do is stored in a file called the *manifest*. By convention, the
manifest is stored in a file named ``.ravello.yml`` in the root directory of a
source code repository. The manifest normally defines applications that are
needed by the code in the repository it is part of, and is version controlled
together with that code.

The manifest is a file in the YAML_ format. The YAML schema tries to satisfy
two, partially conflicting goals:

1. Being concise. Basic configurations should fit on a single screen, and take
   a few minutes to write.

2. Being extensible. It should be possible to create arbitrary complex
   configurations and any internal or default operation should be fully
   customisable (for an interesting take on why this is desirable, see
   InternalReprogrammability_ by Martin Fowler).

TestMill tries to achieve these goals using two techniques: provide sensible
default values where possible, and provide a *short hand* notation for certain
elements. More on this in the section :ref:`concise-manifests`.


Testing a Manifest
==================

Before we describe the manifest in detail, we should mention the ``ravtest
lint`` command. This command checks a manifest and tells you whether it is
valid or not. The command also accepts a ``--dump`` flag that will dump the
expanded manifest on standard output. This command can be a very useful
debugging tool.


Defining Applications
=====================

Applications are defined in the manifest under the top-level ``applications:``
key. This must be a list of dictionaries, each dictionary corresponding to an
application. Applications have a mandatory ``name:`` key that must uniquely
identify them. For a reference of the application schema, see
:ref:`application-ref`.

There are two types of applications: applications that are built from scratch
by composing them from images, and applications that are created from a
*blueprint*.

The first type of application, the one composed from images, is typically the
fastest to get started with. It also has the advantage that the entire
application configuration is embedded in the manifest and no outside setup is
required. An image is in essence a frozen version of a virtual machine. You
compose the application by saying which virtual machines need to be included
and from what image they need to be created.  A number of standard images are
provided by TestMill and available from the Ravello image library. For a list
of the available standard images, see :ref:`standard-images`. You can also
create your own custom images by uploading VMware and KVM based virtual
machines through the Ravello web site.

A blueprint based application on the other hand needs to be set up outside
TestMill, but it can be more flexible. A blueprint is a frozen version of an
entire multi-vm application. Blueprints are created and managed through the
Ravello web site. This allows you to use configurations that are not yet
supported through TestMill but that are available in Ravello. For example, in a
"from image" application, all VMs share a single L2 network that spans all
the VMs. In a blueprint on the other hand you have the option of creating more
complicated network topologies, use IP filtering, custom DNS, and more.  A
number of standard blueprints are available from the Ravello blueprint library.
You can also create a custom blueprint using the Ravello web site, or by using
``ravtest save`` to save an application that was created from images.

Let's start with an example application, one that is composed from standard
images:

.. code-block:: yaml
    :linenos:

    applications:
    -   name: unittest
        vms:
        -   name: executor1
            image: ubuntu1204
        -   name: executor2
            image: ubuntu1204


This application consists of two virtual machines. Both VMs are based on Ubuntu
12.04 and are called ``executor1`` and ``executor2``. The names serve 3
purposes: they are the names of the VM objects in the Ravello application that
is created, they will be configured as host names inside the virtual machines,
and they are also included as A records for the VMs in managed DNS service
inside the application. The name ``ubuntu1204`` refers to the standard Ubuntu
12.04 image in the image library. Note that image names are case sensitive.

An application that is based on a blueprint would look like this:

.. code-block:: yaml
    :linenos:

    applications:
    -   name: unittest
        blueprint: unittest-bp
        vms:
        -   name: executor1
        -   name: executor2

As you can see there are two differences. First of all, the ``blueprint:`` key
is provided for the application, and secondly the ``image:`` key is *not*
provided for the VMs. Note that the VM definitions are still needed, even
though they could be taken from the blueprint. This is because it allows us to
attach workflows to them (explained below), and also because it allows you to
use blueprints with some "no-touch" VMs that are started up by Ravello but not
managed by TestMill.


Defining Workflows
==================

Workflows are defined at the level of virtual machines. Each VM in an
application has exactly one workflow attached to it. A work flow consists of a
number of tasks, and each task is implemented as a number of shell commands (a
step can also be implemented by a Python class by specifying the ``class:`` key
in the task definition -- more on that in the section :ref:`custom-tasks`).

Let's have a look at a workflow. The workflow is defined using the ``tasks:``
key on a virtual machine. Below an example flow is given:

.. code-block:: yaml
    :linenos:

    tasks:
    -   name: prepare
        commands:
        - shell_cmd_1
        - shell_cmd_2
    -   name: execute:
        commands:
        -   shell_cmd_1
        -   shell_cmd_2


This workflow defines two tasks: "prepare" and "execute". Each task consists of
two shell commands.

Shell Commands
--------------

Each task is composed of a number of shell commands. The commands are listed
under the ``commands:`` key, which should be a list of strings. Each string is
a (simple or compound) shell command that is executed remotely with the default
login shell of the "ravello" user.

If there are multiple commands in one task, they are executed by the same
shell. This means that you can use shell variables to communicate information
between the commands. After each command, the shell variable "$?" is checked,
and if it is nonzero, the task is aborted. This means that from an error
handling point of view, the following two are different::

    commands:
    -   shell_cmd_1; shell_cmd_2

and::

    commands:
    -  shell_cmd_1
    -  shell_cmd_2

In the first case, if "shell_cmd_1" exits with a nonzero exit status, then
"shell_cmd_2" is still executed and if that succeeds, then the entire task
succeeds. In the second case however, the task is aborted.

Currently all standard images are Linux based and the "ravello" user is
configured with the bash login shell.  It is recommended however to keep the
syntax of the commands compatible with the Bourne shell. That way when other
images are added where bash is not the default shell, things will still work.

The shell commands in each task have access to a number of standard environment
variables that are provided by TestMill. These variables allow you to e.g.
detect what application you are running in, or to make calls to the Ravello
API. A table with the list of available environment variables can be found in
the section :ref:`env-vars`.

Synchronization
---------------

The tasks that make up a workflows cannot be executed in an uncoordinated way.
For example, if one step prepares a database on a database server, then we need
to be sure that a different step on a different VM that needs that database is
not executed until the this step completes. For this purpose, TestMill executes
the tasks in a synchronized way. This works as follows:

 * The workflows for all VMs are all started up at the same time and execute in
   parallel.

 * On each VM, the tasks are executed in the order that they are specified
   (obviously).
   
 * If a shell command within a task fails, then what happens depends on whether
   the ``--continue`` command-line argument was provided. If it was not
   provided, then the task aborts and the remaining shell commands are not
   executed. Steps on other VMs that run in parallel will continue to execute,
   but when they are done, no new tasks are started and the flows are aborted.
   If ``--continue`` was provided, then the current task will continue and so
   will the tasks on the other VMs.

 * A task is not started before all task with the same name as the previous
   task on the current VM, complete on all other VMs that have that task. So
   say for example that you have 4 VMs where 3 have an "prepare" action and all
   4 have an "execute" action. No execute action is started before the 3
   "prepare" actions complete.

The example below shows how to you could safely build a 2-vm application that
consists of a database server and a web server, where the database server needs
to be running before the web server can start:

.. code-block:: yaml
    :linenos:

    vms:
    -   name: db
        tasks:
        -   name: prepare
            commands:
            -   setup_database.sh
    -   name: web
        -   name: prepare
        -   name: execute
            commands:
            -   start_webserver.sh

In this example, the VM "web" has a task "prepare" and a task "execute".  This
means that the task "execute" will only start after *all* tasks named "prepare"
on *all* VMs have completed. Specifically, this means that "execute" on "web"
will run after "prepare" on "db". Without having the (in this case empty)
"prepare" task on "web", TestMill would not have synchronized both tasks.

Passing Information
-------------------

Tasks on one VM can communicate information to tasks on other VMs. This is
useful in situations where you need to pass small pieces of configuration data
between the VMs. For example, when you set a random database password on a
database server, it can be communicated to clients of that database.

The mechanism works by invoking the shell function ``broadcast()`` on the shell
variable name that you want to communicate. This function is made available by
TestMill to all shell commands. It will make the variable available as a shell
variable on future tasks on this and other VMs. Example:

.. code-block:: yaml
    :linenos:

    vms:
    -   name: db
        tasks:
        -   name: prepare
            commands:
            -   password=`generate_password.sh`
            -   setup_database.sh $password
            -   broadcast password
    -   name: web
        -   name: prepare
        -   name: execute
            commands:
            -   start_webserver.sh $password

One important note is that ``broadcast`` only works for synchronized tasks.
This is the only way to prevent race conditions, and synchronization is
therefore enforced by TestMill. If in the example above, the VM "web" would not
have a "prepare" task, then "execute" would not be synchronized on "prepare"
and in this case TestMill would not make the value of ``$password`` available.


.. _concise-manifests:

Concise Manifests
=================

It is important that manifests can be written concisely. The more boilerplate
that is required, the less readable and expressive a manifest becomes.

In order to provide for conciseness, without losing extensibility, two
techniques are used: sensible defaults for many settings, and a separate
short-hand notation that is expanded when the manifest is parsed.

Defaults
--------

Two types of defaults are implemented: global defaults and language specific
defaults. Language specific defaults have the higher precedence, and are only
are only used when the programming language of the source code repository can
be determined (or is specified in the manifest). 

The defaults are merged with the settings provided in the manifest when the
manifest is parsed. This happens at the top level, the application level, the
VM level, and the task level. The merge process works in the following way:

 * If a key does not exist in the target, it is copied.
 * If a key exists, and both source and target are dictionaries,
   the dictionaries are merged.

In order to achieve InternalReprogrammability_, any built-in default can be
overridden with a new default by the user in the manifest. In fact, the
built-in defaults simply specified in a `default manifest`_ that is merged with
the project manifest before it is processed.

The following, top-level defaults are normally detected by TestMill and do not
need to be given explicitly:

.. code-block:: yaml
    :linenos:

    project:
        name: project-name
        language: project-language
    repository:
        type: git
        url: remote-origin

The project name, if absent, is determined from the name of the top-level
directory of the source code repository. The project language is auto detected
from the files in the repository. The repository type and origin are similarly
detected by inspecting the repository directories and files.

At the VM level, a default workflow is defined in the default manifest. It
looks like this:

.. code-block:: yaml
    :linenos:

    tasks:
    -   name: deploy
        quiet: true
        class: testmill.tasks.DeployTask
    -   name: sysinit
        quiet: true
        class: testmill.tasks.SysinitTask
    -   name: prepare
        quiet: true
        class: testmill.tasks.Task
    -   name: execute
        quiet: false
        class: testmill.tasks.Task

As describe above, the merge process will copy this ``tasks:`` key to a VM
definition in the manifest, if the VM does not specify this key. This
effectively established a default workflow for all virtual machines.

The ``deploy`` task is a special task that will create a gzipped tarfile from
the local source repository and copy it to the remote VM. During the packing,
the repository specific ignore files (.e.g ``.gitignore`` for git) are honored
and files that are ignored are not copied over. To prevent copying unnecessary
data it is therefore important that you keep your ignore files accurate. If the
``remote`` key is set to ``true`` for the task, then a remote checkout from the
upstream repository is performed instead of copying the local directory.

The ``sysinit`` task is another special task that can be used to perform system
initialization. This task runs its commands as root, and it also makes sure
that commands are run only once per virtual machine, even if multiple runs of
the same workflow are executed.

The ``prepare`` and ``execute`` tasks are regular tasks that execute the shell
commands in their ``commands:`` key. Since there are not default commands,
these tasks will do nothing unless you specify commands for these tasks in the
manifest. In case a language is detected however, language specific default
commands for these two actions are given in the default manifest. The following
table lists these defaults:

============  =======  ==================================
Language      Task     Command
============  =======  ==================================
Python        prepare  ``python setup.py build``
Python        execute  ``python setup.py test``
Java (Maven)  execute  ``mvn test``
Java (Ant)    execute  ``ant test``
Clojure       execute  ``lein test``
============  =======  ==================================

As you can see, these commands are very much geared towards a unit-testing use
case. The benefit of having these language specific default actions is
currently under consideration, and may be removed in a future release. To
disable language default settings today, use the following idiom in your
manifest::

    language: nodefaults


Shorthands
----------

TestMill implements a few shorthands that allow you to write manifests in a
more concise way. A simple short-hand is that of the ``language:`` key. If a
top-level ``language:`` key exists, it is moved under the ``project:`` key.

More interesting shorthands are those for tasks.  Assume your workflow wants to
provide the commands for the "prepare" and "execute" commands in the default
workflow. One way to do that would be this:

.. code-block:: yaml
    :linenos:

    # wrong way to specify commands for "prepare" and "execute"
    vms:
    -   name: vm1
        tasks:
        -   name: prepare
            commands:
            -   shell_cmd_1
        -   name: execute:
            commands:
            -   shell_cmd_2

This does not work because the merge algorithm that will merge the default
tasks into the VM will see that the VM already has a ``tasks:`` key and
therefore skip it. The way to do this instead is by using the short-hand
notation for specifying tasks. By default, any key in a VM that has the same
name as a task, is assumed to be the ``commands:`` for that task. So:

.. code-block:: yaml
    :linenos:

    name: vm1
    sysinit:
    -   shell_cmd_1
    -   shell_cmd_2
    execute:
    -   shell_cmd


This kills two birds with one stone. First, the notation is more compact. And
second, it allow us to have a default workflow that can be completely
customized by providing the ``tasks:`` key in a VM. If the merge algorithm
would try to merge the two ``tasks:`` keys instead, it would not be possible to
remove tasks for the default workflow.

.. _YAML: http://yaml.org/
.. _InternalReprogrammability: http://martinfowler.com/bliki/InternalReprogrammability.html
.. _default manifest: https://github.com/ravello/testmill/blob/master/lib/testmill/defaults.yml
