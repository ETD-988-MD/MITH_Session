# -*- coding: utf-8 -*-
# Copyright (c) 2012, The Pyzo team
#
# This file is distributed under the terms of the (new) BSD License.

""" Package pyzolib

The pyzolib package provides basic functionality for the Pyzo environment.
It contains a collection of modules and small packages that should be
imported as "from pyzolib import xxx"

The packages currently are:
  * path - object oriented path processing (no more os.path.x)
  * paths - Get paths to useful directories in a cross platform manner.
  * qt - Proxy for importing QtCore et al. from PySide or PyQt4
  * ssdf - the Simple Structured Data Format (for config files and 
    scientific databases)
  * insertdocs - a sphynx pre-processor to include docstrings in the text,
    allowing readthedocs.org to host the docs without requiring importing code.
  * pyximport - for easy on the fly compilation of Cython, using the Pyzo 
    environment to establish the location of a gcc compiler.
  * gccutils - used by the above to manage the gcc compiler.
  * interprerers - list the Python interpreters available on this system.
  * dllutils - utilities to set the RPATH in dynamic libararies and 
    remove depndencies on the MSVCR from the embedded manifest.
  * shebang - for making shebangs in pyzo distro absolute.

"""

__version__ = '0.3.3'
