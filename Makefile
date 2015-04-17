# Copyright 2015 Canonical Ltd.
# Licensed under the AGPLv3, see LICENCE file for details.

PYTHON = python
APT_SYSDEPS = python-dev python-pip python-setuptools python-sphinx
# Since the python-tox package in Ubuntu uses Python 3, use pip to install tox
# instead. This also works on OSX where tox is not present in Homebrew.
PIP_SYSDEPS = tox

SYSDEPS_INSTALLED = .sysdeps-installed
DEVENV = devenv
DEVENVPIP = $(DEVENV)/bin/pip

.DEFAULT_GOAL := setup

$(DEVENVPIP):
	@tox -e devenv

$(SYSDEPS_INSTALLED): Makefile
	sudo sh ./sysdeps.sh

.PHONY: check
check: setup
	@tox -e lint
	@tox

.PHONY: clean
clean:
	$(PYTHON) setup.py clean
	# Remove the development environments.
	rm -rfv $(DEVENV) .tox/
	# Remove distribution artifacts.
	rm -rfv *.egg build/ dist/ jujubundlelib.egg-info MANIFEST
	# Remove tests artifacts.
	rm -fv .coverage
	# Remove the sysdeps canary file.
	rm -fv $(SYSDEPS_INSTALLED)
	# Remove Python compiled bytecode.
	find . -name '*.pyc' -delete
	find . -name '__pycache__' -type d -delete

.PHONY: docs
docs: setup
	$(MAKE) -C docs html

.PHONY: help
help:
	@echo -e 'Juju Bundle Lib - list of make targets:\n'
	@echo 'make - Set up the development and testing environment.'
	@echo 'make test - Run tests.'
	@echo 'make lint - Run linter and pep8.'
	@echo 'make check - Run all the tests and lint in all supported scenarios.'
	@echo 'make source - Create source package.'
	@echo 'make clean - Get rid of bytecode files, build and dist dirs, venvs.'
	@echo 'make release - Register and upload a release on PyPI.'
	@echo -e '\nAfter creating the development environment with "make", it is'
	@echo 'also possible to do the following:'
	@echo '- run a specific subset of the test suite, e.g. with'
	@echo '  "$(DEVENV)/bin/nosetests jujubundlelib/tests/...";'
	@echo '- use tox as usual on this project;'
	@echo '  see https://tox.readthedocs.org/en/latest/'


.PHONY: lint
lint: setup
	@$(DEVENV)/bin/flake8 --ignore E731 --show-source jujubundlelib

.PHONY: release
release: check
	$(PYTHON) setup.py register sdist upload

.PHONY: setup
setup: $(SYSDEPS_INSTALLED) $(DEVENVPIP) setup.py

.PHONY: source
source:
	$(PYTHON) setup.py sdist

.PHONY: sysdeps
sysdeps: $(SYSDEPS_INSTALLED)

.PHONY: test
test: setup
	@$(DEVENV)/bin/nosetests \
		--verbosity 2 --with-coverage --cover-erase \
		--cover-package jujubundlelib
