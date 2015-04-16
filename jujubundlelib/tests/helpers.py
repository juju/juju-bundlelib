# Copyright 2015 Canonical Ltd.
# Licensed under the AGPLv3, see LICENCE file for details.

from __future__ import unicode_literals

from contextlib import contextmanager


class ValueErrorTestsMixin(object):
    """Set up some base methods for testing functions raising ValueErrors."""

    @contextmanager
    def assert_value_error(self, error):
        """Ensure a ValueError is raised in the context block.

        Also check that the exception includes the expected error message.
        """
        with self.assertRaises(ValueError) as context_manager:
            yield
        self.assertEqual(error, context_manager.exception.args[0])
