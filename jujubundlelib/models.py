# Copyright 2015 Canonical Ltd.
# Licensed under the AGPLv3, see LICENCE file for details.

from __future__ import unicode_literals

from collections import namedtuple


VALID_CONTAINERS = (
    'lxc',
    'kvm',
)


# Define a tuple holding a specific unit placement.
UnitPlacement = namedtuple(
    'UnitPlacement', [
        'container_type',
        'machine',
        'service',
        'unit',
    ]
)

# Define a relation object.
Relation = namedtuple('Relation', ['name', 'interface'])


def parse_v3_unit_placement(placement_str):
    """Return a UnitPlacement for bundles version 3, given a placement string.

    See https://github.com/juju/charmstore/blob/v4/docs/bundles.md
    """
    placement = placement_str
    container = machine = service = unit = ''
    if ':' in placement:
        try:
            container, placement = placement_str.split(':')
        except ValueError:
            msg = 'placement {} is malformed, too many parts'.format(
                placement_str)
            raise ValueError(msg.encode('utf-8'))
    if '=' in placement:
        try:
            placement, unit = placement.split('=')
        except ValueError:
            msg = 'placement {} is malformed, too many parts'.format(
                placement_str)
            raise ValueError(msg.encode('utf-8'))
    if placement.isdigit():
        machine = placement
    else:
        service = placement
    if (container and container not in VALID_CONTAINERS):
        msg = 'invalid container {} for placement {}'.format(
            container, placement_str)
        raise ValueError(msg.encode('utf-8'))
    if unit:
        try:
            unit = int(unit)
        except (TypeError, ValueError):
            msg = 'unit in placement {} must be digit'.format(placement_str)
            raise ValueError(msg.encode('utf-8'))
    if machine and machine != '0':
        raise ValueError(b'legacy bundles may not place units on machines '
                         b'other than 0')
    return UnitPlacement(container, machine, service, unit)


def parse_v4_unit_placement(placement_str):
    """Return a UnitPlacement for bundles version 4, given a placement string.

    See https://github.com/juju/charmstore/blob/v4/docs/bundles.md
    """
    placement = placement_str
    container = machine = service = unit = ''
    if ':' in placement:
        try:
            container, placement = placement_str.split(':')
        except ValueError:
            msg = 'placement {} is malformed, too many parts'.format(
                placement_str)
            raise ValueError(msg.encode('utf-8'))
    if '/' in placement:
        try:
            placement, unit = placement.split('/')
        except ValueError:
            msg = 'placement {} is malformed, too many parts'.format(
                placement_str)
            raise ValueError(msg.encode('utf-8'))
    if placement.isdigit() or placement == 'new':
        machine = placement
    else:
        service = placement
    if (container and container not in VALID_CONTAINERS):
        msg = 'invalid container {} for placement {}'.format(
            container, placement_str)
        raise ValueError(msg.encode('utf-8'))
    if unit:
        try:
            unit = int(unit)
        except (TypeError, ValueError):
            msg = 'unit in placement {} must be digit'.format(placement_str)
            raise ValueError(msg.encode('utf-8'))
    return UnitPlacement(container, machine, service, unit)
