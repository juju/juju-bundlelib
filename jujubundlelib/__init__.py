from __future__ import unicode_literals


VERSION = (0, 1, 0)


def get_version():
    """Return the Juju Bundle Lib version as a string."""
    return '.'.join(map(str, VERSION))
