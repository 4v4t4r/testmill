********
Commands
********

The primary interface into TestMill is via the command-line utility
``ravtest``. The utility has a option/command/option interface, very similar to
that of e.g. "git". The general form of a ravtest invocation is::

    $ ravtest [common options] <command> [command specific options]

Extensive on-line help is available. To get help on the general options, use::

    $ ravtest --help

To get help on a specific command instead, use::

    $ ravtest --help <command>

Common Options
==============

-u <user>, --user <user>
    Specifies the Ravello user name
-p <password>, --password <password>
    Specifies the Ravello password
-s <service_url>, --service-url <service_url>
    Specifies the Ravello API service URL
-q, --quiet
    Be quiet
-v, --verbose
    Be verbose
-d, --debug
    Show debugging information
-y, --yes
    Do not ask for confirmation
-h, --help
    Show help

Available Commands
==================

login
-----

.. autocmd:: login

logout
------

.. autocmd:: logout

ps
--

.. autocmd:: ps

run
---

.. autocmd:: run

ssh
---

.. autocmd:: ssh

save
----

.. autocmd:: save

restore
-------

.. autocmd:: restore

lint
----

.. autocmd:: lint
