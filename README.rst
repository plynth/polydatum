=========
Polydatum
=========

A Python enscapsulated persitance layer for supporting many data access layers.

Very rough at the moment, only offers basic functionality.

Principals
----------

- Methods that get an object should return `None` if an object can not be found.
- Methods that rely on an object existing to work (such as `create` that relies on a parent object) should raise `NotFound` if the parent object does not exist.

Testing
-------

To run tests you'll need to install the test requirements:

    pip install -r src/tests/requirements.txt

Run tests:

    python src/tests/runtests.py