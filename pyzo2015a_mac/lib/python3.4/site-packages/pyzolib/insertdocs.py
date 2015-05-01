# -*- coding: utf-8 -*-
# Copyright (C) 2012 Almar Klein
# This module is distributed under the terms of the (new) BSD License.

""" insertdocs.py

Module to insert documentation from docstrings in RST files, which can 
then be used by Sphinx to generate beautiful html or pdf documentation.

Sphinx has a very nice autodoc extension, but that approach has shortcomings:
  * The sphinx that is used to create the docs must be able to import 
    all modules that you want to use docstrings of.
  * This is specifically a problem when using for instance readthedocs.org.

The approach advocated by this module is to insert the docstrings in the
.rst files before building the documentation. This has the advantage that
the subsequent build process can be done by about any RST builder; you
only need the doc directory with the .rst files to build the docs.


How to use
----------

Step 1: in the .rst documentation files, you use the directive 
``.. insertdocs:: objectName`` to specify that a certain object should
be documented there. insertdocs can document modules, classes, functions
(and their members).

Step 2: before building, run the parse_rst_files function that is defined
in this module. It will inject all the docstrings and also automatically
make references for the object names it knows.

Notes: when the docstrings are inserted, the directives are replaced by
comments: ``.. insertdocs start::`` another comment is placed at the end
of the inserted text: ``.. insertdocs end::``. To remove the inserted 
docs for easier editing, use the clear_rst_files function.


Options
-------
insertdocs tries to be a bit compatible with Sphynx's autodoc. In currently
supports the ``:members:`` and the ``:inherited-members:`` options. 

Note than when the docs are inserted the options look like: 
``.. insertdocs :members:``.


Example script (Windows)
------------------------
# docsinserter.py - put this next to conf.py

# Imports to fill the global namespace
import yoton

# Insert docs
from pyzolib import insertdocs
insertdocs.parse_rst_files(globals(), '.')

# Tell Sphinx to build the docs
import subprocess
# p = subprocess.check_call(['make.bat', 'html'])

"""

import os
import sys
import re

# Version dependent defs
V2 = sys.version_info[0] == 2
if V2:
    D = __builtins__
    if not isinstance(D, dict):
        D = D.__dict__
    bytes = D['str']
    str = D['unicode']
    basestring = basestring
else:
    basestring = str  # to check if instance is string
    bytes, str = bytes, str


DIRECTIVES_AUTO = ['.. autoclass::', '.. autofunction::', '.. automodule::']
DIRECTIVE_BASE = '.. insertdocs::'
DIRECTIVE_START = '.. insertdocs start::' # is really a comment
DIRECTIVE_END = '.. insertdocs end::' # is really a comment
PREFIX_OPTION = '.. insertdocs '

# todo: options for directive (members)

## Functions to parse the files


def clear_rst_files(path='.'):
    """ clear_rst_files(path='.')
    
    Remove the inserted docstrings from the documentation and put the
    insertdocs directives. Also removes any auto-generated references.
    
    """
    return parse_rst_files(None, path, True)


def parse_rst_files(NS, path='.', clear=False):
    """ parse_rst_files(NS, path='.')
    
    Parse all RST files in the given directory and insert the docstrings
    where the insertdocs directive has been placed. Also automatically
    creates references to objects that are known.
    
    """
    
    printPrefix = ['Inserted ', 'Cleared'][clear]
    
    # Get list of files
    path = os.path.abspath(path)
    files = []
    for fname in os.listdir(path):
        if fname.endswith('.rst'):
            files.append(fname)
    
    # Insert docstrings
    changedCount = 0
    knownNames = []
    for fname in files:
        # Get text and parse the docs
        fname2 = os.path.join(path, fname)
        text = open(fname2, 'rb').read().decode('utf-8')
        text, changed, names = _parse_rst_file_docs(text, NS, clear)
        knownNames.extend(names)
        
        # If it was modified, save the file.
        if changed:
            changedCount += 1
            print(printPrefix + 'docstrings in %s' % fname)
            f = open(fname2, 'wb')
            f.write(text.encode('utf-8'))
            f.close()
    
    # Message done
    print(printPrefix + 'docstrings in %i/%i files.' % (changedCount, len(files)))
    
    # Clear?
    if clear:
        knownNames = []
    
    # Handle cross-refences
    changedCount = 0
    for fname in files:
        # Get text and parse the references
        fname2 = os.path.join(path, fname)
        text = open(fname2, 'rb').read().decode('utf-8')
        text, changed = _parse_rst_file_refs(text, knownNames)
        
        # If it was modified, save the file.
        if changed:
            changedCount += 1
            print(printPrefix + 'auto-refs in %s' % fname)
            f = open(fname2, 'wb')
            f.write(text.encode('utf-8'))
            f.close()
    
     # Message done
    print(printPrefix + 'auto-references in %i/%i files.' % (changedCount, len(files)))


class LineByLine:
    """ Class to walk over the lines looking for our derective and changing
    the code.
    """
    
    def __init__(self, text, NS, cleanMode=False):
        
        # Store lines and init new version
        self._lines1 = [line for line in text.splitlines()]
        if text.endswith('\n') or True:
            # If endswith newline, splitlines has popped one,
            # otherwise, make it end with a newline!
            self._lines1.append('')
        
        # Current index, 
        self._i = -1
        
        # New lines and flag to signal whether anything has changed
        self._lines2 = []
        self._changed = False
        
        # Namespace to look for docstrings
        self._NS = NS
        
        # Whether to clean up (default is False)
        self._cleanMode = cleanMode
        
        # To store a "piece"
        self._objectName = None
        self._options = {}
        
        # List of known names
        self._knownNames = []
    
    
    def get(self):
        line = self.pop()
        self._lines2.append(line)
        return line
    
    def pop(self):
        self._i += 1
        
        # Get line or raise stop
        try:
            line = self._lines1[self._i]
        except IndexError:
            raise StopIteration
        
        # Return (do not add line)
        return line
    
    def set(self, line):
        if self._changed or line != self._lines2[-1]:
            self._lines2[-1] = line
            self._changed = True
    
    def append(self, line):
        self._lines2.append(line)
        self._changed = True
    
    
    def add_option(self, name, value):
        name = name.replace('-', '_')
        if not value:
            value = True
        self._options[name] = value
        
    
    def search_start(self):
        """ Search for the start. If found, search for options.
        Then search for end if necessary, then insert text.
        """
        
        # Prepare
        self._objectName = None
        self._options = {}
        
        while True:
            line = self.get()
            
            if line.startswith(DIRECTIVE_BASE):
                search_for_end = False
                break
            elif line.startswith(DIRECTIVE_START):
                search_for_end = True
                break
        
        # Store object name
        self._objectName = line.split('::',1)[1].strip()
        
        # Change syntax to how we want it
        if self._cleanMode:
            self.set(DIRECTIVE_BASE + ' ' + self._objectName)
        else:
            self.set(DIRECTIVE_START + ' ' + self._objectName)
        
        # Next step, search options
        self.search_options()
        
        # Search for end if we need to
        if search_for_end:
            self.search_end()
        
        # Insert text if we need to
        if not self._cleanMode:
            self.insert_text()
        
        # Done
        return self._objectName
    
    
    def search_options(self):
        """ Process lines until we have one that is not an option.
        """
        while True:
            line = self.get()
            
            # Detect options
            m1 = re.search(r'^\s+?:(.+?):', line)
            m2 = re.search(r'^.. insertdocs\s+?:(.+?):', line)
            m = m1 or m2
            
            if m is not None:
                # Option found
                optionName = m.group(1)
                optionValue = line[m.end():].strip()
                self.add_option(optionName, optionValue)
                # Change syntax to how we need it
                if self._cleanMode:
                    self.set('   :%s: %s' % (optionName, optionValue))
                else:
                    self.set('.. insertdocs :%s: %s' % (optionName, optionValue))
            else:
                # No more options
                break
    
    
    def insert_text(self):
        """ Insert text generated from docstrings. 
        Then search for the end.
        """
        
        # Get text to insert
        extraText = ''
        if self._NS is not None:
            extraText = get_docs(self._objectName, NS=self._NS, **self._options)
        # Insert it
        if extraText:
            self._knownNames.append(self._objectName)
            self.append('')
            for extraline in extraText.splitlines():
                self.append(extraline)
        # Always insert end
        self.append(DIRECTIVE_END)
        self.append('') # extra blanc line
    
    
    def search_end(self):
        """ Keep getting lines until we reach the end.
        """
        
        while True:
            line = self.pop()
            
            if line.startswith(DIRECTIVE_END):
                self.pop() # pop one extra, because we added an extra blanc line
                break


def _parse_rst_file_docs(allText, NS=None, clean=False):
    
    # Instantiate lines object
    lines = LineByLine(allText, NS, clean)
    
    # Let it process until we are out of lines
    count = 0
    knownNames = []
    try:
        while True:
            objectName = lines.search_start() # Returns if a "piece" is processed
            count += 1
            knownNames.append(objectName)
    except StopIteration:
        pass
    
    # Done (if changed, rebould text from all the lines)
    if lines._changed:
        allText = '\n'.join(lines._lines2)
    return allText, lines._changed, knownNames


def _parse_rst_file_refs(allText, knownNames):
    
    # Remove all insertdocs :ref: instances
    r = re.compile(':ref:`(.+?)<insertdocs-(.+?)>`')
    allText, n1 = r.subn(r'\1', allText)
    
    # Check all lines
    lines1 = []
    lines2 = []
    nChanged = 0
    for line in allText.splitlines():
        lines1.append(line)
        # No refs in headings
#         if line.startswith('===') or line.startswith('---') or line.startswith('^^^'):
#             if lines2:
#                 lines2[-1] = lines1[-2]
#             lines2.append(line)
#             continue
        # No refs in directives or comments
        if line.startswith('..'):
            lines2.append(line)
            continue
        # Try!
        for name in knownNames:
            i0 = 0
            while i0 >= 0:
                i0 = line.find(name, i0)
                if i0 < 0:
                    break
                # Found something
                i1 = i0 + len(name)
                pre, post = line[:i0], line[i1:]
                nquotes = pre.count('``')
                # Not in a quote?
                if nquotes%2 == 1:
                    i0 = i1
                    continue
                # Check if ending is ok
                endingok= True
                for ending in [' ', ',', ':', ';', '. ']: # no braces: `( will format wrong by sphinx!
                    if post.startswith(ending): break
                else: endingok = False
                # If all is well... modify line
                if endingok or not post or post=='.':
                    nChanged += 1
                    line = pre + make_xref(name) + post
                    i1 += 4
                # Next!
                i0 = i1
        else:
            lines2.append(line)
    
    # Done
    if nChanged:
        # Add newline (splitlines removes one if there is at least one)
        lines2.append('') 
        allText = '\n'.join(lines2)
    return allText, (n1+nChanged) > 0


## Functions to get the RST docs for an object


def get_docs(objectName, NS, **kwargs):
    """ get_docs(objectName, NS, **kwargs)
    
    Get the docs for the given string, class, function, or list with 
    any of the above items.
    
    """
    
    # Make object
    try:
        object = eval(objectName, {}, NS)
    except Exception:
        print('Warning: do not know object "%s".' % objectName)
        return ''
    
    if isinstance(object, basestring):
        return smart_format(object, **kwargs)
    elif isinstance(object, list):
        tmp = [get_docs(ob, NS, **kwargs) for ob in object]
        return '\n\n'.join(tmp)
    elif isclass(object):
        return get_class_docs(object, objectName, **kwargs)
    elif 'function' in str(type(object)):
        return get_function_docs(object, objectName, **kwargs)
    elif 'method' in str(type(object)):
        return get_function_docs(object, objectName, **kwargs)
    elif 'module' in str(type(object)):
        return get_module_docs(object, objectName, **kwargs)
    else:
        print('Cannot determine how to generate docs from object "%s".' % objectName)


def get_property_docs(prop, fullName, **kwargs):
    """ get_property_docs(prop, fullName)
    
    Get RST content for the specified property. Makes a "header" from
    the property name (with a label) and indents the body of
    the documentation.
    
    (Need the name, since we cannot obtain it from the 
    property object. )
    """
    
    # Get docs
    header, docs = split_docs (prop, fullName)
    
    # Return with markup
    result = '%s\n\n' % make_label(fullName)
    result += '.. py:attribute:: %s\n\n' % header
    result += indent(docs, 2)
    return result

    
def get_function_docs(fun, fullName=None, isMethod=False, **kwargs):
    """ get_function_docs(fun, fullName=None, isMethod=False, **kwargs)
    
    Get RST content for the specified function or method. Makes 
    a "header" from the property name (with a label) and indents 
    the body of the documentation.
    """
    
    # Get docs
    if fullName is None:
        fullName = fun.__name__
    header, docs = split_docs(fun, fullName)
    
    # Return with markup
    result = '%s\n\n' % make_label(fullName)
    if isMethod:
        result += '.. py:method:: %s\n\n' % header
    else:
        result += '.. py:function:: %s\n\n' % header
    result += indent(docs, 2)
    return result


def get_class_docs(cls, fullName='', members=None, inherited_members=None, **kwargs):
    """ get_class_docs(cls, fullName='', inherited_members=False)
    
    Get RST content for the specified class. Writes the formatted
    docstring of the class, lists all methods and properties and
    gives the docs for all methods and properties (as given by 
    get_function_docs() and get_property_docs()).
    
    If inherited_members is True, also include inherited properties
    and methods. 
    
    """
    
    # Get name
    if not fullName:
        fullName = get_class_name(cls)
    
    # Init the variable to hold the docs
    total_docs = ''
    
    # Produce label and title
    total_docs += '%s\n\n' % make_label(fullName)
    header, docs = split_docs(cls, fullName)
    total_docs += '.. py:class:: %s\n\n' % header
    #total_docs += '%s\n%s\n\n' % (header, '^'*len(fullName))
    
    # Show inheritance
    bases = []
    for base in cls.__bases__:
        tmp = get_class_name(base)
        # todo: auto-crossref
        bases.append( tmp )
    total_docs += '  *Inherits from %s*\n\n' % ', '.join(bases)
    
    # Insert docs itself (add indentation)
    total_docs += indent(docs, 2) + '\n\n'
    
    # Stop here?
    if not members:
        return total_docs
    elif isinstance(members, str):
        memberSelection = [m.strip() for m in members.split(',')]
    else:
        memberSelection = None
    
    
    # containers for attributes
    methods = {}
    properties = {}
    
    # Collect attributes
    atts = {}
    def collect_attributes(cls):
        for att, val in cls.__dict__.items():
            atts[att] = val
        if inherited_members:
            for c in cls.__bases__:
                collect_attributes(c)
    collect_attributes(cls)
    
    # Collect docs for methods and properties
    for att in atts.keys():
        if att.startswith('_'):
            continue
        if memberSelection and att not in memberSelection:
            continue
        
        # Get value
        val = atts[att]
        
        # Skip if attribute does not have a docstring
        if not val.__doc__:
            print('Skipping %s.%s: no docstring' % (fullName, att))
            continue
        
        # Get info
        if 'function' in str(type(val)):
            methods[att] = get_function_docs(val, fullName+'.'+att, isMethod=True)
        elif 'property' in str(type(val)):
            properties[att] = get_property_docs(val, fullName + '.' + att)
    
    
    
    # todo: if class summary: need table
#     # Insert summary of properties with links
#     if properties:
#         propList = []
#         for key in sorted( properties.keys() ):
#             propList.append( '[#%s %s]' % (key, key) )
#         tmp = '*The %s class implements the following properties:*\n'
#         total_docs += tmp % fullName
#         #propList = ['  * '+m for m in propList]
#         #total_docs += '\n'.join(propList) + '\n\n'
#         total_docs += create_table_from_list(propList) + '\n'
#     
#     # Insert summary of methods with links
#     if methods:
#         method_list = []
#         for key in sorted( methods.keys() ):
#             method_list.append( '[#%s %s]' % (key, key) )
#         tmp = '*The %s class implements the following methods:*<br/>\n'
#         total_docs += tmp % fullName
#         #method_list = ['  * '+m for m in method_list]
#         #total_docs += '\n'.join(method_list) + '\n\n'
#         total_docs += create_table_from_list(method_list) + '\n'
    
    # Insert properties
    if properties:
        total_docs += '  *PROPERTIES*\n\n'
        for key in sorted( properties.keys() ):
            total_docs += indent(properties[key],2) + '\n\n'
    
    # Insert methods
    if methods:
        total_docs += '  *METHODS*\n\n'
        for key in sorted( methods.keys() ):
            total_docs += indent(methods[key], 2) + '\n\n'
    
    # Done
    total_docs += '\n\n'
    return total_docs


def get_module_docs(module, fullName='', members=None, **kwargs):
    """ get_module_docs(module, fullName='')
    
    Get RST documentation for a module.
    
    """
    
    # Get name
    if not fullName:
        fullName = get_class_name(cls)
    
    # Get our docs
    header, docs = split_docs(module, fullName)
    
    # Produce label and title
    total_docs = ''
    total_docs += '%s\n\n' % make_label(fullName)
    total_docs += '.. py:module:: %s\n\n' % header
    #total_docs += 'Module %s\n%s\n\n' % ( header, '='*((len(header)+30)) )
    # -> User should use :mod:`modulename` -- description in the rst file
    
    # Insert our own docs
    total_docs += docs + '\n\n'
    
    # Stop here?
    if not members:
        return total_docs
    elif isinstance(members, str):
        memberSelection = [m.strip() for m in members.split(',')]
    else:
        memberSelection = None
    
    
    # Collect children
    classes, functions = {}, {}
    
    # Collect docs for classes and functions
    for att in dir(module):
        if att.startswith('_'):
            continue
        if memberSelection and att not in memberSelection:
            continue
        
        # Get value, 
        val = getattr(module, att)
        
        # Skip if not defined in module
        if not hasattr(val, '__module__'):
            continue
        if val.__module__.split('.')[-1] != fullName.split('.')[-1]:
            continue
        
        # Skip if attribute does not have a docstring
        if not val.__doc__:
            print('Skipping %s.%s: no docstring' % (fullName, att))
            continue
        
        # Get info
        if isclass(val):
            classes[att] = get_class_docs(val, fullName+'.'+att)
        elif 'function' in str(type(val)):
            functions[att] = get_function_docs(val, fullName+'.'+att)
    
    
    # Insert functions
    if functions:
        total_docs += 'Functions\n----------\n\n'
        for key in sorted( functions.keys() ):
            total_docs += functions[key] + '\n\n'
    
    # Insert methods
    if classes:
        total_docs += 'Classes\n----------\n\n'
        for key in sorted( classes.keys() ):
            total_docs += classes[key] + '\n\n'
    
    total_docs += '\n\n'
    return total_docs

    
## Functions to parse the docstrings to RST


def smart_format(text):
    """ smart_format(text)
    
    Smart formats text -> changing headers to bold text, handling
    code examples, etc.
    
    This is where most of the smarty (and hard-to-maintain) bits are.
    
    """
    class Line:
        def __init__(self, text):
            self.text = text
            self.sText = text.lstrip()
            self.indent = len(self.text) - len(self.sText)
            self.needNL = False
            self.isParameter = False
    
    # Get lines
    lines = text.splitlines()
    
    # Test minimal indentation
    minIndent = 9999
    for line in lines[1:]:
        tmp = line.lstrip()
        indent = len(line) - len(tmp)
        if tmp:
            minIndent = min(minIndent, indent)
    
    # Remove minimal indentation
    lines2 = [ Line(lines[0].lstrip()) ]
    for line in lines[1:]:            
        lines2.append( Line(line[minIndent:]) )
    
    # Prepare state variables   
    prevLine = Line('')     
    inExample = False
    inCode = False
    
    # Format line by line
    lines3 = []
    for line in lines2:
        
        # Detect special cases
        if line.indent == prevLine.indent and ( "---" in line.text or 
                                                "===" in line.text):
            underCount = line.text.count('-') + line.text.count('=')
            len1, len2 = len(line.text.strip()), len(prevLine.text.strip())
            if underCount == len1 and len2 and  len1 >= len2:
                # Header
                if True:
                    lines3[-1] = '**%s**\n' % (prevLine.sText)
                    line.text = line.sText = ''
                    line.needNL = True
                # Start example?
                inExample = False
                if prevLine.sText.lower().startswith('example'):
                    line.text = '.. code-block:: python\n'
                    inExample = True
        elif ' : ' in line.text:
            # Parameter (numpy style)
            pass
        elif line.sText[:3] in ['{{{', '}}}']:
            # Code block
            if line.sText[0] == '{':
                inCode = True
                prevline.text = prevlineline.text + '::'
            else:
                inCode = False
            line.text = ''
        elif inExample or inCode:
            line.text = '    ' + line.text
        else:
            line.text = line.text
        
        # Done with line
        prevLine = line
        lines3.append(line.text)
    
    # Done line by line formatting
    lines3.append('')
    docs = '\n'.join(lines3)
    
#     # "Pack" underscores and asterix that are not intended as markup
#     # Mark all asterixes that surround a word or bullet
#     docs = re.sub('(\s)\*(\w+)\*(\s)', '\g<1>\0\g<2>\0\g<3>', docs)
#     docs = re.sub( re.compile('^(\s+)\* ',re.MULTILINE), '\g<1>\0 ', docs)
#     # Pack all remaining asterixes
#     docs = docs.replace('*',"`*`").replace('\0','*')
#     # Do the same for underscores (but no need to look for bullets)
#     # Underscores within a word do not need esacping.
#     docs = re.sub('(\s)_(\w+)_(\s)', '\g<1>\0\g<2>\0\g<3>', docs)
#     docs = docs.replace(' _'," `_`").replace('_ ', '`_` ').replace('\0','_')
#     # Pack square brackets
#     docs = docs.replace("[[","<BRACKL>").replace("]]","<BRACKR>")
#     docs = docs.replace("[","`[`").replace("]","`]`")
#     docs = docs.replace("<BRACKL>", "[").replace("<BRACKR>", "]")
    
    return docs


def split_docs(ob, fullName):
    """ split_docs(ob, fullName)
    
    Get the docstring of the given object as a two element tuple:
    (header, body)
    
    The header contains the name and signature (if available) of the class
    or function. 
    
    Uses smart_format() internally.
    
    """
    
    # Get name and base name
    if '.' in fullName:
        tmp = fullName.rsplit('.', 1)
        baseName, name = tmp[0], tmp[1]
    else:
        baseName, name = '', fullName
    
    def searchEndBrace(text, i0):
        """ Start on opening brace. """
        i = i0
        level = int(text[i0]=='(')
        while level and (i <len(text)-1):
            i+=1
            if text[i] == '(':
                level += 1
            elif text[i] == ')':
                level -= 1
        
        if level:
            return i0+1
        else:
            return i
    
    
    # Get docs using smart_format()
    docs = smart_format(ob.__doc__)
    
    # Depending on class, analyse signature, or use a default signature.
    
    if 'module' in str(type(ob)):
        header = name
        #docs = docs
        
    elif 'function' in str(type(ob)) or  'method' in str(type(ob)):
        header = name + '()'
        
        # Is the signature in the docstring?
        if docs.startswith(name+'('):
            docs2 = docs.replace('\r','|').replace('\n','|')
            tmp = re.search(name+'(\(.*?\))', docs2)
            if True:
                i = searchEndBrace(docs, len(name)) + 1
                header = docs2[:i].replace('|', '') 
                docs = docs[i:].lstrip(':').lstrip()
            elif tmp:
                header = name + tmp.group(1)
                docs = docs[len(header):].lstrip(':').lstrip()
                #header = header.replace('*','`*`').replace('|','')
                header = header.replace('|','')
    
    elif 'property' in str(type(ob)): 
        header = name
        
        # Is the "signature in the header?
        if docs.startswith(name):
            header, sep, docs = docs.partition('\n')
    
    elif isclass(ob): 
        header = name
        
        # Is the signature in the docstring?
        if docs.startswith(name+'('):
            docs2 = docs.replace('\r','|').replace('\n','|')
            tmp = re.search(name+'(\(.*?\))', docs2)
            if True:
                i = searchEndBrace(docs, len(name)) + 1
                header = docs2[:i].replace('|', '') 
                docs = docs[i:].lstrip(':').lstrip()
            elif tmp:
                header = name + tmp.group(1)
                docs = docs[len(header):].lstrip(':').lstrip()
                #header = header.replace('*','`*`').replace('|','')
                header = header.replace('|','')
        elif docs.startswith(name):
            header, sep, docs = docs.partition('\n')
    
    # Remove extra spaces from header
    for i in range(10):
        header = header.replace('  ',' ')
    
    # Add class name to header
    if baseName:
        header = baseName + '.' + header
    
    # Done
    return header, docs


## Helper functions


def get_class_name(cls):
    """ get_class_name(cls)
    Get the name of the given type object.
    """
    name = str(cls)
    try:
        name = name.split("'")[1]
    except Exception:
        pass
    name = name.split(".")[-1]
    return name
    

def make_label(name):
    cleanname = name.replace('.', '-')
    return '.. _insertdocs-' + cleanname + ':'


def make_xref(name):
    cleanname = name.replace('.', '-')
    return ':ref:`' + name + '<insertdocs-' + cleanname + '>`'


def isclass(object):
    return isinstance(object, type) or type(object).__name__ == 'classobj'


def indent(text, n):
    lines = text.splitlines()
    for i in range(len(lines)):
        lines[i] = " "*n + lines[i]
    return '\n'.join(lines)


# def create_table_from_list(elements, columns=3):
#     """ create_table_from_list(elements, columns=3)
#     
#     Create a table from a list, consisting of a specified number
#     of columns.
#     """
#     
#     import math
#     
#     # Check how many elements in each column
#     n = len(elements)
#     tmp = n / float(columns)
#     rows = int( math.ceil(tmp) )
#     
#     # Correct rows in a smart way, so that each column has at least
#     # three items
#     ok = False  
#     while not ok:
#         cn = []
#         for i in range(columns):
#             tmp = n - rows*i
#             if tmp <= 0:
#                 tmp = 9999999999 
#             cn.append( min(rows, tmp) )
#         #print cn
#         if rows >= n:
#             ok = True
#         elif min(cn) <= 3:
#             rows += 1
#         else:
#             ok = True
#     
#     
#     # Open table
#     text = "<table cellpadding='10px'><tr>\n"
#     
#     # Insert columns
#     for col in range(columns):
#         text += '<td valign="top">\n'
#         for row in range(rows):
#             i = col*rows + row
#             if i < len(elements):
#                 text += elements[i] + '<br />'
#         text += '</td>\n'
#     
#     # Close table and return
#     text += '</tr></table>\n'
#     return text

