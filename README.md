Nereid Image Transformation Module
==================================

This module works as a dynamic image resizing addon for the statifc file
functionality in Nereid.

[![Build Status](https://travis-ci.org/openlabs/nereid-image-transformation.svg?branch=develop)](https://travis-ci.org/openlabs/nereid-image-transformation)
[![Downloads](https://pypip.in/download/trytond_nereid-image-transformation/badge.svg)](https://pypi.python.org/pypi/trytond_nereid-image-transformation/)
[![Latest Version](https://pypip.in/version/trytond_nereid-image-transformation/badge.svg)](https://pypi.python.org/pypi/trytond_nereid-image-transformation/)
[![Development Status](https://pypip.in/status/trytond_nereid-image-transformation/badge.svg)](https://pypi.python.org/pypi/trytond_nereid-image-transformation/)
[![Coverage Status](https://coveralls.io/repos/openlabs/nereid-image-transformation/badge.svg?branch=develop)](https://coveralls.io/r/openlabs/nereid-image-transformation?branch=develop)

How to use
----------

The module introduces a new URL handler to the static file module, which
takes a URL path in which transformation commands could be embedded to
dynamically resize, rotate (TODO) and do various other tranformations.

A note of warning
-----------------

Image manipulation is slow! Really Slow!

Hence, this module is designed to be used with a frontend cache. The
responses from the module by default has instructions for frontend caches
to store the file in cache for 86400 seconds (equivalent to a day).

It is also recommended to use X-Send-File configuration with Nereid and
your web server (apache, nginx) to speed up delivery of images.

Examples
--------

    {{ product.large_image.transform_command().thumbnail(120, 120).resize(100, 100) }}


Using the above in a template should result in the following URL:

    /en_US/static-file-transform/1/thumbnail,w_120,h_120,m_n/resize,w_100,h_100,m_n.png
