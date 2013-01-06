Ravello TestMill
================

A system test driver for Ravello.

Installation
============

Ravello TestMill is written in Python, and has the following requirements:

 * Python 2.x (x >= 6) or Python 3.x (x >= 3).
 * Fabric. Only versions >= 1.4.1 have been tested.
 * PyYAML. Any reasonable version should do.
 * Setuptools. Any resaonable version should do.

Fabric is a somewhat complicated dependency because it depends on Paramiko (a
Python SSH2 implementation) which in turn depends on PyCrypto. And because
there are no binary packages for PyCrypto are available on the Python Package
Index, you will either need to get it from your OS or you need to compile it
youself.

Generic Installation Instructions
---------------------------------

The following instructions will load Ravello TestMill and all its dependencies
from the Python Package Index (the '#' prompt means to run this as root, or via
sudo)::

  # easy_install ravello-testmill

This will require that you have a C compiler installed if PyCrypto is not yet
available on your local system.

OS Specific Installation instructions
-------------------------------------

See the Ravello TestMill Wiki_ for installation instructions specific to your
Operating System.

.. _Wiki: https://github.com/ravello/testmill/wiki
