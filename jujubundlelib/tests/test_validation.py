# Copyright 2015 Canonical Ltd.
# Licensed under the AGPLv3, see LICENCE file for details.

from __future__ import unicode_literals

import mock
import unittest

from jujubundlelib import (
    references,
    validation,
)


class TestBundleValidator(unittest.TestCase):

    def test_errors(self):
        validator = validation.BundleValidator({})
        self.assertEqual(validator.errors(), [])
        validator.add_error('bad-wolf')
        self.assertEqual(validator.errors(), ['bad-wolf'])

    def test_is_legacy_bundle(self):
        validator = validation.BundleValidator({'machines': {}})
        self.assertFalse(validator.is_legacy_bundle())
        validator = validation.BundleValidator({'services': {}})
        self.assertTrue(validator.is_legacy_bundle())


class TestValidate(unittest.TestCase):

    def test_validate(self):
        bundle = {
            'series': 'precise',
            'services': {
                'django': {'charm': 'cs:trusty/django-42', 'num_units': 1},
            },
        }
        self.assertEqual([], validation.validate(bundle))

    def test_no_services(self):
        bundle = {'services': {}}
        expected_errors = ['bundle does not define any services']
        self.assertEqual(expected_errors, validation.validate(bundle))

    def test_no_services_section(self):
        bundle = {}
        expected_errors = ['bundle does not define any services']
        self.assertEqual(expected_errors, validation.validate(bundle))

    def test_no_series(self):
        bundle = {
            'services': {
                'django': {'charm': 'cs:trusty/django-42', 'num_units': 1},
            },
        }
        self.assertEqual([], validation.validate(bundle))

    def test_bad_series(self):
        bundle = {
            'series': 'bad@wolf',
            'services': {
                'django': {'charm': 'cs:trusty/django-42', 'num_units': 1},
            },
        }
        expected_errors = ['bundle has invalid series bad@wolf']
        self.assertEqual(expected_errors, validation.validate(bundle))

    def test_bad_bundle(self):
        expected_errors = ['bundle does not appear to be a bundle']
        self.assertEqual(expected_errors, validation.validate('bad-wolf'))

    def test_machine_used(self):
        bundle = {
            'series': 'precise',
            'services': {
                'django': {'charm': 'cs:trusty/django-42', 'num_units': 1},
            },
            'machines': {
                '0': {},
            },
        }
        expected_errors = [
            'machine 0 not referred to by a placement directive']
        self.assertEqual(expected_errors, validation.validate(bundle))

    def test_bad_machines(self):
        bundle = {
            'services': {},
            'machines': 'bad-wolf',
        }
        expected_errors = ['machines spec does not appear to be well-formed']
        self.assertEqual(expected_errors, validation.validate(bundle))


class TestValidPartials(unittest.TestCase):

    def test_valid_series(self):
        self.assertFalse(validation.valid_series('a:b'))
        self.assertFalse(validation.valid_series('bundle'))
        self.assertTrue(validation.valid_series('precise'))

    def test_valid_constraints(self):
        good_constraints = (
            '',
            'mem=bar arch=42',
            'mem=bar    arch=42',
        )
        for constraint in good_constraints:
            self.assertTrue(validation.valid_constraints(constraint))

        bad_constraints = (
            'mem',
            'foo=bar'
            'mem=bar=baz',
            'mem=bar ='
            '==',
        )
        for constraint in bad_constraints:
            self.assertFalse(validation.valid_constraints(constraint))


class TestValidateMachines(unittest.TestCase):

    def test_validate_machines_success(self):
        tests = (
            {
                'about': 'no machines',
                'bundle': {'services': {}},
            },
            {
                'about': 'simple machine',
                'bundle': {'services': {}, 'machines': {'0': {}}},
            },
            {
                'about': 'machine with constraints',
                'bundle': {
                    'services': {},
                    'machines': {
                        '0': {
                            'constraints': 'mem=foo',
                        }
                    },
                },
            },
            {
                'about': 'machine with series',
                'bundle': {
                    'services': {},
                    'machines': {
                        '0': {
                            'series': 'trusty',
                        },
                    },
                },
            },
            {
                'about': 'machine with series, constraints, and annotations',
                'bundle': {
                    'services': {},
                    'machines': {
                        '0': {
                            'series': 'trusty',
                            'constraints': 'mem=foo',
                            'annotations': {
                                'foo': 'bar',
                            },
                        },
                    },
                },
            },
        )
        for test in tests:
            validator = validation.BundleValidator(test['bundle'])
            validation.validate_machines(validator)
            self.assertEqual(validator.errors(), [], msg=test['about'])

    def test_validate_machines_failure(self):
        tests = (
            {
                'about': 'bad name',
                'bundle': {'services': {}, 'machines': {'foo': {}}},
                'errors': [
                    'machine foo has an invalid id, must be digit',
                ],
            },
            {
                'about': 'negative name',
                'bundle': {'services': {}, 'machines': {'-1': {}}},
                'errors': [
                    'machine -1 has an invalid id, must be positive digit',
                ],
            },
            {
                'about': 'invalid constraints',
                'bundle': {
                    'services': {},
                    'machines': {
                        '0': {
                            'constraints': 'bad-wolf=foo',
                        }
                    },
                },
                'errors': [
                    'machine 0 has invalid constraints bad-wolf=foo',
                ],
            },
            {
                'about': 'invalid series',
                'bundle': {
                    'services': {},
                    'machines': {
                        '0': {
                            'series': 'bad@wolf',
                        },
                    },
                },
                'errors': [
                    'machine 0 has invalid series bad@wolf',
                ],
            },
            {
                'about': 'integration',
                'bundle': {
                    'services': {},
                    'machines': {
                        'bad-wolf': {
                            'series': 'bad@wolf',
                            'constraints': 'bad-wolf=foo',
                            'annotations': 'bad-wolf',
                        },
                    },
                },
                'errors': [
                    'machine bad-wolf has an invalid id, must be digit',
                    'machine bad-wolf has invalid constraints bad-wolf=foo',
                    'machine bad-wolf has invalid series bad@wolf',
                    'machine bad-wolf has invalid annotations bad-wolf',
                ],
            },
        )
        for test in tests:
            validator = validation.BundleValidator(test['bundle'])
            validation.validate_machines(validator)
            self.assertEqual(validator.errors(), test['errors'],
                             msg=test['about'])


class TestValidateServices(unittest.TestCase):

    @mock.patch('jujubundlelib.validation.validate_placement')
    def test_validate_services_success(self, mock_placement):
        tests = (
            {
                'about': 'plain service',
                'bundle': {
                    'services': {
                        'foo': {
                            'charm': 'cs:precise/django-1',
                            'num_units': 1,
                        },
                    },
                },
                'machines_used': {
                    'in': {},
                    'out': {},
                }
            },
            {
                'about': 'with constraints',
                'bundle': {
                    'services': {
                        'foo': {
                            'charm': 'cs:precise/django-1',
                            'num_units': 1,
                            'constraints': 'mem=foo',
                        },
                    },
                },
                'machines_used': {
                    'in': {},
                    'out': {},
                }
            },
            {
                'about': 'with single placement',
                'bundle': {
                    'services': {
                        'foo': {
                            'charm': 'cs:precise/django-1',
                            'num_units': 1,
                            'to': '0',
                        },
                    },
                },
                'machines_used': {
                    'in': {'0': False},
                    'out': {'0': True},
                }
            },
            {
                'about': 'with list placement',
                'bundle': {
                    'services': {
                        'foo': {
                            'charm': 'cs:precise/django-1',
                            'num_units': 1,
                            'to': ['0'],
                        },
                    },
                },
                'machines_used': {
                    'in': {'0': False},
                    'out': {'0': True},
                }
            },
            {
                'about': 'integration',
                'bundle': {
                    'services': {
                        'foo': {
                            'charm': 'cs:precise/django-1',
                            'num_units': 1,
                            'constraints': 'mem=foo',
                            'to': ['0'],
                        },
                    },
                },
                'machines_used': {
                    'in': {'0': False},
                    'out': {'0': True},
                }
            },
        )
        for test in tests:
            validator = validation.BundleValidator(test['bundle'])
            validation.validate_services(
                validator, machines_used=test['machines_used']['in'])
            self.assertEqual(validator.errors(), [], msg=test['about'])

    @mock.patch('jujubundlelib.validation.validate_placement')
    def test_validate_services_failure(self, mock_placement):
        tests = (
            {
                'about': 'malformed services',
                'bundle': {
                    'services': 'bad-wolf',
                },
                'errors': [
                    'services spec does not appear to be well-formed',
                ],
            },
            {
                'about': 'bad charm - parsing',
                'bundle': {
                    'services': {
                        'foo': {
                            'charm': 'cs:foo:bar/baz-q',
                            'num_units': 1,
                        },
                    },
                },
                'errors': [
                    'invalid charm specified for service foo: URL has '
                    'invalid series: foo:bar',
                ],
            },
            {
                'about': 'bad charm - local',
                'bundle': {
                    'services': {
                        'foo': {
                            'charm': 'local:precise/django-1',
                            'num_units': 1,
                        },
                    },
                },
                'errors': [
                    'local charms not allowed for service foo: '
                    'local:precise/django-1',
                ],
            },
            {
                'about': 'bad charm - bundle',
                'bundle': {
                    'services': {
                        'foo': {
                            'charm': 'cs:bundle/django-1',
                            'num_units': 1,
                        },
                    },
                },
                'errors': [
                    'bundles not allowed for service foo: '
                    'cs:bundle/django-1',
                ],
            },
            {
                'about': 'bad num_units',
                'bundle': {
                    'services': {
                        'foo': {
                            'charm': 'cs:precise/django-1',
                            'num_units': 'a',
                        },
                    },
                },
                'errors': [
                    'num_units for service foo must be an integer',
                ],
            },
            {
                'about': 'bad num_units regression: string digit',
                'bundle': {
                    'services': {
                        'foo': {
                            'charm': 'cs:precise/django-1',
                            'num_units': '1',
                        },
                    },
                },
                'errors': [
                    'num_units for service foo must be an integer',
                ],
            },
            {
                'about': 'bad constraints',
                'bundle': {
                    'services': {
                        'foo': {
                            'charm': 'cs:precise/django-1',
                            'num_units': 1,
                            'constraints': 'bad-wolf=foo',
                        },
                    },
                },
                'errors': [
                    'service foo has invalid constraints bad-wolf=foo',
                ],
            },
            {
                'about': 'too many placements',
                'bundle': {
                    'services': {
                        'foo': {
                            'charm': 'cs:precise/django-1',
                            'num_units': 1,
                            'to': ['0', '1'],
                        },
                    },
                },
                'errors': [
                    'too many units for service foo',
                ],
            },
            {
                'about': 'integration',
                'bundle': {
                    'services': {
                        'foo': {
                            'charm': 'cs:precise/django-1',
                            'num_units': -1,
                            'constraints': 'bad-wolf=foo',
                            'to': ['0', '1'],
                        },
                    },
                },
                'errors': [
                    'service foo has invalid constraints bad-wolf=foo',
                    'invalid units for service foo: -1',
                    'too many units for service foo',
                ],
            },
            {
                'about': 'no charm specified',
                'bundle': {
                    'services': {
                        'foo': {
                            'num_units': 1,
                        },
                    },
                },
                'errors': ['no charm specified for service foo'],
            },
        )
        for test in tests:
            validator = validation.BundleValidator(test['bundle'])
            validation.validate_services(validator)
            errors = validator.errors()
            msg = '{}: {} != {}'.format(test['about'], test['errors'], errors)
            self.assertEqual(test['errors'], errors, msg=msg)


class TestValidatePlacement(unittest.TestCase):

    def test_validate_placement_v3_success(self):
        tests = (
            {
                'about': 'v3: service, no unit',
                'placement': 'foo',
            },
            {
                'about': 'v3: service, unit',
                'placement': 'foo=0',
            },
            {
                'about': 'v3: machine',
                'placement': '0'
            },
            {
                'about': 'v3: container, service, no unit',
                'placement': 'lxc:foo',
            },
            {
                'about': 'v3: container, service, unit',
                'placement': 'lxc:foo=0',
            },
            {
                'about': 'v3: container, machine',
                'placement': 'lxc:0',
            },
        )
        for test in tests:
            validator = validation.BundleValidator({
                'services': {
                    'foo': {
                        'num_units': 1,
                    },
                },
            })
            validation.validate_placement(
                validator, test['placement'], None, {})
            self.assertEqual(validator.errors(), [], msg=test['about'])

    def test_validate_placement_v3_failure(self):
        tests = (
            {
                'about': 'v3: bad service, no unit',
                'placement': 'bar',
                'errors': [
                    'placement bar refers to non-existant service bar',
                ],
            },
            {
                'about': 'v3: bad service, good unit',
                'placement': 'bar=0',
                'errors': [
                    'placement bar=0 refers to non-existant service bar',
                ],
            },
            {
                'about': 'v3: good service, bad unit format',
                'placement': 'foo=a',
                'errors': [
                    'unit in placement foo=a must be digit',
                ],
            },
            {
                'about': 'v3: good service, bad unit',
                'placement': 'foo=1',
                'errors': [
                    'placement foo=1 specifies a unit greater than the units '
                    'in service foo',
                ],
            },
            {
                'about': 'v3: bad machine',
                'placement': '1',
                'errors': [
                    'legacy bundles may not place units on machines other '
                    'than 0',
                ],
            },
            {
                'about': 'v3: bad container',
                'placement': 'bar:0',
                'errors': [
                    'invalid container bar for placement bar:0',
                ],
            }
        )
        for test in tests:
            validator = validation.BundleValidator({
                'services': {
                    'foo': {
                        'num_units': 1,
                    },
                },
            })
            validation.validate_placement(
                validator, test['placement'], None, {})
            self.assertEqual(validator.errors(), test['errors'],
                             msg=test['about'])

    def test_validate_placement_v4_success(self):
        tests = (
            {
                'about': 'v4: service, no unit',
                'placement': 'foo',
            },
            {
                'about': 'v4: service, unit',
                'placement': 'foo/0',
            },
            {
                'about': 'v4: machine',
                'placement': '0',
                'expected_machines_used': {0: True},
            },
            {
                'about': 'v4: container, service, no unit',
                'placement': 'lxc:foo',
            },
            {
                'about': 'v4: container, service, unit',
                'placement': 'lxc:foo/0',
            },
            {
                'about': 'v4: container, machine',
                'placement': 'lxc:0',
            },
            {
                'about': 'v4: with charm',
                'placement': '0',
                'charm': references.Reference.from_string('cs:precise/foo-1'),
            },
        )
        for test in tests:
            machines_used = {0: False}
            validator = validation.BundleValidator({
                'services': {
                    'foo': {
                        'num_units': 1,
                    },
                },
                'machines': {
                    0: {
                        'series': 'precise',
                    },
                },
            })
            validation.validate_placement(
                validator, test['placement'], test.get('charm'), machines_used)
            self.assertEqual(validator.errors(), [], msg=test['about'])
            if 'expected_machines_used' in test:
                self.assertEqual(machines_used,
                                 test['expected_machines_used'])

    def test_validate_placement_v4_failure(self):
        tests = (
            {
                'about': 'v4: bad service, no unit',
                'placement': 'bar',
                'errors': [
                    'placement bar refers to non-existant service bar',
                ],
            },
            {
                'about': 'v4: bad service, good unit',
                'placement': 'bar/0',
                'errors': [
                    'placement bar/0 refers to non-existant service bar',
                ],
            },
            {
                'about': 'v4: good service, bad unit format',
                'placement': 'foo/a',
                'errors': [
                    'unit in placement foo/a must be digit',
                ],
            },
            {
                'about': 'v4: good service, bad unit',
                'placement': 'foo/1',
                'errors': [
                    'placement foo/1 specifies a unit greater than the units '
                    'in service foo',
                ],
            },
            {
                'about': 'v4: bad machine',
                'placement': '1',
                'errors': [
                    'placement 1 refers to a non-existant machine 1',
                ],
            },
            {
                'about': 'v4: bad container',
                'placement': 'bar:0',
                'errors': [
                    'invalid container bar for placement bar:0',
                ],
            },
            {
                'about': 'v4: bad charm series',
                'placement': '0',
                'charm': references.Reference.from_string('cs:trusty/foo-1'),
                'errors': [
                    'charm cs:trusty/foo-1 cannot be deployed to machine '
                    'with different series precise'
                ],
            },
        )
        for test in tests:
            validator = validation.BundleValidator({
                'services': {
                    'foo': {
                        'num_units': 1,
                    },
                },
                'machines': {
                    0: {
                        'series': 'precise',
                    },
                },
            })
            validation.validate_placement(
                validator, test['placement'], test.get('charm'), {})
            self.assertEqual(validator.errors(), test['errors'],
                             msg=test['about'])


class TestValidateRelations(unittest.TestCase):

    def test_validate_realtions_success(self):
        success = validation.BundleValidator({
            'services': {
                'foo': {},
                'bar': {},
            },
            'relations': [
                ['foo:a', 'bar:a'],
            ],
        })
        validation.validate_relations(success)
        self.assertEqual(success.errors(), [])

    def test_validate_relations_failure(self):
        failure = validation.BundleValidator({
            'services': {
                'foo': {},
                'bar': {},
            },
            'relations': [
                'bad-wolf',
                ['foo', 'bar:a'],
                ['foo:a', 'baz:a'],
            ],
        })
        validation.validate_relations(failure)
        failure.bundle['relations'] = 'bad-wolf'
        validation.validate_relations(failure)
        self.assertEqual(failure.errors(), [
            'relation bad-wolf is malformed',
            'endpoint foo is malformed; name and interface required',
            'relation {} refers to a non-existant service baz'.format(
                ['foo:a', 'baz:a']),
            'relations bad-wolf are malformed',
        ])


class TestValidateOptions(unittest.TestCase):

    def test_validate_options(self):
        success = validation.BundleValidator({
            'services': {
                'foo': {
                    'options': {
                        'foo': 'bar',
                    },
                },
                'bar': {},
            },
        })
        validation.validate_options(
            success, 'foo', success.bundle['services']['foo'])
        self.assertEqual(success.errors(), [])
        failure = validation.BundleValidator({
            'services': {
                'foo': {
                    'options': "bad-wolf"
                },
                'bar': {},
            },
        })
        validation.validate_options(
            failure, 'foo', failure.bundle['services']['foo'])
        self.assertEqual(
            failure.errors(), ['service foo has malformed options'])
