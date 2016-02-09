Sparklines.py
=============

SVG sparklines in Python with a dead-easy API.


Why should you use Sparklines.py:

* Simple API
* Works with Pandas
* Intended to be used in the browser
* SVG graphics mean high quality everywhere
* No JavaScript dependencies

Useage
------

.. code-block:: python

    from sparklines import Sparkline

    some_data = np.random.normal(size=100).cumsum()
    Sparkline(some_data)

.. code-block:: python 

    from sparklines import Sparkline

    d1 = np.random.normal(size=100).cumsum()
    d2 = np.random.normal(size=100).cumsum()

    s1 = Sparkline(d1, width=300, height=50, show_max=True, show_min=True)
    s2 = Sparkline(d2, width=300, height=50)

    composition = s1 + s2

.. code-block:: python

    from sparklines import SparkBar
    d = np.random.normal(size=12).cumsum()
    SparkBar(d, bar_color="#afafaf", bar_spacing=1, height=50)

.. code-block:: python

    pd.DataFrame([s1, s2, s1 + s2]).style

Installation
------------

Currently this project is pre-alpha software and cannot yet be installed. You 
shouldn't use it yet.

TODO:
-----

- Write some documentation.
- Write tests.
- Add to PyPI.
- Possibly remove ``numpy`` dependency to keep things light.
- Improve API and add features like bands.
