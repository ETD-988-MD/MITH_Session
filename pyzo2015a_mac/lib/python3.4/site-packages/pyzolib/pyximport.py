# -*- coding: utf-8 -*-
# Copyright (c) 2012, The Pyzo team
#
# This file is distributed under the terms of the (new) BSD License.

""" Module pyximport

Provides functionality to compile Cython files on the fly. Before installing
a cython module, call pyximport.install(). The module will be compiled if
necessary, and then imported.

Extra keyword arguments can be supplied to install() to control the 
compiling stage. In this manner even complex code can be compiled without
the need of a setup script. See the docs of the install function for more 
information.

Example1
--------
from pyzo import pyximport
pyximport.install()
import your_cython_module


Example2
--------
from pyzo import pyximport
pyximport.install(  language='c++', 
                    compiler='native',
                    include_dirs=['include'],
                    library_dirs=['lib'], 
                    libraries=['1394camera'] )
import your_cython_module

"""


Remarks_related_to_pyzo = """

We need a clear distinction between developer and end-user. The latter is the
person who uses apps that are created using Pyzo. The end-user does not have
a Pyzo directory, and should not need a gcc compiler; cx_freeze will make
sure that all the libraries are packed. But we have to help cx_freeze do that.
For one thing, we need normal "import a_cython_module" statements.


Notes for Windows (Pyzo related):
  * MinGW or Microsoft studio. Not sure if latter also works with free version.
  * MinGW is relatively portable, we could send it along with the rest of Pyzo.
  * But MinGW has no 64 bit support, The MinGW-w64 project does, but its less stable.
  * To get MinGW or MinGW-w64 relatively easy: http://tdm-gcc.tdragon.net
  
  * Users with 32bit should get mingw, others 64bit. Cross compiling, nah.
  * Both the compile-args and link-args need '-m32' and '-DMS_WIN32' (or 64)

  * The TDM version compiles but is very unstable, getting invalid accesss errors
  * The normal version (sezero build) asks for msvcr90.dll, so ship that along!!
    
  * libpython32.a needs to be placed in [pythondir]libs directory. Otherwise
    distutils tries to build it, which fails on Py3k.
  * the mingw directory must be in os.environ['PATH'], also when freezing!

Troubleshooting:
  * Make sure c:/mingw/bin is in the PATH
  * Make sure to include the numpy libs
  
Known problems on Windows:
  * "No module named msvccompiler in numpy.distutils"
    "Unable to find vcvarsall.bat"
    --> there is no MS compiler installed. Install visual studio 2008. Not 2010!
  * "'gcc' is not recognized as an internal or external command, operable program or batch file."
    "Could not locate executable gcc"
    --> Mingw is used, but is not installed
  * "fatal error LNK1181: cannot open input file 'files.obj'"
    There are probably spaces in the paths to the libraries.


"""

# todo: test when frozen
# todo: test when used from a deployed site_packages with no admin rights
# todo: in that case, can we not use a temp directory?

import os, sys
import struct
import traceback
import shutil
import imp

from pyzolib import paths
from pyzolib.gccutils import prepare_gcc

# Get number of bits of this process
NBITS = 8 * struct.calcsize("P")


def getFileNames(moduleName, path='', sourceExt='.pyx'):
    """ Get source and binary file names:
      * sourceName: the filename of the .pyx source file
      * binName: the filename of the corresponding .pyd/.os binary file
      * binName2: like binName but with mangled name using Python version+bits
    """
    # Source file name
    sourceName = os.path.join(path, moduleName + sourceExt)
    # Binary name (plain)
    if sys.platform.startswith('win'):
        binName = os.path.join(path, moduleName + '.pyd')
    else:
        binName = os.path.join(path, moduleName + '.so')
    # Binary name with extension to mark python version and nbits
    binName2, ext = os.path.splitext(binName)
    binName2 = binName2 + '_py%i%i_%i' + ext
    binName2 = binName2 % (sys.version_info[0], sys.version_info[1], NBITS)
    return sourceName, binName, binName2


def getFileModificationTimes(*args):
    """ Given filenames as arguments, get the modification times of each
    file, or 0 of the file does not exist.
    """
    # ms accuracy, on Linux shutil.copy still results in a tiny winy difference
    T = []
    for arg in args:
        if os.path.isfile(arg):
            t = os.stat(arg).st_mtime
            t = round(t, 3) 
        else:
            t = 0
        T.append(t)
    
    # Done
    return tuple(T)


def locate_cython_module(moduleName):
    """ Locate the .pyx or .pyd/.os file corresponding with the given name.
    """
    
    # Get paths to search module in
    paths1 = [p for p in sys.path]
    paths1.insert(0, '')
    
    # Search
    for path in paths1:
        fnames = getFileNames(moduleName, path) # source, bin, bin2
        if any([os.path.isfile(fname) for fname in fnames]):
            return path
    else:
        return None # Note that empty string is valid path (current directory)


def install(**kwargs):
    """ install(**kwargs)
    
    Install the Cython importer. Call this every time before importing
    a Cython module. The code is recompiled if necessary.
    
    For simple code, one just needs to call install(). For more advanced
    code, use the keyword arguments to specify language, include dirs etc.
    This makes setup scripts unnecessary in many cases.
    
    Keyword arguments
    -----------------
    compiler : {'gcc', 'native'}
        On Windows, use this to specify the compiler. Default gcc.
    language : {'c', 'c++'}
        Language to compile the Cython code to. Default c.
    include_dirs : list
        List of directories to find header files. The list is extended with
        numpy header files.
    library_dirs : list
        List of directories to find libraries.
    libraries : list
        Names of libraries to link to.
    extra_compile_args : list
        Extra compile arguments. '-O2' is added by default, and when using
        gcc, some flags to distinguish 32bit/64bit code.
    extra_link_args : list
        Extra link arguments. When using gcc, some flags to distinguish 
        32bit/64bit code.
    
    """
    
    # NOTE: The kwargs are passed to all stages of the compile tree. 
    # Every function can pick from it what it needs.
    
    # Never try to compile if we are in a frozen app
    if paths.is_frozen():
        return
    
    # Prevent double installation -> uninstall any current importers
    for importer in [i for i in sys.meta_path]:
        if isinstance(importer, Importer):
            importer.uninstall()
    
    # Install new importer
    sys.meta_path.insert(0, Importer(kwargs))


class Importer(object):
    """ Importer
    
    Is registered at sys.meta_path when calling install().
    It will try to find a cython module and return a Loader object
    for it.
    
    """
    
    def __init__(self, user_kwargs):
        self._user_kwargs = user_kwargs
    
    
    def uninstall(self):
        """ Remove all Importer instances from sys.meta_path.
        """
        # Collect instances of this class at sys.meta_path
        importersToRemove = []
        for importer in sys.meta_path:
            if isinstance(importer, Importer):
                importersToRemove.append(importer)
        
        # Remove these
        for importer in importersToRemove:
            try:
                sys.meta_path.remove(importer)
            except Exception:
                pass
    
    
    def find_module(self, fullname, packagePath=None):
        """ The method to implement to be a real Importer.
        Try finding the module (if nor already imported) and uninstall.
        """
        # Check if we can exit early
        if fullname in sys.modules:
            return None
        if fullname.startswith('Cython.'):
            return None
        
        # print('Finding module', fullname, packagePath)
        
        # Uninstall now
        self.uninstall()
        
        # Find the module. On Python 2.7 the underscore may be removed from
        # a module name. I have no idea why they do that, but this fixes it.
        for fullname2 in [fullname, fullname+'_']:
            res = self._find_module(fullname2, packagePath)
            if res:
                return res
                
    
    def _find_module(self, fullname, packagePath=None):
        """ Try to find the module. If found, return Loader instance.
        """
        
        # Init
        moduleName = fullname.split('.')[-1]
        path = None
        
        # Get path where the module is located
        if packagePath:
            fnames = getFileNames(moduleName, packagePath[0]) # source, bin, bin2
            if any([os.path.isfile(fname) for fname in fnames]):
                path = packagePath[0]
        else:
            path = locate_cython_module(moduleName)
        
        # Success?
        if path is None:
            return None
        else:
            path = os.path.abspath(path)
            return Loader(fullname, moduleName, path, self._user_kwargs)


class Loader(object):
    """ Loader
    
    When a Cython module is found, an instance of this class is created.
    It is used to import the module using the filename that was mangled
    using the Python version. But first, the module is (re)compiled
    if necessary.
    
    """
    
    def __init__(self, fullname, moduleName, path, user_kwargs):
        self._fullname = fullname
        self._moduleName = moduleName
        self._path = path
        self._user_kwargs = user_kwargs
    
    
    def load_module(self, fullname):
        """ This is the method that we should implement to be a real Loader.
        It gets the binary to load (which may involve some compiling) and
        then loads it.
        """
        
        # Test
        if not (self._fullname == fullname or self._fullname == fullname+'_'):
            raise RuntimeError("invalid module, expected %s, got %s" % 
                                        (self._fullname, fullname) )
        
        # Prepare GCC. Also if not compiling, because it may need gcc libs
        prepare_gcc()
        
        # Import module
        moduleNameToLoad = self.get_binary_to_load(self._fullname)
        return imp.load_dynamic(self._fullname, moduleNameToLoad)
    
    
    def get_binary_to_load(self, fullname):
        """ Get the binary to load. We might have to (re)create it.
        
        We have a source file sourceName. From that, we compile a binary
        called binName2, which has its name mangled with the Python version.
        This binary is copied for freezing (and normal import) compatibility
        to binName.
        
        Step 1: compile binName2  (if binName2 out of date)
        Step 2: copy binName2 to binName  (if not currently the same file)
        Step 3: return binName2 (prefered) or binName.
        
        Different things can happen:
          * If step 1 fails raise error or show a warning (stuff might still work)
          * If step 2 fails we will show a warning (freezing will not work)
          * If step 3 fails it is an error (we can check after step 1)
        
        """
        
        # Get names 
        sourceName, binName, binName2 = getFileNames(self._moduleName, self._path)
        
        # Get modification times of these files.
        sourceTime, binTime, binTime2 = getFileModificationTimes(
                                                sourceName, binName, binName2)
       
        # Step 1: create binary (compile and copy), update times
        if sourceTime > binTime2:
            self.create_binary(sourceName, binName, binName2)
            sourceTime, binTime, binTime2 = getFileModificationTimes(
                                                sourceName, binName, binName2)
        
        # Test if ok. Compiling may have failed, but if we have the binaries
        # it will still work
        if not (binTime or binTime2):
            raise RuntimeError("No binary available for Cython module %s." %
                                    self._moduleName )
        
        # Step 2: copy binName2 to binName
        # Copy the special name to a file that has the name of the module
        # (binName). This is what cx_freeze will detect and collect.
        # This action is done every time so that the binary is up to date
        # with the latest Python version with which the module was imported.
        if binTime2 and (binTime == 0 or binTime2 != binTime):
            try:
                shutil.copy2(binName2, binName)
                print('Copied %s to match with current Python version.' % binName)
            except Exception:
                print('Could not copy %s to match it with the current Python '+
                    'version, therefore not ready for freezing.' % binName)
        
        # Step 3: return name of binary to import
        # Prefer the one with the mangled name. In this way, we do not lock
        # the binary with the moduleName, so it can be overwritten (updated).
        # Note that above we already check if either binary exists.
        if binTime2:
            return binName2 # ok
        else:
            return binName # not so good, a warning should have been shown
    
    
    def create_binary(self, sourceName, binName, binName2):
        """ Creates the binary. This is just a small wrapper around the
        function that compiles the Cython code. Here we also copy
        the resulting library to the right location and clean up the
        build dir.
        """
        
        # Init
        build_dir = 'build_py%i%i_%i' % (sys.version_info[0], sys.version_info[1], NBITS)
        base_dir, name = os.path.split(binName)
        binName3 = os.path.join(base_dir, build_dir, name)
        if not os.path.isdir(os.path.dirname(binName3)):
            os.makedirs(os.path.dirname(binName3))
        
        try:
            # Try to compile
            compile_error = self.compile_cython(sourceName, build_dir)
            # Try to copy the file
            if not os.path.isfile(binName3):
                try:
                    import sysconfig
                    abitag = sysconfig.get_config_var('SOABI')
                    binName3 = binName3.replace('.so', '.'+abitag+'.so')
                except Exception:
                    pass
                if not os.path.isfile(binName3):
                    print(compile_error)
                    raise RuntimeError('Could not find %s, was it not compiled?' % binName3)
            if not compile_error:
                try:
                    shutil.copy2(binName3, binName2)
                except Exception:
                    print(compile_error)
                    raise RuntimeError('Could not write %s, is a process holding it?' % binName2)
        finally:
            self.cleanup(os.path.join(base_dir, build_dir))
        
        # Make sure its a string
        compile_error = compile_error or ''
        
        # Decide if we can proceed: either binary should be available
        binExists, binExists2 = os.path.isfile(binName), os.path.isfile(binName2)
        if binExists or binExists2:
            if compile_error:
                print(compile_error)
        else:
            raise RuntimeError("No binary available for Cython module %s. %s" %
                                        (self._moduleName, compile_error) )
    
    
    def compile_cython(self, sourceName, build_dir='cython_build'):
        """ compile_cython(sourceName, **kwargs)
        
        Do the actual compiling. Raises an error if there is a critical 
        problem. Or returns an error string if compiling fails but
        things might still work (e.g. Cython is not installed but user
        has the binaries).
        
        """
        
        # Get extension args given during install()
        user_kwargs = self._user_kwargs
        
        # Get compiler
        # todo: Explicitly use selected compiler downstream
        compiler = user_kwargs.get('compiler', 'gcc').lower()
        if compiler not in ['gcc', 'mingw', 'native']:
            raise RuntimeError('Unkown compiler %s.' % compiler)
        if compiler in ['mingw']:
            compiler = 'gcc'
        
        
        # Try importing Cython, if not available, return gracefully
        try:
            from Cython.Distutils import build_ext as build_pyx
        except ImportError:
            return "Could not compile: require Cython (www.cython.org)."
        
        # Store interpreter state
        old_argv = sys.argv
        old_dir = os.getcwd()
        
        # Prepare state for distutils
        sys.argv = [sourceName] # Is like the script that was "called"
        sys.argv.append('build_ext')
        #sys.argv.append('--inplace')
        sys.argv.append('--build-lib=%s'%build_dir)
        sys.argv.append('--build-temp=%s'%build_dir)
        if sys.platform.startswith('win') and compiler=='gcc':
            # Force using mingw (is gcc compiler fow Windows)
            sys.argv.append('-cmingw32') 
            if 'DISTUTILS_USE_SDK' in os.environ:
                del os.environ['DISTUTILS_USE_SDK']
        
        # Goto the right directory
        os.chdir(os.path.dirname(sourceName))
        
        # Get modulename
        modNamePlus = os.path.split(sourceName)[1]
        modName = os.path.splitext(modNamePlus)[0]
        
        # Set language
        language = user_kwargs.get('language', 'c')
        
        # Init extension args     
        include_dirs = ['.'] + user_kwargs.get('include_dirs',[])
        library_dirs = ['.'] + user_kwargs.get('library_dirs',[])
        libraries = [] + user_kwargs.get('libraries',[])
        extra_compile_args = ['-O2'] + user_kwargs.get('extra_compile_args',[])
        extra_link_args = [] + user_kwargs.get('extra_link_args',[])
        
        # Set number of bits
        # Includes fix for http://bugs.python.org/issue4709
        # See also http://projects.scipy.org/numpy/wiki/MicrosoftToolchainSupport
        if compiler=='gcc':
            for L in [extra_compile_args, extra_link_args]:
                L.append('-m%i' % NBITS)
                L.extend(['-static-libgcc', '-static-libstdc++']) # At least on Windows, wont hurt in Linux either I think
                if sys.platform.startswith('win'):
                    L.append('-DMS_WIN%i' % NBITS) # Means "#define MS_WINxx"
                    
        
        # Try compiling
        try:
            
            # Imports
            from distutils.core import setup
            from distutils.extension import Extension
            from numpy.distutils.misc_util import get_numpy_include_dirs
            
            # Get numpy headers
            include_dirs.extend(get_numpy_include_dirs())
            
#             # Extra libs (for msvcr90.dll for exampe)            
#             if sys.platform.startswith('win') and paths.pyzo_lib_dir():
#                 library_dirs.append(str(paths.pyzo_lib_dir()))
            
            # Extra extension kwargs?
            extension_kwargs = user_kwargs.get('extension_kwargs',{})
            
            # Create extension module object
            ext1 = Extension(modName, [modNamePlus], 
                                language=language,
                                include_dirs=include_dirs,
                                library_dirs=library_dirs,
                                libraries=libraries,
                                extra_compile_args=extra_compile_args,
                                extra_link_args=extra_link_args,
                                **extension_kwargs
                                )
            
            # Compile
            ext_modules = [ext1]
            setup(
                cmdclass = {'build_ext': build_pyx},
                ext_modules = ext_modules,
            )
        
        except BaseException as err: # also catch system exit
            #msg = traceback.format_exception_only(*sys.exc_info()[:2])
            #raise RuntimeError("Building module %s failed: %s" % (modName, msg))
            print("Building module %s failed: " % modName)
            raise
        else:
            print('Successfully compiled cython file: %s' % modName)
        finally:
            # Put back the state
            sys.argv = old_argv
            os.chdir(old_dir)
    
    
    def cleanup(self, path):
        """ Try to remove the build directory and its contents.
        """
        
        # Get directory
        if not os.path.isdir(path):
            return
        
        def _clearDir(path):
            # Remove contents
            for fname in os.listdir(path):
                fname = (os.path.join(path, fname))
                if os.path.isdir(fname):
                    _clearDir(fname)
                elif os.path.isfile(fname):
                    try:
                        os.remove(fname)
                    except Exception:
                        pass
            # Remove dir itself
            try:
                os.rmdir(path)
            except Exception:
                pass
        
        # Clean
        _clearDir(path)
        if os.path.isdir(path):
            print('Could not remove build directory.')
