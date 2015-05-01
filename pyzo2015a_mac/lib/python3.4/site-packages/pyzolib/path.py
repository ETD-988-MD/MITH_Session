# -*- coding: utf-8 -*-
# Copyright (c) 2012, The Pyzo team
#
# This file is distributed under the terms of the (new) BSD License.

"""
Definition of a Path class (that inherits from string)
for object oriented path processing.

Inspired by http://pypi.python.org/pypi/path.py,
but modfied to also work on Python 3 and a bit more compact (a simpler API).

"""

import os
import sys
import fnmatch

print('Note about pyzolib.path - better use pathlib (part of py34)')


# Python 2/3 compatibility (from six.py)
if sys.version_info[0] == 3:
    text_type = str
    string_types = str,
else:    
    text_type = unicode
    string_types = basestring,


class Path(text_type):
    """ Path(path, clean=True)
    
    Object oriented approach to path handling. If clean is True,
    applies expandvars, expanduser, normpath and realpath to clean
    the path.
    
    Concatenate paths using the "/" operator.
    """
    
    def __new__(cls, path, clean=True):
        # Clean path
        if clean:
            path = os.path.expandvars(path)
            path = os.path.expanduser(path)
            path = os.path.normpath(path)
            #path = os.path.realpath(path) # this kills relative paths
        # Instantiate
        obj = text_type.__new__(cls, path)
        return obj
    
    ## Magic functions
    
    def __repr__(self):
        return 'Path(%s)' % text_type.__repr__(self)
    
    # Adding a path and a string yields a path.
    def __add__(self, other):
        if isinstance(other, string_types):
            return Path(text_type.__add__(self, other), False)
        else:
            return NotImplemented()

    def __radd__(self, other):
        if isinstance(other, string_types):
            return Path(other.__add__(self), False)
        else:
            return NotImplemented()
    
    # The / operator joins paths.
    def __div__(self, rel):
        """ fp.__div__(rel) == fp / rel == fp.joinpath(rel)

        Join two path components, adding a separator character if
        needed.
        """
        return Path(os.path.join(self, rel)) # Clean=True, so '..' is converted
    
    # Make the / operator work even when true division is enabled.
    __truediv__ = __div__
    
    
    def __eq__(self, other):
        return str.__eq__(self.normcase(), os.path.normcase(other))
    
    def __neq__(self, other):
        return not Path.__eq__(self, other)

    def __hash__(self):
        # The __eq__ and __neq__ make it unhashable, thus we need __has__ too
        return str.__hash__(self)
    
    
    ## Identity
    
    @property
    def isfile(self):
        return os.path.isfile(self)
    
    @property
    def isdir(self):
        # Add os.sep, because trailing spaces seem to be ignored on Windows
        return os.path.isdir(self+os.sep) 
    
    @property
    def stat(self):
        return os.stat(self)
    
    ## Getting parts 
    
    @property
    def dirname(self):
        return Path(os.path.dirname(self), False)
    
    @property
    def basename(self):
        return Path(os.path.basename(self), False)
    
    @property
    def ext(self):
        return os.path.splitext(self)[1]
    
    @property
    def drive(self):
        drive, r = os.path.splitdrive(self)
        return Path(drive, False)
    
    ## Listing
    
    def listdir(self, pattern=None):
        """ Return the list of entries contained in this directory.
        """
        names = os.listdir(self)
        if pattern is not None:
            names = fnmatch.filter(names, pattern)
        return [self / child for child in names]
    
    def dirs(self, pattern=None):
        """ Return the list of directories contained in this directory.
        """
        return [p for p in self.listdir(pattern) if p.isdir]
    
    def files(self, pattern=None):
        """ Return the list of file contained in this directory.
        """
        return [p for p in self.listdir(pattern) if p.isfile]
    
    ## Transforming
    
    def normcase(self):
        """ Makes the path lowercase on case-insensitive file systems
        (like Windows), otherwise (e.g. Linux) leaves the path unchanged.
        """
        return Path(os.path.normcase(self), False)
    
    def realpath(self):
        """ Return the absolute version of a path, follow symlinks.
        """
        return Path(os.path.abspath(self), False)
    
    def abspath(self):
        """ Return the absolute version of a path.
        """
        return Path(os.path.abspath(self), False)
    
    def relpath(self, start=None):
        """ Return a relative filepath either from the current directory
        or from an optional start point.
        """
        return Path(os.path.relpath(self, reference), False)
    
    # todo: a walk function
    
    ## Actions
    
    def makedir(self, mode=0o777, tolerant=False):
        """ Make dir. If tolerant is True, will only attempt if the dir
        does not yet exist.
        """
        if not tolerant or not os.path.isdir(self):
            os.mkdir(self, mode)
    
    def makedirs(self, mode=0o777, tolerant=False):
        """ Make dir (and parent dirs). If tolerant is True, will only
        attempt if the dir does not yet exist.
        """
        if not tolerant or not os.path.isdir(self):
            os.makedirs(self, mode)
    
    def removedir(self, tolerant=False):
        """ Remove directory. If tolerant is True, will only attempt
        if the dir exists.
        """
        if not tolerant or os.path.isdir(self):
            os.rmdir(self)
    
    def removedirs(self, tolerant=False):
        """ Remove directory and all empty intermediate ones.  If
        tolerant is True, will only attempt if the dir exists.
        """
        if not tolerant or os.path.isdir(self):
            os.removedirs(self)
    
    def remove(self, tolerant=False):
        """ Remove file.  If tolerant is True, will only attempt if the
        file exists.
        """ 
        if not tolerant or not os.path.isfile(self):
            os.remove(self)


if __name__ == '__main__':
    
    p = Path('c:/almar')
    s = set()
    s.add(p)
    s.add(p)
    
    
    