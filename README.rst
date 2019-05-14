=========
Polydatum
=========

.. image:: https://secure.travis-ci.org/plynth/polydatum.png
    :target: http://travis-ci.org/plynth/polydatum
    :alt: Build Status

A Python encapsulated persistence layer for supporting many data access layers.

---------
Changelog
---------

0.9.0
=====

* Added support for Python 3.6+


0.8.4
=====

* Added context middleware
* Added read only Meta for context
* First pass at removing LocalProxy magic to make it easier to integrate with other frameworks
* Made it so you can use simple generator functions for resources
* Added replace service/resource and made it hard to accidentally register on top of an existing one
* Simplified exception handling on DataAccessContext so that only in-context or middleware exceptions are raised. Resource exit exceptions are suppressed.

Bug Fixes
---------

* Fixed a bug that prevented usage of a resource in __exit__

----------
Components
----------

DataManager
===========

The DataManager is the central object of Polydatum. It is a top-level registry for
Services, Resources, and Middleware. Typically an application has one DataManager
per process. The DataManager also manages Contexts and gives access the DAL.


Context
=======

The Context contains the current state for the active request. It also provides
access to Resources. When used in an HTTP framework typically one context is
created at the start of the HTTP request and it ends before the HTTP response
is sent.

When used with task managers such as Celery, the Context is created at the
start of a task and ends before the task result is returned.


DAL
===

The DAL is the "Data Access Layer". The DAL is the registry for all Services.
To make call a method on a Service, you start with the DAL.

::

    result = dal.someservice.somemethod()


Service
=======

Services encapsulate business logic and data access. They are the Controller of
MVC-like applications. Services can be nested within other services.

::

    dal.register_services(
        someservice=SomeService().register_services(
            subservice=SubService()
        )
    )

    result = dal.someservice.subservice.somemethod()


Meta
====

Meta is data about the context and usually includes things like the active
user or HTTP request. Meta is read only and can not be modified inside the
context.

::

    class UserService(Service):
        def get_user(self):
            return self._ctx.meta.user

    dm = DataManager()
    dm.register_services(users=UserService())

    with dm.context(meta={'user': 'bob'}) as ctx:
        assert ctx.dal.test.get_user() == 'bob'


Resource
========

Resources are on-demand access to data backends such as SQL databases, key
stores, and blob stores. Resources have a setup and teardown phase. Resources
are only initialized and setup when they are first accessed within a context.
This lazy loading ensures that only the Resources that are needed for a
particular request are initialized.

The setup/teardown phases are particularly good for checking connections out
from a connection pool and checking them back in at the end of the request.

::

    def db_pool(context):
        conn = db.checkout_connection()
        yield conn
        db.checkin_connection(conn)

    class ItemService(Service):
        def get_item(self, id):
            return self._data_manager.db.query(
                'SELECT * FROM table WHERE id={id}',
                id=id
            )

    dm = DataManager()
    dm.register_services(items=ItemService())
    dm.register_resources(db=db_pool)

    with dm.dal() as dal:
        item = dal.items.get_item(1)


Middleware
==========

Middleware have a setup and teardown phase for each context. They are
particularly useful for managing transactions or error handling.

Context Middleware may only see and modify the Context. With the
Context, Context Middleware can gain access to Resources.

::

    def transaction_middleware(context):
        trans = context.db_resource.new_transaction()
        trans.start()
        try:
            yield trans
        except:
            trans.abort()
        else:
            trans.commit()

    dm = DataManager()
    dm.register_context_middleware(transaction_middleware)


----------
Principles
----------

- Methods that get an object should return `None` if an object can not be found.
- Methods that rely on an object existing to work (such as `create` that relies
  on a parent object) should raise `NotFound` if the parent object does not exist.
- All data access (SQL, MongoDB, Redis, S3, etc) must be done within a Service.


--------------
Considerations
--------------

Middleware vs Resource
======================

A Resource is created on demand. It's purpose is to create a needed resource
for a request and clean it up when done. It is created inside the context (and possibly
by middleware). Errors that occur during Resource teardown are suppressed.

Middleware is ran on every context. It is setup before the context is active and
torndown before resources are torndown. It's purpose is to do setup/teardown within
the context. Errors that occur in-context are propagated to middleware. Errors that
occur in middleware are also propagated.


Testing
-------

To run tests you'll need to install the test requirements:

    pip install -e .
    pip install -r src/tests/requirements.txt

Run tests:

    cd src/tests && py.test

