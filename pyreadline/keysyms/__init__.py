from __future__ import print_function, unicode_literals, absolute_import

from . import winconstants
import pyreadline.site as site
in_ironpython = site.in_ironpython()


success = False
if in_ironpython:
    try:
        from .ironpython_keysyms import *
        success = True
    except ImportError as x:
        raise
else:
    try:
        from .keysyms import *
        success = True
    except ImportError as x:
        pass

if not success:
    raise ImportError("Could not import keysym for local pythonversion", x)