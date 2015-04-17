#!/usr/bin/env python

# Copyright 2015 Canonical Ltd.
# Licensed under the AGPLv3, see LICENCE file for details.

from setuptools import (
    find_packages,
    setup,
)


PROJECT_NAME = 'jujubundlelib'
project = __import__(PROJECT_NAME)

with open('README.rst') as readme_file:
    readme = readme_file.read()

requirements = [
    'PyYAML==3.11',
]

test_requirements = [
    'tox',
]

setup(
    name=PROJECT_NAME,
    version=project.get_version(),
    description='A python library for working with Juju bundles',
    long_description=readme,
    author="Juju UI Team",
    author_email='juju-gui@lists.ubuntu.com',
    url='https://github.com/juju/juju-bundlelib',
    scripts=['getchangeset'],
    packages=find_packages(),
    include_package_data=True,
    install_requires=requirements,
    license="LGPL3",
    zip_safe=False,
    keywords='juju bundles',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)',
        'Natural Language :: English',
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
    ],
    test_suite='tests',
    tests_require=test_requirements,
)
