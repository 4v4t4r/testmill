Installation Instructions
=========================

This page contains a operating system specific installation instructions

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
