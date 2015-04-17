#!/bin/bash

APT_SYSDEPS="python-dev python-pip python-setuptools python-sphinx"
PIP_SYSDEPS="tox"
if [ -e `which apt-get` ] ; then
	apt-get install --yes $APT_SYSDEPS
else
	echo 'System dependencies can only be installed automatically on'
	echo 'systems with "apt-get". On OSX you can manually use Homebrew'
	echo 'if there are missing dependencies corresponding to the following'
	echo 'Debian packages:'
	echo $APT_SYSDEPS
fi
pip2 install $PIP_SYSDEPS
touch .sysdeps-installed
