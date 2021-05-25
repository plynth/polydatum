Development
===========

Running Tests
-------------

To run tests::

    make test


To run tests with pytest directly::

    make test.shell
    py.test --pdb


Formatting & Linting
--------------------

    make lint
    make format


Poetry
------

Dependencies are managed with [poetry](https://python-poetry.org/). To get a shell for using poetry::

    make poetry.shell

Publish::

    poetry publish
