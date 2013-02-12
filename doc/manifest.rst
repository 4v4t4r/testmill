************
The Manifest
************

The core functionality of TestMill is to create single or multi-vm applications
on the fly, and then run workflows in them. The configuration on how to
construct the applications and what workflows to run is stored in a file called
the *manifest*. By convention, the manifest is stored in a file called
``.ravello.yml`` in the root directory of a source code repository. It is
version controlled together with the rest of the sources, and normally defines
applications that are needed by the code in the repository it is part of.

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
elements. The short hand notation removes most unnecessary boilerplate but it
still allows to use the full expanded notation if required.

The two most important parts of the manifest are:

1. The application definitions. Every manifest will define 1 or more
   applications, where application consists of 1 or more virtual machines.

2. The workflow definitions. Each virtual machine has a workflow associated for
   it. Each workflow is responsible for achieving part of the overall goal of
   the application.
   A workflow is more than just a simple script that is executed remotely.
   Steps across multiple virtual machines are synchronized to each other, and
   there is a mechanism for passing information from one VM to the others.


Testing a Manifest
==================

Before we describe the manifest in detail, we should mention the ``ravtest
lint`` command. This command checks a manifest and tells you whether it is
valid or not. The command also accepts a ``--dump`` flag that will dump the
expanded manifest on standard output. This is very useful for understand how
the short-hand notation is expanded.


Defining applications
=====================

In the manifest, applications are defined under the top-level ``applications:``
key. This must be a list of dictionaries, each dictionary corresponding to an
applcation. Each dictionary has a a mandatory ``name:`` key that must uniquely
identify the application. For a reference of the application schema, see
:ref:`application-ref`.

There are two types of applications: applications that are built from scratch
by composing virtual machines from images, and applications that are cloned
from a *blueprint*. Both images and blueprints are library items in the Ravello
service, and a small amount of standard images and blueprints are available. A
blueprint is in essence a frozen version of an application. A blueprint can be
created graphically using the Ravello GUI, or from an existing, "from scratch"
application using ``ravtest save``.

Both application types have their advantagages and disadvantages. It is a
typically a lot faster to compose an application from scratch as you just need
to list the images in the manifest. On the other hand, blueprints are more
flexible and can support any feature that is supported by Ravello. For example,
applications that are created from scratch always have a single L2 network that
spans all VMs.  With a blueprint instead you can design more complex network
topologies, implement IP filtering, and also include "other" VMs for which no
standard images exist.

Within an application, you need to specify the VMs. This is required even if
the application is created from a blueprint. The VM definitions allow us to
attach workflows to the VMs later.

Let's start with an example application, one that is composed on-demand:

.. code-block:: yaml
    :linenos:

    applications:
    -   name: unittest
        vms:
        -   name: executor1
            image: ubuntu1204
        -   name: executor2
            image: ubuntu1204


This example demonstrates the first type of application, where an application
is constructed on demand by composing virtual machines. The application in this
case consists of two virtual machines, both based on Ubuntu 12.04. They are
called ``executor1`` and ``executor2``.

The name ``ubuntu1204`` refers to a *image* in the Ravello library. A set of
useful default images is provided. For more information on the standard images,
see :ref:`standard-images`.

An application that is based on a blueprint would look like this:

.. code-block:: yaml
    :linenos:

    applications:
    -   name: unittest
        blueprint: unittest-bp
        vms:
        -   name: executor1
        -   name: executor2

As you can see, there are two differences. First of all, the ``blueprint:`` key
is provided for the application. And secondly, the ``image:`` key is *not*
provided for the VMs.

Defining Workflows
==================

Workflows are defined at the level of virtual machines. Each VM in an
application has exactly one workflow attached to it. A work flow consists of a
number of steps, and normally each step consists of a number of shell commands
(a step can also be implemented by a Python class -- more on that in the
section :ref:`custom-tasks`).

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


This workflow defines two steps: "prepare" and "execute". Each step consists of
two shell commands.

Concise Manifests
=================

It is important that manifests can be written concisely. The more boilerplate
that is required, the less readable and expressive a manifest becomes.

In order to provide for conciseness, without losing extensibility, two
techniques are used: sensible defaults for many settings, and a separate
short-hand notation that is expanded when the manifest is parsed.

Defaults
--------

Two levels of defaults are implemented: global defaults and language specific
defaults. Language specific defaults have the higher precendence, and are only
are only used when the programming language of the source code repository can
be determined (or is specified in the manifest).

In order to achieve InternalReprogrammability_, both levels of defaults can be
overridden by the user in the manifest. In fact, the defaults are specified in
a `default manifest`_ that is merged with the project manifest before it is
processed. To understand how the default manifest is structured, have a look at
it in the TestMill source code.

The following defaults are normally detected by TestMill and do not need to be
given explicitly:

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

The default workflow as defined in the default manifest looks like this:

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

This ``tasks:`` section will be copied to the ``tasks:`` section in a virtual
machine in case it does not specific the tasks. This effectively established a
default workflow for all virtual machines.

The ``deploy`` task is a special task that by default will create a gzipped
tarfile from the local source repository and copy it to the remote VM. During
the packing, the repository specific ignore files (.e.g ``.gitignore``) are
honored and files that are ignored are not copied over. To prevent copying
unnecessary data it is therefore important that you keep your ignore files
accurate. If the ``remote`` key is set to ``true`` for the task, then instead a
remote checkout from the upstream repository is performed.

The ``sysinit`` task is another special task that can be used to perform system
initialization. This task runs its shell commands as root, and it also makes
sure that commands are run only once per virtual machine, even if multiple runs
of the same workflow are executed.

The ``prepare`` and ``execute`` tasks are regular tasks that execute the shell
commands in their ``commands:`` key.

In case a language is detected, language specific default action will override
the global default actions. The following table lists the currentl language
specific default actions:

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
currently under consideration, and this feautre may be removed in a future
release. To disable language default settings already today, use the following
idiom in your manifest::

    language: nodefaults


Workflow shorthand
------------------

This is best illustrated by example. Assume your workflow wants to provide the
steps "sysinit" and "execute", and those steps have no special configuration
and are just a list of shell commands. In this case, the steps can be described
at the VM level like this:

.. code-block:: yaml
    :linenos:

    name: myvm
    sysinit:
    -   shell_cmd_1
    -   shell_cmd_2
    execute:
    -   shell_cmd

The nice thing is that this works nicely together with the default ``tasks``
section. If you would specify the ``tasks:`` key in for the virtual machine,
then it would override all default tasks. This way however, individual tasks
can be customized while leaving the other tasks in place.


.. _YAML: http://yaml.org/
.. _InternalReprogrammability: http://martinfowler.com/bliki/InternalReprogrammability.html
.. _default manifest: https://github.com/ravello/testmill/blob/master/lib/testmill/defaults.yml
