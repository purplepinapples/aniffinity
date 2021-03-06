|forthebadge1| |forthebadge2| |forthebadge3|


aniffinity
==========

|rtd|

"An-knee-fin-knee-tea".

Calculate affinity between anime list users.


What is this?
-------------

Calculate the affinity between a user and another user on anime list
services. Refer to the `docs <#documentation>`__ for more info.


Install
-------

When the package is deployed to PyPI...,

..  code-block:: bash

    pip install aniffinity


Dependencies
------------

* json-api-doc
* Requests


Example Usage
-------------

..  code-block:: python

    from aniffinity import Aniffinity

    af = Aniffinity("YOUR_USERNAME", base_service="A_SERVICE")

    affinity, shared = af.calculate_affinity("OTHER_USERNAME", service="OTHER_SERVICE")

    print(affinity)
    # 79.00545465639877
    print(shared)
    # 82


Available Services
------------------

* `AniList <https://anilist.co>`__
* `Kitsu <https://kitsu.io>`__
* `MyAnimeList <https://myanimelist.net>`__

For more info, read the `docs <#documentation>`__.


Documentation
-------------

Documentation at https://aniffinity.readthedocs.io


Legal Stuff
-----------

Licensed under MIT. See `LICENSE <LICENSE>`__ for more info.


Cat Gif
-------

..  figure:: https://i.imgur.com/sq42SnU.gif
    :alt:


..  |forthebadge1| image:: http://forthebadge.com/images/badges/fuck-it-ship-it.svg
    :target: http://forthebadge.com
..  |forthebadge2| image:: http://forthebadge.com/images/badges/contains-cat-gifs.svg
    :target: http://forthebadge.com
..  |forthebadge3| image:: http://forthebadge.com/images/badges/built-with-love.svg
    :target: http://forthebadge.com

..  |rtd| image:: https://readthedocs.org/projects/aniffinity/badge/?version=latest
    :target: https://aniffinity.readthedocs.io/en/latest/
