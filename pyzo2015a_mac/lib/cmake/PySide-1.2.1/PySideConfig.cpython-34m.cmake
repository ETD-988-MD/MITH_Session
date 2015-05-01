#  PYSIDE_INCLUDE_DIR   - Directories to include to use PySide
#  PYSIDE_LIBRARY       - Files to link against to use PySide
#  PYSIDE_PYTHONPATH    - Path to where the PySide Python module files could be found
#  PYSIDE_TYPESYSTEMS   - Type system files that should be used by other bindings extending PySide

SET(PYSIDE_INCLUDE_DIR "/Users/almar/pyzo2015a/include/PySide")
# Platform specific library names
if(MSVC)
    SET(PYSIDE_LIBRARY "/Users/almar/pyzo2015a/lib/libpyside.cpython-34m.lib")
elseif(CYGWIN)
    SET(PYSIDE_LIBRARY "/Users/almar/pyzo2015a/lib/libpyside.cpython-34m")
elseif(WIN32)
    SET(PYSIDE_LIBRARY "/Users/almar/pyzo2015a/bin/libpyside.cpython-34m.dylib")
else()
    SET(PYSIDE_LIBRARY "/Users/almar/pyzo2015a/lib/libpyside.cpython-34m.dylib")
endif()
SET(PYSIDE_PYTHONPATH "/Users/almar/pyzo2015a/lib/python3.4/site-packages")
SET(PYSIDE_TYPESYSTEMS "/Users/almar/pyzo2015a/share/PySide/typesystems")
