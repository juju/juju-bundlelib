# Copyright 2015 Canonical Ltd.
# Licensed under the AGPLv3, see LICENCE file for details.

from __future__ import unicode_literals


VERSION = (0, 5, 3)


def get_version():
    """Return the Juju Bundle Lib version as a string."""
    return '.'.join(map(str, VERSION))
