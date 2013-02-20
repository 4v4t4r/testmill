Changelog
=========

New in version 0.9.10
---------------------

* Fix an important bug that would prevent first-time users from
  using TestMill due to an issue with keypair generation.

New in version 0.9.9
--------------------

* Always publish to Amazon. Amazon is preferred because it allows us
  to stop instances rather than kill them.
* Allow specification of the memory size for the VMs. The default is
  2048 MiB.
* Allow specification of the number of CPUs.
* Add basic mercurial support (no parsing of .hginore files yet).

New in version 0.9.8
--------------------

* Fix a rather serious bug that could cause a deadlock in certain
  situation when a task failed.
* Improve the quick start in the documentation.

New in version 0.9.7
--------------------

* Fix an issue where the installer doesn't download all the required
  dependencies.
* Fix a critical issue where our shell glue (runtask.sh and preininit.sh)
  don't get installed.
* Some fixes in the test suite.

New in version 0.9.6
--------------------

* Many bug fixes.
* Greatly improved test coverage.

New in version 0.9.5
--------------------

* New commands: ``save``, ``restore``, ``clean`` and ``lint``.
* Much better blueprint support. Applications can be instantiated from
  blueprints.
* Orchestration support for creating multi-vm applications from images.

New in version 0.9.4
--------------------

* The "ravtest ssh" command has been added.
* Argument parsing of sub-commands has been improved.
* "ravtest run --dump" now outputs YAML format.
