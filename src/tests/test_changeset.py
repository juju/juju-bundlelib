from __future__ import unicode_literals

from collections import OrderedDict
import unittest

from src import changeset


class TestParsePlacements(unittest.TestCase):

    def test_parse_v3(self):
        self.assertEqual(
            changeset.UnitPlacement('', '', '', ''),
            changeset._parse_v3_unit_placement(''),
        )
        self.assertEqual(
            changeset.UnitPlacement('', '0', '', ''),
            changeset._parse_v3_unit_placement('0'),
        )
        self.assertEqual(
            changeset.UnitPlacement('', '', 'mysql', ''),
            changeset._parse_v3_unit_placement('mysql'),
        )
        self.assertEqual(
            changeset.UnitPlacement('lxc', '0', '', ''),
            changeset._parse_v3_unit_placement('lxc:0'),
        )
        self.assertEqual(
            changeset.UnitPlacement('', '', 'mysql', '1'),
            changeset._parse_v3_unit_placement('mysql=1'),
        )
        self.assertEqual(
            changeset.UnitPlacement('lxc', '', 'mysql', '1'),
            changeset._parse_v3_unit_placement('lxc:mysql=1'),
        )

    def test_parse_v4(self):
        self.assertEqual(
            changeset.UnitPlacement('', '', '', ''),
            changeset._parse_v4_unit_placement(''),
        )
        self.assertEqual(
            changeset.UnitPlacement('', '0', '', ''),
            changeset._parse_v4_unit_placement('0'),
        )
        self.assertEqual(
            changeset.UnitPlacement('', '', 'mysql', ''),
            changeset._parse_v4_unit_placement('mysql'),
        )
        self.assertEqual(
            changeset.UnitPlacement('lxc', '0', '', ''),
            changeset._parse_v4_unit_placement('lxc:0'),
        )
        self.assertEqual(
            changeset.UnitPlacement('', '', 'mysql', '1'),
            changeset._parse_v4_unit_placement('mysql/1'),
        )
        self.assertEqual(
            changeset.UnitPlacement('lxc', '', 'mysql', '1'),
            changeset._parse_v4_unit_placement('lxc:mysql/1'),
        )


class TestChangeSet(unittest.TestCase):

    def setUp(self):
        self.cs = changeset.ChangeSet({
            'services': {},
            'machines': {},
            'relations': {},
            'series': 'trusty',
        })

    def test_send_receive(self):
        self.cs.send('foo')
        self.cs.send('bar')
        self.assertEqual(['foo', 'bar'], self.cs.recv())
        self.assertEqual([], self.cs.recv())


class TestParse(unittest.TestCase):

    def handler1(self, changeset):
        for i in range(3):
            changeset.send((1, i))
        return self.handler2

    def handler2(self, changeset):
        for i in range(3):
            changeset.send((2, i))
        return None

    def test_parse(self):
        bundle = {
            'services': {},
            'machines': {},
            'relations': {},
            'series': 'trusty',
        }
        changes = list(changeset.parse(bundle, handler=self.handler1))
        self.assertEqual(
            [
                (1, 0),
                (1, 1),
                (1, 2),
                (2, 0),
                (2, 1),
                (2, 2),
            ],
            changes,
        )

    def test_parse_nothing(self):
        bundle = {'services': {}}
        self.assertEqual([], list(changeset.parse(bundle)))


class TestHandleServices(unittest.TestCase):

    def test_handler(self):
        cs = changeset.ChangeSet({
            # Use an ordered dict so that changes' ids can be predicted
            # deterministically.
            'services': OrderedDict((
                ('django', {
                    'charm': 'cs:trusty/django-42',
                }),
                ('mysql-master', {
                    'charm': 'cs:utopic/mysql-47',
                }),
                ('mysql-slave', {
                    'charm': 'cs:utopic/mysql-47',
                    'options': {
                        'key1': 'value1',
                        'key2': 'value2',
                    }
                }),
            ))
        })
        handler = changeset.handle_services(cs)
        self.assertEqual(changeset.handle_machines, handler)
        self.assertEqual(
            [
                {
                    'id': 'addCharm-0',
                    'method': 'addCharm',
                    'args': ['cs:trusty/django-42'],
                    'requires': []
                },
                {
                    'id': 'addService-1',
                    'method': 'deploy',
                    'args': ['cs:trusty/django-42', 'django', {}],
                    'requires': ['addCharm-0']
                },
                {
                    'id': 'addCharm-2',
                    'method': 'addCharm',
                    'args': ['cs:utopic/mysql-47'],
                    'requires': []
                },
                {
                    'id': 'addService-3',
                    'method': 'deploy',
                    'args': ['cs:utopic/mysql-47', 'mysql-master', {}],
                    'requires': ['addCharm-2']
                },
                {
                    'id': 'addService-4',
                    'method': 'deploy',
                    'args': ['cs:utopic/mysql-47', 'mysql-slave', {
                        'key1': 'value1',
                        'key2': 'value2',
                    }],
                    'requires': ['addCharm-2']
                },
            ],
            cs.recv())

    def test_no_services(self):
        cs = changeset.ChangeSet({'services': {}})
        changeset.handle_services(cs)
        self.assertEqual([], cs.recv())


class TestHandleMachines(unittest.TestCase):

    def test_handler(self):
        cs = changeset.ChangeSet({
            # Use an ordered dict so that changes' ids can be predicted
            # deterministically.
            'machines': OrderedDict((
                ('1', {'series': 'vivid'}),
                ('2', {}),
                ('42', {'constraints': {'cpu-cores': 4}}),
            ))
        })
        handler = changeset.handle_machines(cs)
        self.assertEqual(changeset.handle_relations, handler)
        self.assertEqual(
            [
                {
                    'id': 'addMachine-0',
                    'method': 'addMachine',
                    'args': ['vivid', {}],
                    'requires': []
                },
                {
                    'id': 'addMachine-1',
                    'method': 'addMachine',
                    'args': ['', {}],
                    'requires': []
                },
                {
                    'id': 'addMachine-2',
                    'method': 'addMachine',
                    'args': ['', {'cpu-cores': 4}],
                    'requires': []
                },
            ],
            cs.recv())

    def test_no_machines(self):
        cs = changeset.ChangeSet({'services': {}})
        changeset.handle_machines(cs)
        self.assertEqual([], cs.recv())


class TestHandleRelations(unittest.TestCase):

    def test_handler(self):
        cs = changeset.ChangeSet({
            'services': OrderedDict((
                ('django', {
                    'charm': 'cs:trusty/django-42',
                }),
                ('mysql', {
                    'charm': 'cs:utopic/mysql-47',
                }),
            )),
            'relations': [
                ['mysql:foo', 'django:bar'],
            ],
        })
        cs.services_added = {
            'django': 'addService-1',
            'mysql': 'addService-3',
        }
        handler = changeset.handle_relations(cs)
        self.assertEqual(changeset.handle_units, handler)
        self.assertEqual(
            [
                {
                    'id': 'addRelation-0',
                    'method': 'addRelation',
                    'args': [
                        [
                            '$addService-3',
                            {'name': 'foo'}
                        ], [
                            '$addService-1',
                            {'name': 'bar'}
                        ]
                    ],
                    'requires': [
                        'addService-3',
                        'addService-1'
                    ],
                }
            ], cs.recv()
        )

    def test_no_relations(self):
        cs = changeset.ChangeSet({'relations': []})
        changeset.handle_relations(cs)
        self.assertEqual([], cs.recv())


class TestHandleUnits(unittest.TestCase):

    def test_handler(self):
        cs = changeset.ChangeSet({
            'services': OrderedDict((
                ('django', {
                    'charm': 'cs:trusty/django-42',
                    'num_units': 1,
                    'to': '42',
                }),
                ('mysql', {
                    'charm': 'cs:utopic/mysql-47',
                    'num_units': 0,
                }),
                ('haproxy', {
                    'charm': 'cs:precise/haproxy-0',
                    'num_units': 2,
                }),
                ('rails', {
                    'charm': 'cs:precise/rails-1',
                    'num_units': 1,
                    'to': ['0'],
                }),
            )),
            'machines': {0: {}, 42: {}},
        })
        cs.services_added = {
            'django': 'addService-1',
            'mysql': 'addService-2',
            'haproxy': 'addService-3',
            'rails': 'addService-4',
        }
        cs.machines_added = {
            '0': 'addMachine-0',
            '42': 'addMachine-42',
        }
        handler = changeset.handle_units(cs)
        self.assertIsNone(handler)
        self.assertEqual(
            [
                {
                    'id': 'addUnit-0',
                    'method': 'addUnit',
                    'args': ['$addService-1', 1, '$addMachine-42'],
                    'requires': ['addService-1', 'addMachine-42'],
                },
                {
                    'id': 'addUnit-1',
                    'method': 'addUnit',
                    'args': ['$addService-3', 1, None],
                    'requires': ['addService-3'],
                },
                {
                    'id': 'addUnit-2',
                    'method': 'addUnit',
                    'args': ['$addService-3', 1, None],
                    'requires': ['addService-3'],
                },
                {
                    'id': 'addUnit-3',
                    'method': 'addUnit',
                    'args': ['$addService-4', 1, '$addMachine-0'],
                    'requires': ['addService-4', 'addMachine-0'],
                },
            ],
            cs.recv())

    def test_no_units(self):
        cs = changeset.ChangeSet({'services': {}})
        changeset.handle_units(cs)
        self.assertEqual([], cs.recv())
