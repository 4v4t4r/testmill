Welcome to Ravello TestMill
===========================

TestMill is an orchestration tool to build single- and multi-VM application
environments on the fly from a textual description and run workflows in them.
The focus is on providing clean and high-fidelity environments for running any
kind of development and test workloads, including per-developer development
environments, unit tests, system tests, integration tests, functional tests and
usability tests.

TestMill uses the `Ravello`_ `Cloud Application Hypervisor`_ as the
virtualization engine to reproduce almost any legacy or new-app environment in
the cloud with high fidelity. It also uses the excellent `Fabric`_ toolkit as a
robust remote execution environment on which the workflows are built.

TestMill fully subscribes to the devops mantra of *Infrastructure as Code*. The
environments that TestMill builds and manages are described by a concise
textual format that can be version controlled, and is intended to be part of
the repository containing the code it provides infrastructure for.

Contents
--------

.. toctree::
   :maxdepth: 1

   introduction
   manifest
   commands
   appendices
   changelog


.. _`Ravello`: http://www.ravellosystems.com
.. _`Cloud Application Hypervisor`: http://www.ravellosystems.com/technology
.. _`Fabric`: http://fabfile.org
