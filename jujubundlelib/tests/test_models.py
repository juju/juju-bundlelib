# Copyright 2015 Canonical Ltd.
# Licensed under the AGPLv3, see LICENCE file for details.

from __future__ import unicode_literals

import unittest

from jujubundlelib import models


class TestParseV3UnitPlacement(unittest.TestCase):

    def test_success(self):
        self.assertEqual(
            models.UnitPlacement('', '', '', ''),
            models.parse_v3_unit_placement(''),
        )
        self.assertEqual(
            models.UnitPlacement('', '0', '', ''),
            models.parse_v3_unit_placement('0'),
        )
        self.assertEqual(
            models.UnitPlacement('', '', 'mysql', ''),
            models.parse_v3_unit_placement('mysql'),
        )
        self.assertEqual(
            models.UnitPlacement('lxc', '0', '', ''),
            models.parse_v3_unit_placement('lxc:0'),
        )
        self.assertEqual(
            models.UnitPlacement('', '', 'mysql', '1'),
            models.parse_v3_unit_placement('mysql=1'),
        )
        self.assertEqual(
            models.UnitPlacement('lxc', '', 'mysql', '1'),
            models.parse_v3_unit_placement('lxc:mysql=1'),
        )


class TestParseV4UnitPlacement(unittest.TestCase):

    def test_success(self):
        self.assertEqual(
            models.UnitPlacement('', '', '', ''),
            models.parse_v4_unit_placement(''),
        )
        self.assertEqual(
            models.UnitPlacement('', '0', '', ''),
            models.parse_v4_unit_placement('0'),
        )
        self.assertEqual(
            models.UnitPlacement('', '', 'mysql', ''),
            models.parse_v4_unit_placement('mysql'),
        )
        self.assertEqual(
            models.UnitPlacement('lxc', '0', '', ''),
            models.parse_v4_unit_placement('lxc:0'),
        )
        self.assertEqual(
            models.UnitPlacement('', '', 'mysql', '1'),
            models.parse_v4_unit_placement('mysql/1'),
        )
        self.assertEqual(
            models.UnitPlacement('lxc', '', 'mysql', '1'),
            models.parse_v4_unit_placement('lxc:mysql/1'),
        )
        self.assertEqual(
            models.UnitPlacement('', 'new', '', ''),
            models.parse_v4_unit_placement('new'),
        )
        self.assertEqual(
            models.UnitPlacement('lxc', 'new', '', ''),
            models.parse_v4_unit_placement('lxc:new'),
        )
