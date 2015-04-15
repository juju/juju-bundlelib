from __future__ import unicode_literals

from collections import namedtuple


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


def parse_v3_unit_placement(placement):
    """Return a UnitPlacement for bundles version 3, given a placement string.

    See https://github.com/juju/charmstore/blob/v4/docs/bundles.md
    """
    container = machine = service = unit = ''
    if ':' in placement:
        container, placement = placement.split(':')
    if '=' in placement:
        placement, unit = placement.split('=')
    if placement.isdigit():
        machine = placement
    else:
        service = placement
    return UnitPlacement(container, machine, service, unit)


def parse_v4_unit_placement(placement):
    """Return a UnitPlacement for bundles version 4, given a placement string.

    See https://github.com/juju/charmstore/blob/v4/docs/bundles.md
    """
    container = machine = service = unit = ''
    if ':' in placement:
        container, placement = placement.split(':')
    if '/' in placement:
        placement, unit = placement.split('/')
    if placement.isdigit() or placement == 'new':
        machine = placement
    else:
        service = placement
    return UnitPlacement(container, machine, service, unit)
