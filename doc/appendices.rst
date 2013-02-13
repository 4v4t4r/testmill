**********
Appendices
**********

Installation Instructions
=========================

This section contains a operating system specific installation instructions

.. _linux-installation:

Installing on Linux
-------------------

Installing on Linux is relatively straightforward. The instructions below are
routinely tested in Ubuntu and Fedora, and should work on other Linux variants
as well.

Your distribution should provide a Python version 2.6, 2.7, 3.2 or 3.3. Most
Linux distributions today provide one of these versions. However,
RHEL/CentOS/Scientific Linux version 5 is the notable exception. These
distributions include Python 2.5 which is too old to run TestMill. To find your
your Python version, issue the command ``python -V`` on the command line.

1. Install System Dependencies

   It is recommend that you install the setuptools, PyCrypto and PyYAML
   dependencies that are provided by the distribution. All mainstream
   distributions provide a version of these packages:

   For Ubuntu and Debian (derived) distributions::

    $ sudo apt-get install python-setuptools python-crypto python-yaml 

   For Fedora, RHEL, and Red Hat derived distributions::

    $ sudo yum install python-setuptools python-crypto PyYAML

2. Install TestMill from the Python Package Index::

    $ sudo easy_install ravello-testmill


.. _mac-installation:

Installing on Mac
-----------------

Mac OSX versions 10.6 (Snow Leopard) and higher ship with a sufficiently recent
Python version out of the box. Installation is still somewhat complicated
because of the dependency on PyCrypto (via Fabric and Paramiko). Since there
are no binary packages for PyCrypto on the Python Package Index, you will need
to compile it yourself. This requires a C compiler.

1. Install Xcode

   Xcode can be found on the Mac App Store and is available for free. After
   you've installed it, go to Xcode -> Preferences -> Components, and install
   the "Command Line Tools" component.

2. Install TestMill

   You can now install Ravello TestMill directly from the Python Package Index.
   Open up a terminal and issue::

    $ sudo easy_install ravello-testmill

   This step will likely give an error that a file called ``yaml.h`` is not
   found. It is safe to ignore this error.

.. _windows-installation:

Installing on Windows
---------------------

Windows is the most complicated platform to install TestMill on. This is
because Windows neither provides Python nor a C compiler by default. The C
compiler is needed because of the dependency on PyCrypto (via Fabric and
Paramiko).

1. Download and Install Python

  Download the executable Python installer from the `Python home page
  <http://www.python.org/download/>`_.  It is recommended to select the latest
  2.7.x version.  Run the installer, and install Python to ``C:\Python27``.
  Add ``C:\Python27`` and ``C:\Python27\Scripts`` to your ``PATH``.

2. Download and install MinGW.

   Download the latest installer for MinGW from its `sourceforce project page
   <http://sourceforge.net/projects/mingw/files/Installer/mingw-get-inst/>`_.
   Run the installer, select the C compiler, and then install into
   ``C:\MinGW``.  Add ``C:\MinGW\bin`` to your ``PATH``.
   
3. Download and install Git
   
   We need to install Git to get the ``patch.exe`` command that we need for
   Step 5. Git ships with a complete Unix environment and contains the only
   version of patch that I know works on Windows.

   Download the latest installer from the `Git web site
   <http://git-scm.com/download/win>`_.  Install Git. Select the option "Run
   Git and Included Unix Tools from the Windows Command Prompt".  This will
   automatically add Git and the Unix tools to your ``PATH``.

4. Install Setuptools

   Get the binary installer from the `setuptools page
   <http://pypi.python.org/pypi/setuptools>`_ on the Python Package Index.  Run
   the installer, and install to the default location.

5. Patch distutils.

   Unfortunately there is a bug in distutils where it will pass a flag to the
   MinGW compiler that it does not understand.  This is reported in `this
   Python Issue <http://bugs.python.org/issue12641>`_, and as as of the time of
   writing (Feb 2013) still not fixed.  Download the patch from `this Github
   GIST <https://gist.github.com/4466320>`_. Save it to ``C:\Python27\Lib``.
   Now open a command prompt. Go to ``C:\Python27\Lib`` and issue the following
   command::
   
    $ patch -p0 < distutils.patch
    
6. Install from Python Package

   Index We can now install from the Python package index. Open a command
   prompt and issue::

    $ easy_install ravello-testmill

   This step will likely give an error that a file called ``yaml.h`` is not
   found. It is safe to ignore this error.

.. _standard-images:

Standard Images
===============

TestMill comes with a few standard images that are available through the
Ravello public image library. You can use the images as-is, or use them as the
basis for your own images.

The images are built using the Red Hat `Oz`_ tool. The recipes can be found in
the `images/ directory`_ in the TestMill Github repo. The images have the
following basic properties:

 * A user "ravello" is present. The user has the password "ravelloCloud" (but
   password logins are only available on the VNC console).

 * The "ravello" user can ``sudo`` to root without need for a password.

 * Root has a disabled password.

 * `Cloud-init`_ is configured to use the "NoCloud" data source, and accept an
   authorized key for the user "ravello".

 * Ssh is configured to accept only public key authentication. The root user is
   not allowed to log in via ssh.

 * The image uses DHCP to get an IPv4 network address. IPv6 is disabled. The
   network configuration is tweaked so that no Mac address binding is
   performed.

The images are basic OS installs with some useful development tools and runtime
stacks installed. The images try to be as close as possible to the original OS.
With very few exceptions, only software that is shipped by the distribution is
installed.

The images contain the following software:

 * C/C++ runtime and development environment. This includes the system provided
   versions of ``gcc``, ``g++``, ``make``, the autotools, etc.

 * Python runtime and development environment. The system provides Python
   version is provided. Also installed are ``pip``, ``easy_install`` and
   ``virtualenv``.

 * Python 3.x runtime and development environment. Python 3 is co-installed
   with Python 2 and available as ``python3``. Also provides ``pip3``,
   ``easy_install3`` and ``virtualenv3``.

 * A Ruby runtime and development environment. This includes the system version
   of Ruby, the Ruby development headers and libraries, Rake and Bundler.

 * A Java runtime and development environment, including Maven and Ant. The
   system provided OpenJDK version is installed.

 * A Clojure development environment. This is essentially just the ``lein``
   build tool. When it is first run, it will download Clojure from Maven
   central. On Fedora, the latest (2.0) version from upstream is provided
   because the system version either doesn't exist or is buggy.

 * MySQL and PostgreSQL.


The table below lists which images have what software available.

==========  ======================  ======  ========  ======  ======  =======
Name        Description             Python  Python 3  Ruby    Java    Clojure
==========  ======================  ======  ========  ======  ======  =======
ubuntu1204  Ubuntu 12.04.x LTS      2.7.3   3.2.3     1.8.7   1.6.0   any
            (latest minor update)
ubuntu1210  Ubuntu 12.10            2.7.3   3.2.3     1.9.3   1.7.0   any
fedora16    Fedora 16               2.7.3   3.2.3     1.8.7   1.7.0   any
fedora17    Fedora 17               2.7.3   3.2.3     1.9.3   1.7.0   any
fedora18    Fedora 18               2.7.3   3.3.0     1.9.3   1.7.0   any
centos6     CentOS 6.x              2.6.6   N/A       1.8.7   N/A     N/A
            (latest minor update)
==========  ======================  ======  ========  ======  ======  =======


Schema Reference
================

.. _application-ref:

Applications
------------

The table below lists the available keys for applications that are specified in
the manifest.

=========  ======  ===================================================
Name       Type    Description
=========  ======  ===================================================
name       string  The application name. Must be unique within the
                   manifest.
blueprint  string  The blueprint this application is based on.
                   Default: null (= no blueprint)
keepalive  int     The number of minutes before this application is
                   shut down. Starts counting when the machine is
                   started up. Default: 90 minutes.
vms        list    The virtual machines that make up this application.
                   List entries must contain VMs, see below.
=========  ======  ===================================================

.. _vm-ref:

Virtual Machines
----------------

The following table lists the available keys for virtual machines in the
manifest.

========  ======  ===================================================
Name      Type    Description
========  ======  ===================================================
name      string  The name of the VM. Must be unique in
                  the application. Mandatory.
image     string  The name of an image in the library.
                  Must be provided in case this application
                  does *not* derive from a blueprint.
tasks     list    List of tasks. Entries must be tasks, see below.
                  Tasks are executed in the order specified.
services  list    List of external services provided by this VM.
                  Entries must be ints or strings. For ints, this
                  specifies the port number. For strings, the service
                  name (looked up using ``getservbyname()``).
========  ======  ===================================================

.. _task-ref:

Tasks
-----

The following table lists the available keys for tasks that are specified for a
virtual machine.

========  ======  ===================================================
Name      Type    Description
========  ======  ===================================================
name      string  The name of the task. Must be unique
                  within the VM. Mandatory.
class     string  The name of the Python class imlementing
                  the command. Should point to an importable Python
                  class, which would typically be part of the
                  repository. Default: ``testmill.tasks.Task``.
command   list    List of shell commands. Must be a list of strings.
                  The commands are executed in order.
user      string  Whether to use sudo to execute the commands as the
                  specified user.
quiet     bool    Whether to display output for this command.
                  Default: false  (= show output)
========  ======  ===================================================


.. _env-vars:

Environment Variables
=====================

The following environment variables are available to shell commands that are
executed as part of a task:

======================  ====================================================
Name                    Description
======================  ====================================================
RAVELLO_TEST_ID         The ID of the current run. A random, 32-character
                        hexadecimal string.
RAVELLO_TEST_USER       The user name of the test user. Will be "ravello".
RAVELLO_APP_ID          The ID of the Ravello application. A 64-bit integer.
RAVELLO_APP_NAME        The name of the Ravello application. This will
                        be the project name + ":" + manifest application
                        name + ":" + unique suffix.
RAVELLO_APPDEF_NAME     The name of the application as defined in the
                        manifest.
RAVELLO_PROJECT         The project name as define in the manifest.
RAVELLO_SERVICE_URL     The URL to the Ravello API, in case the
                        application need to make API calls.
RAVELLO_SERVICE_COOKIE  A cookie granting access to the Ravello API, in
                        case the application needs to make API calls.
RAVELLO_VM_ID           The ID of the Ravello VM. A 64-bit integer.
RAVELLO_VM_NAME         The name of the Ravello VM.
======================  ====================================================


.. _custom-tasks:

Custom Tasks
============

Normally tasks are specified as a sequence of shell commands. However, for
greater flexibility, it is also possible to provide a custom Python class to
execute the command. This gives greater freedom, and can e.g. be used to
transfer files between the local and the remote system (this is how the default
"deploy" task is implemented, in this case by the class
``testmill.tasks.DeployTask``).

The tasks are specified using the ``class:`` key in a task. The value must be a
string, and be an fully qualified (= with module) importable Python class. The
class should derive from ``fabric.tasks.Task``. In addition:

 * The task constructor should take arbitrary keyword arguments. It will be
   passed in all the keys from the ``task:`` descriptor. These keys should be
   set as attributes on the instance.

 * The task must have a ``run()`` method that performs the desired action.

The task may find it useful to use the following two singleton class instances
that provide configuration and shared state: ``testmill.state.env`` and
``fabric.api.env``. See the `Fabric documentation`_ and the TestMill `source
code`_ for a description of the avaible attributes. Also the class will likely
use the operations defined in ``fabric.api``.

.. _`Oz`: https://github.com/clalancette/oz/wiki
.. _`images/ directory`: https://github.com/ravello/testmill/tree/master/images
.. _`Cloud-init`: https://help.ubuntu.com/community/CloudInit
.. _`Fabric documentation`: http://docs.fabfile.org/en/1.5/usage/env.html
.. _`source code`: https://github.com/ravello/testmill/blob/master/lib/testmill/tasks.py
