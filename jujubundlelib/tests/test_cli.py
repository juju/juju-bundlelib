# Copyright 2015 Canonical Ltd.
# Licensed under the AGPLv3, see LICENCE file for details.

from __future__ import unicode_literals

import unittest

from jujubundlelib import cli
from jujubundlelib.tests import helpers


@helpers.mock_print()
class TestGetChangeset(helpers.BundleFileTestsMixin, unittest.TestCase):

    def test_valid_bundle(self, mock_print):
        path = self.make_bundle_file()
        error = cli.get_changeset([path])
        self.assertIsNone(error)
        self.assertTrue(mock_print.called)

    def test_invalid_bundle(self, mock_print):
        path = self.make_bundle_file("series: bad@wolf\nservices: 'oh nooooo'")
        error = cli.get_changeset([path])
        self.assertEqual(
            error, 'bundle has invalid series bad@wolf\n'
            'services spec does not appear to be well-formed')

    def test_invalid_yaml(self, mock_print):
        path = self.make_bundle_file(content=':')
        error = cli.get_changeset([path])
        self.assertEqual(
            'error: the provided bundle is not a valid YAML', error)
        self.assertFalse(mock_print.called)
