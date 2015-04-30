# Copyright 2015 Canonical Ltd.
# Licensed under the AGPLv3, see LICENCE file for details.

from __future__ import unicode_literals

from collections import OrderedDict
import unittest

from jujubundlelib import changeset


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

    def test_is_legacy_bundle(self):
        self.assertFalse(self.cs.is_legacy_bundle())
        cs = changeset.ChangeSet({'services': {}})
        self.assertTrue(cs.is_legacy_bundle())


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
                    'id': 'addMachines-0',
                    'method': 'addMachines',
                    'args': [{'constraints': {}, 'series': 'vivid'}],
                    'requires': [],
                },
                {
                    'id': 'addMachines-1',
                    'method': 'addMachines',
                    'args': [{'constraints': {}, 'series': ''}],
                    'requires': [],
                },
                {
                    'id': 'addMachines-2',
                    'method': 'addMachines',
                    'args': [{'constraints': {'cpu-cores': 4}, 'series': ''}],
                    'requires': [],
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
                    'args': ['$addService-3:foo', '$addService-1:bar'],
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
            '0': 'addMachines-0',
            '42': 'addMachines-42',
        }
        handler = changeset.handle_units(cs)
        self.assertIsNone(handler)
        self.assertEqual(
            [
                {
                    'id': 'addUnit-0',
                    'method': 'addUnit',
                    'args': ['$addService-1', 1, '$addMachines-42'],
                    'requires': ['addService-1', 'addMachines-42'],
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
                    'args': ['$addService-4', 1, '$addMachines-0'],
                    'requires': ['addService-4', 'addMachines-0'],
                },
            ],
            cs.recv())

    def test_no_units(self):
        cs = changeset.ChangeSet({'services': {}})
        changeset.handle_units(cs)
        self.assertEqual([], cs.recv())

    def test_subordinate_service(self):
        cs = changeset.ChangeSet({'services': {'logger': {'charm': 'logger'}}})
        changeset.handle_units(cs)
        self.assertEqual([], cs.recv())

    def test_unit_in_new_machine(self):
        cs = changeset.ChangeSet({
            'services': OrderedDict((
                ('django-new', {
                    'charm': 'cs:trusty/django-42',
                    'num_units': 1,
                    'to': 'new',
                }),
            )),
            'machines': {},
        })
        cs.services_added = {
            'django-new': 'addService-1',
        }
        handler = changeset.handle_units(cs)
        self.assertIsNone(handler)
        self.assertEqual(
            [
                {
                    'id': 'addMachines-1',
                    'method': 'addMachines',
                    'args': [{}],
                    'requires': [],
                },
                {
                    'id': 'addUnit-0',
                    'method': 'addUnit',
                    'args': ['$addService-1', 1, '$addMachines-1'],
                    'requires': ['addService-1', 'addMachines-1'],
                },
            ],
            cs.recv())

    def test_placement_unit_in_service(self):
        cs = changeset.ChangeSet({
            'services': OrderedDict((
                ('wordpress', {
                    'charm': 'cs:utopic/wordpress-0',
                    'num_units': 3,
                }),
                ('django', {
                    'charm': 'cs:trusty/django-42',
                    'num_units': 2,
                    'to': ['wordpress'],
                }),
            )),
            'machines': {},
        })
        cs.services_added = {
            'django': 'addService-1',
            'wordpress': 'addService-42',
        }
        handler = changeset.handle_units(cs)
        self.assertIsNone(handler)
        self.assertEqual(
            [
                {
                    'id': 'addUnit-0',
                    'method': 'addUnit',
                    'args': ['$addService-42', 1, None],
                    'requires': ['addService-42'],
                },
                {

                    'id': 'addUnit-1',
                    'method': 'addUnit',
                    'args': ['$addService-42', 1, None],
                    'requires': ['addService-42'],
                },
                {
                    'id': 'addUnit-2',
                    'method': 'addUnit',
                    'args': ['$addService-42', 1, None],
                    'requires': ['addService-42'],
                },
                {
                    'id': 'addUnit-3',
                    'method': 'addUnit',
                    'args': ['$addService-1', 1, '$addUnit-0'],
                    'requires': ['addService-1', 'addUnit-0'],
                },
                {
                    'id': 'addUnit-4',
                    'method': 'addUnit',
                    'args': ['$addService-1', 1, '$addUnit-1'],
                    'requires': ['addService-1', 'addUnit-1'],
                }
            ],
            cs.recv())

    def test_unit_colocation_to_unit(self):
        cs = changeset.ChangeSet({
            'services': OrderedDict((
                ('django-new', {
                    'charm': 'cs:trusty/django-42',
                    'num_units': 1,
                }),
                ('django-unit', {
                    'charm': 'cs:trusty/django-42',
                    'num_units': 1,
                    'to': 'django-new/0',
                }),
            )),
            'machines': {},
        })
        cs.services_added = {
            'django-new': 'addService-1',
            'django-unit': 'addService-2',
        }
        handler = changeset.handle_units(cs)
        self.assertIsNone(handler)
        self.assertEqual(
            [
                {
                    'id': 'addUnit-0',
                    'method': 'addUnit',
                    'args': ['$addService-1', 1, None],
                    'requires': ['addService-1'],
                },
                {
                    'id': 'addUnit-1',
                    'method': 'addUnit',
                    'args': ['$addService-2', 1, '$addUnit-0'],
                    'requires': ['addService-2', 'addUnit-0'],
                },
            ],
            cs.recv())

    def test_unit_in_preexisting_machine(self):
        cs = changeset.ChangeSet({
            'services': OrderedDict((
                ('django-machine', {
                    'charm': 'cs:trusty/django-42',
                    'num_units': 1,
                    'to': '42',
                }),
            )),
            'machines': {42: {}},
        })
        cs.services_added = {
            'django-machine': 'addService-3',
        }
        cs.machines_added = {
            '42': 'addMachines-42',
        }
        handler = changeset.handle_units(cs)
        self.assertIsNone(handler)
        self.assertEqual(
            [
                {
                    'id': 'addUnit-0',
                    'method': 'addUnit',
                    'args': ['$addService-3', 1, '$addMachines-42'],
                    'requires': ['addService-3', 'addMachines-42'],
                },
            ],
            cs.recv())

    def test_unit_in_new_machine_container(self):
        cs = changeset.ChangeSet({
            'services': OrderedDict((
                ('django-new-lxc', {
                    'charm': 'cs:trusty/django-42',
                    'num_units': 1,
                    'to': 'lxc:new',
                }),
            )),
            'machines': {},
        })
        cs.services_added = {
            'django-new-lxc': 'addService-4',
        }
        handler = changeset.handle_units(cs)
        self.assertIsNone(handler)
        self.assertEqual(
            [
                {
                    'id': 'addMachines-1',
                    'method': 'addMachines',
                    'args': [{'containerType': 'lxc'}],
                    'requires': [],
                },
                {
                    'id': 'addUnit-0',
                    'method': 'addUnit',
                    'args': ['$addService-4', 1, '$addMachines-1'],
                    'requires': ['addService-4', 'addMachines-1'],
                },
            ],
            cs.recv())

    def test_unit_colocation_to_container_in_unit(self):
        cs = changeset.ChangeSet({
            'services': OrderedDict((
                ('django-new', {
                    'charm': 'cs:trusty/django-42',
                    'num_units': 1,
                }),
                ('django-unit-lxc', {
                    'charm': 'cs:trusty/django-42',
                    'num_units': 1,
                    'to': 'lxc:django-new/0',
                }),
            )),
            'machines': {},
        })
        cs.services_added = {
            'django-new': 'addService-1',
            'django-unit-lxc': 'addService-5',
        }
        handler = changeset.handle_units(cs)
        self.assertIsNone(handler)
        self.maxDiff = None
        self.assertEqual(
            [
                {
                    'id': 'addUnit-0',
                    'method': 'addUnit',
                    'args': ['$addService-1', 1, None],
                    'requires': ['addService-1'],
                },
                {
                    'id': 'addMachines-2',
                    'method': 'addMachines',
                    'args': [{
                        'containerType': 'lxc',
                        'parentId': '$addUnit-0',
                    }],
                    'requires': ['addUnit-0'],
                },
                {
                    'id': 'addUnit-1',
                    'method': 'addUnit',
                    'args': ['$addService-5', 1, '$addMachines-2'],
                    'requires': ['addService-5', 'addMachines-2'],
                },
            ],
            cs.recv())

    def test_placement_unit_in_container_in_service(self):
        cs = changeset.ChangeSet({
            'services': OrderedDict((
                ('wordpress', {
                    'charm': 'cs:utopic/wordpress-0',
                    'num_units': 1,
                }),
                ('rails', {
                    'charm': 'cs:utopic/rails-0',
                    'num_units': 2,
                }),
                ('django', {
                    'charm': 'cs:trusty/django-42',
                    'num_units': 3,
                    'to': ['lxc:wordpress', 'kvm:rails'],
                }),
            )),
            'machines': {},
        })
        cs.services_added = {
            'django': 'addService-1',
            'wordpress': 'addService-42',
            'rails': 'addService-47',
        }
        handler = changeset.handle_units(cs)
        self.assertIsNone(handler)
        self.assertEqual(
            [
                {
                    'id': 'addUnit-0',
                    'method': 'addUnit',
                    'args': ['$addService-42', 1, None],
                    'requires': ['addService-42'],
                },
                {
                    'id': 'addUnit-1',
                    'method': 'addUnit',
                    'args': ['$addService-47', 1, None],
                    'requires': ['addService-47'],
                },
                {
                    'id': 'addUnit-2',
                    'method': 'addUnit',
                    'args': ['$addService-47', 1, None],
                    'requires': ['addService-47'],
                },
                {
                    'id': 'addMachines-6',
                    'method': 'addMachines',
                    'args': [{
                        'containerType': 'lxc',
                        'parentId': '$addUnit-0',
                    }],
                    'requires': ['addUnit-0'],
                },
                {
                    'id': 'addUnit-3',
                    'method': 'addUnit',
                    'args': ['$addService-1', 1, '$addMachines-6'],
                    'requires': ['addService-1', 'addMachines-6'],
                },
                {
                    'id': 'addMachines-7',
                    'method': 'addMachines',
                    'args': [{
                        'containerType': 'kvm',
                        'parentId': '$addUnit-1',
                    }],
                    'requires': ['addUnit-1'],
                },
                {
                    'id': 'addUnit-4',
                    'method': 'addUnit',
                    'args': ['$addService-1', 1, '$addMachines-7'],
                    'requires': ['addService-1', 'addMachines-7'],
                },
                {
                    'id': 'addMachines-8',
                    'method': 'addMachines',
                    'args': [{
                        'containerType': 'kvm',
                        'parentId': '$addUnit-2',
                    }],
                    'requires': ['addUnit-2'],
                },
                {
                    'id': 'addUnit-5',
                    'method': 'addUnit',
                    'args': ['$addService-1', 1, '$addMachines-8'],
                    'requires': ['addService-1', 'addMachines-8'],
                },
            ],
            cs.recv())

    def test_unit_in_preexisting_machine_container(self):
        cs = changeset.ChangeSet({
            'services': OrderedDict((
                ('django-machine-lxc', {
                    'charm': 'cs:trusty/django-42',
                    'num_units': 1,
                    'to': 'lxc:0',
                }),
            )),
            'machines': {0: {}},
        })
        cs.services_added = {
            'django-machine-lxc': 'addService-6',
        }
        cs.machines_added = {
            '0': 'addMachines-47',
        }
        handler = changeset.handle_units(cs)
        self.assertIsNone(handler)
        self.assertEqual(
            [
                {
                    'id': 'addMachines-1',
                    'method': 'addMachines',
                    'args': [{
                        'containerType': 'lxc',
                        'parentId': '$addMachines-47',
                    }],
                    'requires': ['addMachines-47'],
                },
                {
                    'id': 'addUnit-0',
                    'method': 'addUnit',
                    'args': ['$addService-6', 1, '$addMachines-1'],
                    'requires': ['addService-6', 'addMachines-1'],
                },
            ],
            cs.recv())

    def test_v3_placement_unit_in_bootstrap_node(self):
        cs = changeset.ChangeSet({
            'services': OrderedDict((
                ('django', {
                    'charm': 'cs:trusty/django-42',
                    'num_units': 1,
                    'to': '0',
                }),
            )),
        })
        cs.services_added = {
            'django': 'addService-1',
        }
        handler = changeset.handle_units(cs)
        self.assertIsNone(handler)
        self.assertEqual(
            [
                {
                    'id': 'addUnit-0',
                    'method': 'addUnit',
                    'args': ['$addService-1', 1, '0'],
                    'requires': ['addService-1'],
                },
            ],
            cs.recv())

    def test_v3_placement_unit_in_service(self):
        cs = changeset.ChangeSet({
            'services': OrderedDict((
                ('wordpress', {
                    'charm': 'cs:utopic/wordpress-0',
                    'num_units': 3,
                }),
                ('django', {
                    'charm': 'cs:trusty/django-42',
                    'num_units': 2,
                    'to': ['wordpress', 'wordpress'],
                }),
            )),
        })
        cs.services_added = {
            'django': 'addService-1',
            'wordpress': 'addService-42',
        }
        handler = changeset.handle_units(cs)
        self.assertIsNone(handler)
        self.assertEqual(
            [
                {
                    'id': 'addUnit-0',
                    'method': 'addUnit',
                    'args': ['$addService-42', 1, None],
                    'requires': ['addService-42'],
                },
                {

                    'id': 'addUnit-1',
                    'method': 'addUnit',
                    'args': ['$addService-42', 1, None],
                    'requires': ['addService-42'],
                },
                {
                    'id': 'addUnit-2',
                    'method': 'addUnit',
                    'args': ['$addService-42', 1, None],
                    'requires': ['addService-42'],
                },
                {
                    'id': 'addUnit-3',
                    'method': 'addUnit',
                    'args': ['$addService-1', 1, '$addUnit-0'],
                    'requires': ['addService-1', 'addUnit-0'],
                },
                {
                    'id': 'addUnit-4',
                    'method': 'addUnit',
                    'args': ['$addService-1', 1, '$addUnit-1'],
                    'requires': ['addService-1', 'addUnit-1'],
                }
            ],
            cs.recv())

    def test_v3_placement_unit_in_unit(self):
        cs = changeset.ChangeSet({
            'services': OrderedDict((
                ('wordpress', {
                    'charm': 'cs:utopic/wordpress-0',
                    'num_units': 1,
                }),
                ('django', {
                    'charm': 'cs:trusty/django-42',
                    'num_units': 1,
                    'to': 'wordpress=0',
                }),
            )),
        })
        cs.services_added = {
            'django': 'addService-1',
            'wordpress': 'addService-42',
        }
        handler = changeset.handle_units(cs)
        self.assertIsNone(handler)
        self.assertEqual(
            [
                {
                    'id': 'addUnit-0',
                    'method': 'addUnit',
                    'args': ['$addService-42', 1, None],
                    'requires': ['addService-42'],
                },
                {
                    'id': 'addUnit-1',
                    'method': 'addUnit',
                    'args': ['$addService-1', 1, '$addUnit-0'],
                    'requires': ['addService-1', 'addUnit-0'],
                },
            ],
            cs.recv())

    def test_v3_placement_unit_in_lxc_in_service(self):
        cs = changeset.ChangeSet({
            'services': OrderedDict((
                ('wordpress', {
                    'charm': 'cs:utopic/wordpress-0',
                    'num_units': 1,
                }),
                ('django', {
                    'charm': 'cs:trusty/django-42',
                    'num_units': 1,
                    'to': 'lxc:wordpress',
                }),
            )),
        })
        cs.services_added = {
            'django': 'addService-1',
            'wordpress': 'addService-42',
        }
        handler = changeset.handle_units(cs)
        self.assertIsNone(handler)
        self.assertEqual(
            [
                {
                    'id': 'addUnit-0',
                    'method': 'addUnit',
                    'args': ['$addService-42', 1, None],
                    'requires': ['addService-42'],
                },
                {
                    'id': 'addMachines-2',
                    'method': 'addMachines',
                    'args': [{
                        'containerType': 'lxc',
                        'parentId': '$addUnit-0',
                    }],
                    'requires': ['addUnit-0'],
                },
                {
                    'id': 'addUnit-1',
                    'method': 'addUnit',
                    'args': ['$addService-1', 1, '$addMachines-2'],
                    'requires': ['addService-1', 'addMachines-2'],
                },
            ],
            cs.recv())

    def test_v3_placement_unit_in_lxc_in_unit(self):
        cs = changeset.ChangeSet({
            'services': OrderedDict((
                ('wordpress', {
                    'charm': 'cs:utopic/wordpress-0',
                    'num_units': 1,
                }),
                ('django', {
                    'charm': 'cs:trusty/django-42',
                    'num_units': 1,
                    'to': 'lxc:wordpress=0',
                }),
            )),
        })
        cs.services_added = {
            'django': 'addService-1',
            'wordpress': 'addService-42',
        }
        handler = changeset.handle_units(cs)
        self.assertIsNone(handler)
        self.assertEqual(
            [
                {
                    'id': 'addUnit-0',
                    'method': 'addUnit',
                    'args': ['$addService-42', 1, None],
                    'requires': ['addService-42'],
                },
                {
                    'id': 'addMachines-2',
                    'method': 'addMachines',
                    'args': [{
                        'containerType': 'lxc',
                        'parentId': '$addUnit-0',
                    }],
                    'requires': ['addUnit-0'],
                },
                {
                    'id': 'addUnit-1',
                    'method': 'addUnit',
                    'args': ['$addService-1', 1, '$addMachines-2'],
                    'requires': ['addService-1', 'addMachines-2'],
                },
            ],
            cs.recv())
