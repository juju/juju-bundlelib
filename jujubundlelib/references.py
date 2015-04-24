# Copyright 2015 Canonical Ltd.
# Licensed under the AGPLv3, see LICENCE file for details.

from __future__ import unicode_literals

import re

from jujubundlelib import pyutils


# The URL of jujucharms.com, the home of Juju.
JUJUCHARMS_URL = 'https://jujucharms.com/'

# The following regular expressions are the same used in juju-core: see
# http://bazaar.launchpad.net/~go-bot/juju-core/trunk/view/head:/charm/url.go.
USER_PATTERN = r'[a-z0-9][a-zA-Z0-9+.-]+'
SERIES_PATTERN = r'[a-z]+(?:[a-z-]+[a-z])?'
NAME_PATTERN = r'[a-z][a-z0-9]*(?:-[a-z0-9]*[a-z][a-z0-9]*)*'

# Define the callables used to check if entity reference components are valid.
valid_user = re.compile(r'^{}$'.format(USER_PATTERN)).match
valid_name = re.compile(r'^{}$'.format(NAME_PATTERN)).match
valid_series = re.compile(r'^{}$'.format(SERIES_PATTERN)).match

# Compile the regular expression used to parse new jujucharms entity URLs.
_jujucharms_url_expression = re.compile(r"""
    ^  # Beginning of the line.
    (?:
        (?:{jujucharms})?  # Optional jujucharms.com URL.
        |
        /?  # Optional leading slash.
    )?
    (?:u/({user_pattern})/)?  # Optional user name.
    ({name_pattern})  # Bundle name.
    (?:/({series_pattern}))?  # Optional series.
    (?:/(\d+))?  # Optional bundle revision number.
    /?  # Optional trailing slash.
    $  # End of the line.
""".format(
    jujucharms=JUJUCHARMS_URL,
    name_pattern=NAME_PATTERN,
    series_pattern=SERIES_PATTERN,
    user_pattern=USER_PATTERN,
), re.VERBOSE)


@pyutils.string_class
class Reference(object):
    """Represent a charm or bundle URL reference."""

    def __init__(self, schema, user, series, name, revision):
        """Initialize the reference. Receives the URL fragments."""
        self.schema = schema
        self.user = user
        self.series = series
        self.name = name
        if revision is not None:
            revision = int(revision)
        self.revision = revision
        # XXX frankban 2015-02-26: remove the following attribute when
        # switching to the new bundle format, and when we have a better way
        # to increase bundle deployments count.
        self.charmworld_id = None

    @classmethod
    def from_string(cls, url):
        """Given an entity URL as a string, create and return a Reference.

        The given URL may be not fully qualified, meaning it can miss
        the schema (in which case "cs:" is inferred), the series
        (defaulting to "") and the revision (set to None if not specified).

        Raise a ValueError if the provided value is not a valid URL.
        """
        return cls(*_parse_url(url, fully_qualified=False))

    @classmethod
    def from_fully_qualified_url(cls, url):
        """Given an entity URL as a string, create and return a Reference.

        Fully qualified URLs represent the regular entity reference
        representation in Juju, e.g.: "cs:`~who/vivid/django-42" or
        "local:bundle/wordpress-0".

        Raise a ValueError if the provided value is not a valid and fully
        qualified URL, also including the schema and the revision.
        """
        return cls(*_parse_url(url, fully_qualified=True))

    @classmethod
    def from_jujucharms_url(cls, url):
        """Create and return a Reference from the given jujucharms.com URL.

        These are the preferred way to refer to a charm or bundle They
        basically look like the URL paths in jujucharms.com,
        e.g. "u/who/django", "mediawiki/42" or just "mediawiki". The full HTTP
        URL can be also provided, for instance "https://jujucharms.com/django".

        Raise a ValueError if the provided URL is not valid.
        """
        match = _jujucharms_url_expression.match(url)
        if match is None:
            msg = 'invalid bundle URL: {}'.format(url)
            raise ValueError(msg.encode('utf-8'))
        user, name, series, revision = match.groups()
        return cls('cs', user, series or 'bundle', name, revision)

    def __str__(self):
        """The string representation of a reference is its URL string."""
        return self.id()

    def __repr__(self):
        return '<Reference: {}>'.format(self)

    def __eq__(self, other):
        """Two refs are equal if they have the same string representation."""
        return isinstance(other, self.__class__) and self.id() == other.id()

    def path(self):
        """Return the reference as a string without the schema."""
        user = '~{}'.format(self.user) if self.user else ''
        name_revision = self.name
        if self.revision is not None:
            name_revision += '-{}'.format(self.revision)
        return '/'.join(filter(None, [user, self.series, name_revision]))

    def id(self):
        """Return the reference URL as a string."""
        return '{}:{}'.format(self.schema, self.path())

    def similar(self, other):
        """Report whether the other reference refers to a similar charm.

        Two references are considered similar if they share the same schema,
        user and name.
        Raise a TypeError if the given reference is not a Reference instance.
        """
        if not isinstance(other, self.__class__):
            msg = 'cannot compare unsupported type {}'.format(
                other.__class__.__name__)
            raise TypeError(msg.encode('utf-8'))
        return (
            (self.schema, self.user, self.name) ==
            (other.schema, other.user, other.name))

    def copy(self):
        """Copy this reference."""
        return self.__class__(
            self.schema, self.user, self.series, self.name, self.revision)

    def jujucharms_id(self):
        """Return the identifier of this reference in jujucharms.com."""
        user_part = 'u/{}/'.format(self.user) if self.user else ''
        series_part = '' if self.is_bundle() else '/{}'.format(self.series)
        revision_part = ''
        if self.revision is not None:
            revision_part = '/{}'.format(self.revision)
        return '{}{}{}{}'.format(
            user_part, self.name, series_part, revision_part)

    def jujucharms_url(self):
        """Return the URL where this entity lives in jujucharms.com."""
        return JUJUCHARMS_URL + self.jujucharms_id()

    def is_bundle(self):
        """Report whether this reference refers to a bundle entity."""
        return self.series == 'bundle'

    def is_local(self):
        """Return True if this refers to a local entity, False otherwise."""
        return self.schema == 'local'

    def is_fully_qualified(self):
        """Report whether this reference is fully qualified.

        A fully qualified reference includes its schema, series and revision.
        """
        return self.schema and self.series and (self.revision is not None)


def _parse_url(url, fully_qualified=False):
    """Parse the given charm or bundle URL, provided as a string.

    Return a tuple containing the entity reference fragments: schema, user,
    series, name and revision. Each fragment is a string except revision (int).

    Raise a ValueError with a descriptive message if the given URL is not
    valid. If fully_qualified is True, the URL must include the schema, series
    and revision, otherwise a ValueError is raised.
    """
    # Retrieve the schema.
    try:
        schema, remaining = url.split(':', 1)
    except ValueError:
        if fully_qualified:
            msg = 'URL has no schema: {}'.format(url)
            raise ValueError(msg.encode('utf-8'))
        schema = 'cs'
        remaining = url
    if schema not in ('cs', 'local'):
        msg = 'URL has invalid schema: {}'.format(schema)
        raise ValueError(msg.encode('utf-8'))
    # Retrieve the optional user, the series, name and revision.
    parts = remaining.split('/')
    parts_length = len(parts)
    if parts_length == 3:
        user, series, name_revision = parts
        if not user.startswith('~'):
            msg = 'URL has invalid user name form: {}'.format(user)
            raise ValueError(msg.encode('utf-8'))
        user = user[1:]
        if schema == 'local':
            msg = 'local entity URL with user name: {}'.format(url)
            raise ValueError(msg.encode('utf-8'))
    elif parts_length == 2:
        user_or_series, name_revision = parts
        if user_or_series.startswith('~'):
            user, series = user_or_series[1:], ''
        else:
            user, series = '', user_or_series
    elif (parts_length == 1) and (not fully_qualified):
        user = series = ''
        name_revision = parts[0]
    else:
        msg = 'URL has invalid form: {}'.format(url)
        raise ValueError(msg.encode('utf-8'))
    # Validate the user.
    if user and not valid_user(user):
        msg = 'URL has invalid user name: {}'.format(user)
        raise ValueError(msg.encode('utf-8'))
    # Validate the series.
    if series and not valid_series(series):
        msg = 'URL has invalid series: {}'.format(series)
        raise ValueError(msg.encode('utf-8'))
    # Validate name and revision.
    try:
        name, revision = name_revision.rsplit('-', 1)
    except ValueError:
        if fully_qualified:
            msg = 'URL has no revision: {}'.format(url)
            raise ValueError(msg.encode('utf-8'))
        name, revision = name_revision, None
    if revision is not None:
        try:
            revision = int(revision)
        except ValueError:
            if fully_qualified:
                msg = 'URL has invalid revision: {}'.format(revision)
                raise ValueError(msg.encode('utf-8'))
            name, revision = name + '-' + revision, None
    if not valid_name(name):
        msg = 'URL has invalid name: {}'.format(name)
        raise ValueError(msg.encode('utf-8'))

    return schema, user, series, name, revision
