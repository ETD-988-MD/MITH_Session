-------------
Release notes
-------------

Version 1.1 (04-02-2015)
========================

Imageio is now a dependency of `Moviepy <https://github.com/Zulko/moviepy/>`_, 
which exposed a few issues to fix. Imageio is now also available as a
Debian package (thanks Ghislain!). Furher, we tweaked our function names
to be cleared and more consistent (the old names still work).

* All ``Xsave()`` functions are renamed to ``Xwrite()``. 
  Also ``read()`` and ``save()`` are now ``get_reader()`` and ``get_writer()``.
  The old names are available as aliases (and will be for the foreseable
  future) for backward compatibility.
* Protect user from bringing computer in swap-mode by doing e.g.
  ``mimread('hunger games.avi')``.
* Continuous integration for Windows via Appveyor.
* All imports are relative, so imageio can be used as a subpackage in
  a larger project.
* FFMPEG is the default plugin for reading video (since AVBIN has issues).
* Better handling on NaN and Inf when converting to uint8.
* Provide dist packages that include freeimage lib and a few example images.
* Several changes to ease building into Debian package.
* Fixed segfault when saving gif 
  (thanks levskaya, https://github.com/imageio/imageio/pull/53).
* Don't fail when userdir is not writable.
* Gif plugin writer has fps param for consistency with avi/mp4 etc.


Version 1.0 (13-11-2014)
========================

In this release we did a lot of work to push imageio to a new level.
The code is now properly tested, and we have several more formats.

The big changes:

* Many unit tests were written to cover over 95% of the code base.
  (the core of imageio has 100% coverage).
* Setup continuous integration (CI) using Travis.
* Imageio now follows PEP8 style guides (and this is tested with CI).
* Refactoring of the code base. Resulting in a cleaner namespace.
* Many improvements to the documementation.

Plugins:

* The FFMPEG format is now well supported. Binaries are provided.
* New AVBIN format for more efficient reading of video files.
* New NPZ format that can store (a series of) arbitrarily shaped numpy arrays.
* New SWF format (shockwave flash) for lossless animated images.
* Improvements to the GIF format. The GIF and ANIGIF formats are now merged.

Further:

* New simple website to act as a front page (http://imageio.github.io).
* Compatibility with Pypy.
* We provide a range of :doc:`standard images <standardimages>` that are 
  automatically downloaded.
* Binaries (libs and executables) that plugins of imageio uses are now
  downloaded at runtime, not at build/install time. This simplifies
  things a lot.
* freeimage plugin now fully functional on pypy
* Added utilities for developers (run ``python make`` from the repo root).
* PNG, JPEG, BMP,GIF and other plugins can now handle float data (pixel
  values are assumed to be between 0 and 1.
* Imageio now expand the user dir when filename start with '~/'.
* Many improvements and fixes overall.


Version 0.5.1 (23-06-2014)
==========================

* DICOM reader closes file after reading pixel data 
  (avoid too-many-open-files error)
* Support for video data (import and export) via ffmpeg
* Read images from usb camera via ffmpeg (experimental)


Version 0.4.1 (26-10-2013)
==========================

* We moved to github!
* Raise error if URI could not be understood.
* Small improvement for better error reporting.
* FIxes in mvolread and DICOM plugin


Version 0.4 (27-03-2013)
========================

Some more thorough testing resulted in several fixes and improvements over
the last release.

* Fixes to reading of meta data in freeimage plugin which could
  cause errors when reading a file.
* Support for reading 4 bpp images.
* The color table for index images is now applied to yield an RGBA image.
* Basic support for Pypy.
* Better __repr__ for the Image class.


Version 0.3.2
=============

* Fix in dicom reader (RescaleSlope and RescaleIntercept were not found)
* Fixed that progress indicator made things slow


Version 0.3.1
=============

* Fix installation/distribution issue.


Version 0.3.0
=============

This was a long haul. Implemented several plugins for animation and
volumetric data to give an idea of what sort of API's work and which 
do not. 

* Refactored for more conventional package layout 
  (but importing without installing still supported)
* Put Reader and Writer classes in the namespace of the format. This
  makes a format a unified whole, and gets rid of the
  _get_reader_class and _get_write_class methods (at the cost of
  some extra indentation).
* Refactored Reader and Writer classes to come up with a better API
  for both users as plugins.
* The Request class acts as a smart bridging object. Therefore all
  plugins can now read from a zipfile, http/ftp, and bytes. And they
  don't have to do a thing.
* Implemented specific BMP, JPEG, PNG, GIF, ICON formats.
* Implemented animated gif plugin (based on freeimage).
* Implemented standalone DICOM plugin.


Version 0.2.3
=============

* Fixed issue 2 (fail at instal, introduced when implementing freezing)


Version 0.2.2
=============

* Improved documentation.
* Worked on distribution.
* Freezing should work now.


Version 0.2.1
=============

* Introduction of the imageio.help function.
* Wrote a lot of documentation.
* Added example (dummy) plugin.


Version 0.2
===========

* New plugin system implemented after discussions in group.
* Access to format information.


Version 0.1
===========

* First version with a preliminary plugin system.
