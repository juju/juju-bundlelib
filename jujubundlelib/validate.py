# Copyright 2015 Canonical Ltd.
# Licensed under the AGPLv3, see LICENCE file for details.

from __future__ import unicode_literals

import collections

import models
import pyutils
import references
import utils


class BundleValidator(object):
    """Maintain a state of bundle validation, including the bundle object
    and the errors list.
    """

    def __init__(self, bundle):
        self.bundle = bundle
        self._errors = []

    def add_error(self, error):
        """Add an error to the list of validation errors."""
        self._errors.append(error)

    def errors(self):
        """Return the list of all errors produced during validation"""
        return self._errors

    def is_legacy_bundle(self):
        """Report whether the bundle uses the legacy (version 3) syntax."""
        return utils.is_legacy_bundle(self.bundle)


def validate(bundle):
    """Validate a bundle object and all of its components."""
    if not isinstance(bundle, collections.Mapping):
        return ['bundle does not appear to be a bundle']
    validator = BundleValidator(bundle)
    machines = bundle.get('machines', {})
    if not isinstance(machines, collections.Mapping):
        return ['machines spec does not appear to be well-formed']
    machines_used = dict((i, False) for i in machines)
    services = bundle.get('services')
    if services is None:
        return ['services spec is required']

    series = validator.bundle.get('series')
    if series and not valid_series(series):
        validator.add_error(
            'bundle has invalid series {}'.format(series))
    validate_machines(validator)
    validate_services(validator,
                      machines_used=machines_used)
    validate_relations(validator)

    for machine, used in machines_used.items():
        if not used:
            validator.add_error(
                'machine {} not referred to by a placement '
                'directive'.format(machine))
    return validator.errors()


def valid_series(series):
    """Validate a series of some entity."""
    return references.valid_series(series) and series != 'bundle'


def valid_constraints(constraints):
    """Validate a constraints string."""
    constraint_types = (
        'arch',
        'cpu-cores',
        'mem',
        'root-disk',
        'container',
        'cpu-power',
        'tags',
        'networks',
        'instance-type',
    )
    if constraints:
        constraints = constraints.split()
        for constraint in constraints:
            parts = constraint.split('=')
            if (len(parts) != 2 or
                    not parts[1] or
                    parts[0] not in constraint_types):
                return False
    return True


def validate_machines(validator):
    """Validate the machines object (if it exists) within the context of the
    bundle.
    """
    for machine_id, machine in validator.bundle.get('machines', {}).items():
        try:
            int_id = int(machine_id)
            if int_id < 0:
                validator.add_error(
                    'machine {} has an invalid id, must be positive '
                    'digit'.format(
                        machine_id))
        except (TypeError, ValueError):
            validator.add_error(
                'machine {} has an invalid id, must be digit'.format(
                    machine_id))
        if ('constraints' in machine and
                not valid_constraints(machine['constraints'])):
            validator.add_error(
                'machine {} has invalid constraints {}'.format(
                    machine_id, machine['constraints']))
        if ('series' in machine and
                not valid_series(machine['series'])):
            validator.add_error(
                'machine {} has invalid series {}'.format(
                    machine_id, machine['series']))
        if ('annotations' in machine and
                not isinstance(machine['annotations'], collections.Mapping)):
            validator.add_error(
                'machine {} has invalid annotations {}'.format(
                    machine_id, machine['annotations']))


def validate_services(validator, machines_used={}):
    """Validate each service within the bundle.

    if machines_used is supplied, then machines in the dict will be marked
    as used, allowing validation that all machines in the machine spec have
    been used.
    """
    services = validator.bundle.get('services')
    if not isinstance(services, collections.Mapping):
        validator.add_error('services spec does not appear to be well-formed')
        return
    for service_name, service in services.items():
        try:
            charm = references.Reference.from_string(service.get('charm'))
        except ValueError as e:
            validator.add_error(
                'invalid charm specified for service {}: {}'.format(
                    service_name, pyutils.exception_string(e)))
            charm = None
        else:
            if charm.is_local():
                validator.add_error(
                    'local charms not allowed for service {}: {}'.format(
                        service_name, charm))
            if charm.is_bundle():
                validator.add_error(
                    'bundles not allowed for service {}: {}'.format(
                        service_name, charm))
        if ('constraints' in service and
                not valid_constraints(service['constraints'])):
            validator.add_error(
                'service {} has invalid constraints {}'.format(
                    service_name, service['constraints']))
        num_units = service.get('num_units')
        try:
            num_units = int(num_units)
        except (TypeError, ValueError):
            validator.add_error('invalid units for service {}: {}'.format(
                service_name, num_units))
            validate_placements(validator, service, charm, machines_used)
            continue
        if num_units < 0:
            validator.add_error(
                'invalid units for service {}: {}'.format(
                    service_name, service['num_units']))
        placements = validate_placements(validator, service, charm,
                                         machines_used)
        if len(placements) > num_units:
            validator.add_error(
                'too many units for service {}'.format(service_name))
        validate_options(validator, service_name, service)


def validate_placements(validator, service, charm, machines_used):
    """Validate all placement directives for a given service"""
    if 'to' in service:
        placements = service['to']
        if not isinstance(placements, (list, tuple)):
            placements = [placements]
        for placement in placements:
            validate_placement(validator, placement, charm,
                               machines_used)
        return placements
    return []


def validate_placement(validator, placement, charm, machines_used):
    """Validate a placement directive against other services and, if
    applicable, other machines within the bundle.

    Note that some of the logic within this differs between legacy and
    version 4 bundles.
    """
    try:
        if validator.is_legacy_bundle():
            unit_placement = models.parse_v3_unit_placement(placement)
        else:
            unit_placement = models.parse_v4_unit_placement(placement)
    except ValueError as e:
        validator.add_error(pyutils.exception_string(e))
        return
    if unit_placement.service:
        if unit_placement.service not in validator.bundle['services']:
            validator.add_error(
                'placement {} refers to non-existant service {}'.format(
                    placement, unit_placement.service))
            return
        service = validator.bundle['services'][unit_placement.service]
        if unit_placement.unit:
            if int(unit_placement.unit) + 1 > int(service['num_units']):
                validator.add_error(
                    'placement {} specifies a unit greater than the '
                    'units in service {}'.format(
                        placement, unit_placement.service))
    elif unit_placement.machine:
        if not validator.is_legacy_bundle():
            machine = int(unit_placement.machine)
            if machine not in validator.bundle['machines']:
                validator.add_error(
                    'placement {} refers to a non-existant machine '
                    '{}'.format(placement, unit_placement.machine))
            else:
                if charm:
                    machine_series = validator.bundle['machines'][machine].get(
                        'series', validator.bundle.get('series'))
                    if machine_series != charm.series:
                        validator.add_error(
                            'charm {} cannot be deployed to machine with '
                            'different series {}'.format(
                                charm, machine_series))
                if machine in machines_used:
                    machines_used[machine] = True


def validate_relations(validator):
    """Validate relations, ensuring that the endpoints exist."""
    relations = validator.bundle.get('relations', [])
    if not isinstance(relations, (list, tuple)):
        validator.add_error('relations {} are malformed'.format(relations))
        return
    for relation in relations:
        if not isinstance(relation, (list, tuple)):
            validator.add_error('relation {} is malformed'.format(relation))
            continue
        for endpoint in relation:
            try:
                service, _ = endpoint.split(':')
            except ValueError:
                validator.add_error('endpoint {} is malformed; name and '
                                    'interface required'.format(endpoint))
                continue
            if service not in validator.bundle['services']:
                validator.add_error(
                    'relation {} refers to a non-existant service '
                    '{}'.format(relation, service))


def validate_options(validator, service_name, service):
    """Lazily validate the options, ensuring that they are a dict."""
    if ('options' in service and
            not isinstance(service['options'], collections.Mapping)):
        validator.add_error(
            'service {} has malformed options'.format(service_name))
