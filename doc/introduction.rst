***************
Getting Started
***************

Installation Instructions
=========================

This section contains generic installation instructions. See the bottom of this
section for specific instruction on installing on Linux, Mac and Windows.

TestMill is written in the Python programming language, and has the following
dependencies:

 * Python version 2.6, 2.7, 3.2 or 3.3.
 * Fabric, version 1.5.3 or higher. This drags in Paramiko and PyCrypto
   as indirect dependencies.
 * PyYAML, any recent version.

The simplest way to install is to install directly from the Python Package
Index. On Unix-like systems, this means opening a command prompt and issuing
the following command::

 $ sudo easy_install testmill

One caveat is that TestMill has an indirect dependency on PyCrypto. PyCrypto
contains a few modules written in C which need to be compiled. In general it is
recommended to use the PyCrypto version that is provided by your OS vendor, if
one is available. The alternative is to compile it yourself. The
``easy_install`` command above will do this automatically, however, to do so it
will need a C compiler.  Normally this is not a problem on Linux, but Mac and
Windows do not ship with C compiler by default. See the OS specific
installation instructions below for more information.

 * :ref:`linux-installation`
 * :ref:`windows-installation`
 * :ref:`mac-installation`

Registering with Ravello
========================

In order to use TestMill, you need to register with the Ravello service.
Currently (Feb 2013), Ravello is in beta and. You will get 4,320 or 8,640
(depending on the account type) free VM hours per month. This corresponds to
either 3 or 6 dual core systems that are active for an entire month.

You can register on the `Ravello Home Page <http://ravellosystems.com>`_ by
clicking ont he "Try it now" button.

Running your first Application
==============================

Once you've installed TestMill and registered for Ravello, we can start
exploring it. In this section we will give you a small example to wet your
appetite. 

TestMill was designed to provide simple yet powerful automation for development
and test workflows. Its core feature is that it can build multi-vm applications
on the fly using the Ravello Cloud Application Hypervisor, and then run
workflows in them.

When we say application in the context of Ravello, we mean something very
specific. In Ravello, an application is a completely isolated set of virtual
machines, networks and storage that runs together as a unit somewhere in the
cloud and implements one or more (typically network-accessible) services. You
have complete control over all the aspects of the application infrastructure,
which makes it a great tool for creating efficient and high-fidelity
development and test environments.

In TestMill, Ravello applications are described by a text file called the
*manifest*. By convention, the manifest is stored as ``.ravello.yml`` in the
root directory of a source code repository. The manifest is version controlled
together with the rest of the code, and defines applications that are relevant
to the code contained in the repository. It can define for example different
kinds of development and test environments for the code base. This concept of
describing infrastructure as part of your source code is called *infrastructure
as code* and is an important concept in the *devops* movement.

Let's first run a really simple application to illustrate the concept of the
manifest and work flows. On a command-line, issue the following commands::

    $ git clone https://github.com/ravello/testmill
    $ cd testmill/examples/platforms

The directory ``examples/platforms`` contains a basic manifest that creates a
single application with 5 different virtual machines. Each virtual machine will
execute the command ``uname`` command to identify itself.  As mentioned above,
the manifest is stored in the file ``.ravello.yml``, and looks like this:

.. literalinclude:: ../examples/platforms/.ravello.yml
    :language: yaml
    :linenos:

As you see, the file is in YAML format. To run the manifest, issue these
commands::

    $ ravtest login
    $ ravtest run platformtest

The ``ravtest run`` command will execute the actual manifest. It might take up
to 5 minutes to complete while the application is being published to a cloud.
This time is only required the first time you create an application, subsequent
runs will be a lot faster.

The output of the will be something like this::

    Created new application `platformtest:1`.
    Published to AMAZON/Virginia.
    Waiting until application is ready...
    Progress: 'P' = Publishing, 'S' = Starting, 'C' = Connecting
    ===> PPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPCCCCCCCCCCCCCCCCCCCCCC DONE
    Starting run `a7b4f326620f11d7c57cd3847123b3a0`.
    Executing tasks on 5 virtual machines...

    == Output for task `execute` on VM `fedora18`:

    Linux fedora18 3.7.7-201.fc18.x86_64

    == Output for task `execute` on VM `ubuntu1204`:

    Linux ubuntu1204 3.5.0-23-generic

    == Output for task `execute` on VM `fedora17`:

    Linux fedora17 3.7.6-102.fc17.x86_64

    == Output for task `execute` on VM `ubuntu1210`:

    Linux ubuntu1210 3.5.0-17-generic

    == Output for task `execute` on VM `centos6`:

    Linux centos6 2.6.32-279.19.1.el6.x86_64

    All tasks were executed succesfully!

    == The following services will be available for 50 minutes:

    On virtual machine `ubuntu1210`:
        * ssh: 23.20.95.233 port 22

    On virtual machine `ubuntu1204`:
        * ssh: 54.234.154.151 port 22

    On virtual machine `centos6`:
        * ssh: 54.234.217.197 port 22

    On virtual machine `fedora18`:
        * ssh: 107.20.85.146 port 22

    On virtual machine `fedora17`:
        * ssh: 54.234.188.248 port 22

We will explain the manifest in great detail in the rest of this manual.
However, a few things can already be gleaned from this output:

 * TestMill created a new Ravello application ``platformtest:1`` for the
   application specified in the manifest.

 * The application was published to a cloud, in this case to the "Virginia"
   region of Amazon Web Services.

 * A unique ID ``a7b4f326620f11d7c57cd3847123b3a0`` was allocated to the
   current run.

 * The application was created with 5 virtual machines based on versions of
   Fedora, Ubuntu and CentOS.

 * As can be seen from the command output, the host name for each virtual
   machine was set to the name specified for the VM in the manifest.

 * After the run is complete, the VMs will stay up for 50 minutes. This allows
   you to go back into the system and examine in case there was a failure. Go
   ahead right now and issue the command::

    $ ravtest ssh platformtest:1 ubuntu1210

   This will connect you to the ``ubuntu1201`` virtual machine through ssh. By
   default the shell will start out in the directory of the last run.

   After the 50 minutes, the application is shut down. It will automatically be
   restarted in case it is needed by future ``ravtest run`` or ``ravtest ssh``
   commands.

This is all for the introduction. In the rest of this manual we will explain in
much more detail how the manifest works, including how to define more
complicated work flows using TestMill's unique multi-vm work flow
synchronization and communication facilities.
