***************
Getting Started
***************

Installation Instructions
=========================

This section contains generic installation instructions. See the bottom of this
section of specific instruction on installing on Linux, Mac and Windows.

TestMill is written in the Python programming language, and has the following
dependencies:

 * Python version 2.6, 2.7, 3.2 or 3.3.
 * Fabric, version 1.5.3 or higher. This drags in Paramiko and PyCrypto
   as indirect dependencies.
 * PyYAML, any recent version.

The simplest way to install is to install directly from the Python Package
Index. On Unix-like systems, this means opening a command prompt and issuing
the following command::

 $ sudo easy_install ravello-testmill

One caveat is the PyCrypto dependency. PyCrypto contains a few modules written
in the C programming language. In general it is recommended to use the PyCrypto
version that is provided by your OS vendor, if available. Otherwise, you will
need to compile it yourself. The ``easy_install`` command above will do this
automatically, but to do so it will need access to a C compiler. Normally this
is not a problem on Linux, but Mac and Windows do not have a C compiler
installed by default. See the OS specific installation instructions below for
more information.

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

Once you've installed TestMill and registered for Ravello, you can start
exploring it. In this section we will give you a small example to wet your
appetite. 

The job of TestMill is to build applications and run workflows in them. When we
say application in the context of Ravello, we mean something very specific. In
Ravello, an application is a completely isolated set of virtual machines,
networks and storage that runs together as a unit somewhere in the cloud and
implements one or more services (typically network-accessible). One example of
an application that would be very suited to run in Ravello would be a 3-tier
web-based application with a load balancer, application tier, and database
tier.

In TestMill, Ravello applications are described using a textual format called
the *manifest*. By convention, the manifest is stored in a file called
``.ravello.yml`` in the root directory of a source code repository. The
manifest is version controlled together with the rest of the code, and defines
applications that are relevant to the code contained in the repository. It can
define for example different kinds of development and test environments for the
code base. This concept of describing infrastructure as part of your source
code is called *infrastructure as code* and is an important concept in the
*devops* movement.

We will use one of the example applications bundled with TestMill to illustrate
this. On a command-line, issue the following commands::

    $ git clone https://github.com/ravello/testmill
    $ cd testmill/examples/multivm

The directory ``examples/multivm`` contains a simple blog written in Python
using the Pyramid framework. You will see that there is a file called
``.ravello.yml`` in that directory. Its contents are:

.. code-block:: yaml

    language: nodefaults
    applications:
    -   name: unittest
        vms:
        -   name: fedora17
            sysinit:
            -   yum install -y postgresql-devel
            prepare:
            -   sudo pip install -r requirements.txt
            execute:
            -   nosetests

    -   name: acceptance
        vms:
        -   name: db
            image: fedora17
            sysinit:
            -   deploy/setup-postgres.sh
            prepare:
            -   sudo systemctl restart postgresql.service

        -   name: web
            image: fedora17
            sysinit:
            -   yum install -y postgresql-devel
            prepare:
            -   sudo pip install -r requirements.txt
            -   sudo python setup.py develop
            execute:
            -   initialize_blog_db production.ini
            -   killall pserve || true
            -   nohup pserve production.ini --daemon
            services:
            -   http-alt

As you see, the file is in YAML format. The manifest defines two applications:
``unittest`` and ``acceptance``. The former consists of one virtual machine
only, based on Fedora 17. The latter consists of two virtual machines, one
database server and one web server. The manifest also defines the workflow for
each application. This is done using the ``sysinit:``, ``prepare:`` and
``execute:`` keys.

We will explain the manifest in much more detail later. For now, just observe
the behavior of TestMill when you run an application. Issue these commands::

    $ ravtest login
    $ ravtest run acceptance

The second command may take up to 10-15 minutes to complete the first time you
run it while the 'acceptance' application is being constructed, published to a
cloud, and while the workflows are run. After it is done, the output will be
something like this::

    Using 'multivm' as the project name.
    Detected a python project.
    Created new application `acceptance:1`.
    Waiting until application is ready...
    Progress: 'P' = Publishing, 'S' = Starting, 'C' = Connecting
    ===> PPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPCCCCCCCCCCCCCCCCCCCCCCCCC DONE
    Starting run `2c044b0ef5c878bf80232bf22e9224cf`.
    Executing tasks on 2 virtual machines...

    == Output for task `execute` on VM `web`:

    pserve: no process found
    nohup: ignoring input and appending output to `nohup.out'

    All tasks were executed succesfully!

    == The following services will be available for 90 minutes:

    On virtual machine `db`:
        * ssh: 54.234.131.13 port 22

    On virtual machine `web`:
        * http-alt: http://54.242.158.231:8080/
        * ssh: 54.242.158.231 port 22

Go ahead and point your web browser to the link indicated below the 'web` VM.
You should see a simple blog running there.
