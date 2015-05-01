""" pyzolib.shebang.py
Fix shebangs for Pyzo distro.
"""

import os
import sys


def fix(prefix=None, exe=None, verbose=True):
    """ Try to fix the shebangs of all scripts in Pyzo's bin folder.
    
    The given prefix must be the prefix of a Pyzo distro. If not given,
    sys.prefix is used. The given exe must be the path to the Python
    interpreter to put in the shebang. If not given,
    "prefix/bin/python3" is used. Returns the number of fixed shebangs.
    
    Note that updating a package using conda will also update (and fix)
    the shebang.
    """
    
    # Init
    prefix = prefix or sys.prefix
    exe = exe or os.path.join(prefix, 'bin', 'python3')
    bin_folder = os.path.join(prefix, 'bin')
    count = 0
    
    # Check
    if sys.platform.startswith('win'):
        print('Windows has no shebangs.')
        return
    else:
        exename1, exename2 = 'pyzo', 'pyzo.app'  # .app directory on OS X
        if not (os.path.isfile(os.path.join(prefix, exename1)) or 
                os.path.exists(os.path.join(prefix, exename2))):
            raise RuntimeError('Can only fix shebangs of a Pyzo distro.')
            return
    
    # Process all files
    for fname in os.listdir(bin_folder):
        filename = os.path.join(bin_folder, fname)
        # Skip links and binaries
        if os.path.islink(filename):
            #print('SKIP %s: skip link' % fname)
            continue
        stat = os.stat(filename)
        if stat.st_size > 10*1024:
            if verbose:
                print('SKIP %s: > 10kB (probably binary)' % fname)
            continue 
        # Open the file
        try:
            text = open(filename, 'rb').read().decode('utf-8')
        except UnicodeDecodeError:
            if verbose:
                print('SKIP %s: cannot decode (probably binary)' % fname)
            continue
        lines = text.split('\n')
        line0 = lines[0]
        # Only modify if it has a python shebang
        if not (line0.startswith('#!') and 'python' in line0):
            if verbose:
                print('SKIP %s: no Python shebang to replace' % fname)
            continue
        # Replace
        line0 = '#!%s' % exe
        lines[0] = line0
        newtext = '\n'.join(lines)
        # Try writing back
        try:
            open(filename, 'wb').write(newtext.encode('utf-8'))
        except IOError:
            if verbose:
                print('SKIP: %s: cannot write (need sudo?)' % fname)
            continue
        # If we get here ... success!
        count += 1
        if verbose:
            print('FIXED %s' % fname)
    
    # Report
    if verbose:
        print('Modified %i shebangs' % count)
    return count


if __name__ == '__main__':
    fix()
