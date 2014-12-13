# Copyright (c) Twisted Matrix Laboratories.
# See http://twistedmatrix.com/trac/browser/trunk/LICENSE for details.

# This makes sure that users don't have to set up their environment
# specially in order to run these programs from bin/.

# This helper is not intended to be packaged or installed, it is only a
# developer convenience.  By the time the sd-agent is actually installed
# somewhere, the environment should already be set up properly without the
# help of this tool.

import sys
import os

path = os.path.abspath(sys.argv[0])
while os.path.dirname(path) != path:
    if os.path.exists(os.path.join(path, 'serverdensity', '__init__.py')):
        sys.path.insert(0, path)
        break
    path = os.path.dirname(path)
