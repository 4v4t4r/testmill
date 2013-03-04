***********************
Integrating with Fabric
***********************

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

Importing TestMill as a Library
===============================

The module ``testmill.fabric`` defines a publicly available API that is useful
for integrating with Fabric. You are recommended to import it as follows::

    from testmill import fabric as ravello

so you can refer to it simply as ``ravello`` in your code.

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
