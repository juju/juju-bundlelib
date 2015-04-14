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
