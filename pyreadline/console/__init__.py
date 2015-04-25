from __future__ import print_function, unicode_literals, absolute_import

import pyreadline.site as site
in_ironpython = site.in_ironpython()


success = False
if in_ironpython:
    try:
        from .ironpython_console import *
        success = True
    except ImportError:
        raise
else:
    try:
        from .console import *
        success = True
    except ImportError:
        pass
        raise

if not success:
    raise ImportError(
            "Could not find a console implementation for your platform")
