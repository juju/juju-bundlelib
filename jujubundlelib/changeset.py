# Copyright 2015 Canonical Ltd.
# Licensed under the AGPLv3, see LICENCE file for details.

from __future__ import unicode_literals

import copy
import itertools

import models
import utils


class ChangeSet(object):
    """Hold the state for parser handlers.

    Also expose methods to send and receive changes (usually Python dicts).
    """
    services_added = {}
    machines_added = {}

    def __init__(self, bundle):
        self.bundle = bundle
        self._changeset = []
        self._counter = itertools.count()

    def send(self, change):
        """Store a change in this change set."""
        self._changeset.append(change)

    def recv(self):
        """Return all the collected changes.

        Changes are stored using self.send().
        """
        changeset = self._changeset
        self._changeset = []
        return changeset

    def next_action(self):
        """Return an incremental integer to be included in the changes ids."""
        return next(self._counter)

    def is_legacy_bundle(self):
        """Report whether the bundle uses the legacy (version 3) syntax."""
        return utils.is_legacy_bundle(self.bundle)


def handle_services(changeset):
    """Populate the change set with addCharm and addService changes."""
    charms = {}
    for service_name, service in changeset.bundle['services'].items():
        # Add the addCharm record if one hasn't been added yet.
        if service['charm'] not in charms:
            record_id = 'addCharm-{}'.format(changeset.next_action())
            changeset.send({
                'id': record_id,
                'method': 'addCharm',
                'args': [service['charm']],
                'requires': [],
            })
            charms[service['charm']] = record_id

        # Add the deploy record for this service.
        record_id = 'addService-{}'.format(changeset.next_action())
        changeset.send({
            'id': record_id,
            'method': 'deploy',
            'args': [
                service['charm'],
                service_name,
                service.get('options', {})
            ],
            'requires': [charms[service['charm']]],
        })
        changeset.services_added[service_name] = record_id
    return handle_machines


def handle_machines(changeset):
    """Populate the change set with addMachines changes."""
    for machine_name, machine in changeset.bundle.get('machines', {}).items():
        record_id = 'addMachines-{}'.format(changeset.next_action())
        changeset.send({
            'id': record_id,
            'method': 'addMachines',
            'args': [
                {
                    'series': machine.get('series', ''),
                    'constraints': machine.get('constraints', {}),
                },
            ],
            'requires': [],
        })
        changeset.machines_added[str(machine_name)] = record_id
    return handle_relations


def handle_relations(changeset):
    """Populate the change set with addRelation changes."""
    for relation in changeset.bundle.get('relations', []):
        relations = [models.Relation(*i.split(':')) if ':' in i
                     else models.Relation(i, '') for i in relation]
        changeset.send({
            'id': 'addRelation-{}'.format(changeset.next_action()),
            'method': 'addRelation',
            'args': [
                '${}'.format(
                    changeset.services_added[rel.name]) +
                (':{}'.format(rel.interface) if rel.interface else '')
                for rel in relations
            ],
            'requires': [changeset.services_added[rel.name] for
                         rel in relations],
        })
    return handle_units


def handle_units(changeset):
    """Populate the change set with addUnit changes."""
    units, records = {}, {}
    for service_name, service in changeset.bundle['services'].items():
        for i in range(service['num_units']):
            record_id = 'addUnit-{}'.format(changeset.next_action())
            unit_name = '{}/{}'.format(service_name, i)
            records[record_id] = {
                'id': record_id,
                'method': 'addUnit',
                'args': [
                    '${}'.format(changeset.services_added[service_name]),
                    1,
                    None,
                ],
                'requires': [changeset.services_added[service_name]],
            }
            units[unit_name] = {
                'record': record_id,
                'service': service_name,
                'unit': i,
            }
    _handle_units_placement(changeset, units, records)


def _handle_units_placement(changeset, units, records):
    """Ensure that requires and placement directives are taken into account."""
    for service_name, service in changeset.bundle['services'].items():
        placement_directives = service.get('to', [])
        if not isinstance(placement_directives, (list, tuple)):
            placement_directives = [placement_directives]
        if placement_directives and not changeset.is_legacy_bundle():
            placement_directives += placement_directives[-1:] * \
                (service['num_units'] - len(placement_directives))
        for i in range(service['num_units']):
            unit = units['{}/{}'.format(service_name, i)]
            record = records[unit['record']]
            if i < len(placement_directives):
                record = _handle_unit_placement(
                    changeset, units, unit, record, placement_directives[i])
            changeset.send(record)


def _handle_unit_placement(
        changeset, units, unit, record, placement_directive):
    record = copy.deepcopy(record)
    if changeset.is_legacy_bundle():
        placement = models.parse_v3_unit_placement(placement_directive)
    else:
        placement = models.parse_v4_unit_placement(placement_directive)
    if placement.machine:
        if placement.machine == 'new':
            machine_record_id = 'addMachines-{}'.format(
                changeset.next_action())
            options = {}
            if placement.container_type:
                options = {'containerType': placement.container_type}
            changeset.send({
                'id': machine_record_id,
                'method': 'addMachines',
                'args': [options],
                'requires': [],
            })
        else:
            if changeset.is_legacy_bundle():
                record['args'][2] = '0'
                return record
            machine_record_id = changeset.machines_added[
                placement.machine]
            if placement.container_type:
                machine_record_id = _handle_container_placement(
                    changeset, placement, machine_record_id)
    else:
        placement_unit = '{}/{}'.format(
            placement.service, placement.unit)
        machine_record_id = units[placement_unit]['record']
        if placement.container_type:
                machine_record_id = _handle_container_placement(
                    changeset, placement, machine_record_id)
    record['requires'].append(machine_record_id)
    record['args'][2] = '${}'.format(machine_record_id)
    return record


def _handle_container_placement(changeset, placement, machine_record_id):
    container_record_id = 'addMachines-{}'.format(changeset.next_action())
    options = {
        'containerType': placement.container_type,
        'parentId': '${}'.format(machine_record_id),
    }
    changeset.send({
        'id': container_record_id,
        'method': 'addMachines',
        'args': [options],
        'requires': [machine_record_id],
    })
    return container_record_id


def parse(bundle, handler=handle_services):
    """Return a generator yielding changes required to deploy the given bundle.

    The bundle argument is a YAML decoded Python dict.
    """
    changeset = ChangeSet(bundle)
    while True:
        handler = handler(changeset)
        for change in changeset.recv():
            yield change
        if handler is None:
            break
