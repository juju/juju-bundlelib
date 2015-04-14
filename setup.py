#!/usr/bin/env python
# -*- coding: utf-8 -*-


from setuptools import (
    find_packages,
    setup,
)


PROJECT_NAME = 'jujubundlelib'

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
    version='0.1.0',
    description='A python library for working with Juju bundles',
    long_description=readme,
    author="Juju UI Team",
    author_email='juju-gui@lists.ubuntu.com',
    url='https://github.com/juju/juju-bundlelib',
    packages=find_packages(),
    package_dir={PROJECT_NAME: []},
    include_package_data=True,
    install_requires=requirements,
    license="LGPL3",
    zip_safe=False,
    keywords='juju bundles',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: LGPL3 License',
        'Natural Language :: English',
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
    ],
    test_suite='tests',
    tests_require=test_requirements,
)
