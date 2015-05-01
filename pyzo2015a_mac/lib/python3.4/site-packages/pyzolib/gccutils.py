# -*- coding: utf-8 -*-
# Copyright (c) 2012, The Pyzo team
#
# This file is distributed under the terms of the (new) BSD License.

""" Module gccutils

Utilities to make sure there is a working gcc compiler. Particularly for
on Windows (MinGW and MinGW-W64) and also on Mac.

"""

import os
import sys
import struct
import subprocess

from pyzolib.paths import ISWIN, ISMAC, ISLINUX

# todo: test on Mac and Linux (Windows ok)
def has_gcc():
    """ has_gcc()
    
    Returns True if the gcc command invokes the gcc compiler.
    
    """
    
    # Use subprocess to see if the gcc executable is there
    try:
        p = subprocess.Popen('gcc --version', stdout=subprocess.PIPE, shell=True)
        text = p.stdout.readline().decode('utf-8').rstrip()
    except OSError:
        text = ''
    
    # Check
    if text.startswith('gcc'):
        return text
    else:
        return False


def gcc_dir():
    """ gcc_dir()
    
    Get the path to the directory containing the GCC compiler. 
    Search in different places, including the Pyzo directory.
    On Windows searches the default installation dirs (c:/mingw*).
    
    """
    
    # Get number of bits of this process
    NBITS = 8 * struct.calcsize("P")
    
    # Define gcc names on different OS's
    if ISWIN:
        dirName, exeName = 'mingw%i' %NBITS, 'gcc.exe'
    else:
        dirName, exeName = 'gcc%i' %NBITS, 'gcc'
    
    # Init
    possible_paths = []
    
    # Is Pyzo there, and is there a mingw install? If so, prefer that one
    path = None#pyzo_dir()
    if path:
        path = os.path.join(path, 'ext', dirName)
    if path and os.path.isdir(path):
        possible_paths.append(path)
    
    # Init possible paths with default mingw directories
    if ISWIN:
        possible_paths.append(os.path.join(sys.prefix, 'mingw'))
        if NBITS == 32:
            possible_paths.extend(['c:/mingw32', 'c:/mingw'])
            possible_paths.extend(['c:/mingw-w64', 'c:/mingw64'])
        elif NBITS == 64:
            possible_paths.extend(['c:/mingw-w64', 'c:/mingw64'])
            possible_paths.extend(['c:/mingw', 'c:/mingw32'])
    elif ISMAC:
        pass
        # todo: what to do on Mac, or would that be /usr/bin etc
    
    # Check possible directories
    for path in possible_paths:
        path_gcc = os.path.join(path, 'bin', exeName)
        if os.path.isfile(path_gcc):
            return path
    else:
        return None


def _insert_gcc_dir_in_pythonpath():
    """ Try to find the gcc directory and add it to the PATH env. variable.
    This function can safely be run multiple times.
    """
    
    # Can we find a gcc installation?
    # This tries to find one that matches with the number of bits of the
    # Python installation
    path = gcc_dir()
    if not path:
        return False # Let's hope it is installed in another way
    else:
        pathToAdd = os.path.join(path, 'bin')
        #print('Found gcc compiler in "%s"' % path)
    
    # Get all directories in PATH, excluding the one we want to add
    s = os.path.pathsep
    paths1 = os.environ['PATH'].split(s)
    paths1 = [p for p in paths1 if (p and p!=pathToAdd)]
    
    # Add to the front of PATH to make it override the default gcc
    paths1.insert(0, pathToAdd)
    os.environ['PATH'] = s.join(paths1)
    
    return True


def prepare_gcc():
    """ prepare_gcc()
    
    Make sure that the bin directory of the gcc compiler is in the PATH.
    Modifies os.environ['PATH'].
    
    Call this before compiling a Cython module, and also when freezing, 
    because compiled Cython modules may dynamically link to gcc libraries.
    
    """
    
    # Try inserting gcc dir of Pyzo (or MinGW on Windows) in os.environ['PATH']
    inserted = _insert_gcc_dir_in_pythonpath()
    
    # Check if we now have a working gcc
    working = has_gcc()
    
    # Let the user know if it's not working
    if not working:
        if inserted:
            print('Warning: gcc directory detected, but gcc not working.')
        else:
            print('Warning: gcc not available; please install.')
