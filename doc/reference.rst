*********
Reference
*********

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
image     string  The name of an image in the libary.
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
