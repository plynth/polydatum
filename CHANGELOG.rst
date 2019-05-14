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