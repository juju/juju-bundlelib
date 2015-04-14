from __future__ import unicode_literals

import json
import sys

import yaml

from src import changeset


def main():
    """Dump the changeset objects as JSON, reading the bundle YAML in from
    stdin or a given file.
    """
    source = sys.stdin
    if len(sys.argv) == 2:
        source = open(sys.argv[1])
    bundle = yaml.safe_load(source)
    print '['
    for num, change in enumerate(changeset.parse(bundle)):
        if num:
            print ','
        print json.dumps(change)
    print ']'


if __name__ == '__main__':
    main()
