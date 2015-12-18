=========
Packaging
=========

Use the following instructions to create Juju Bundle Lib Debian/Ubuntu packages
to be pushed in the Juju Stable PPA (``ppa:juju/stable``).

* Install the required packages::

    sudo apt-get install debhelper devscripts git python-setuptools ubuntu-dev-tools

* Set up your Debian environment variables, for instance::

    export DEBEMAIL=francesco.banconi@canonical.com
    export DEBFULLNAME="Francesco Banconi"

* Ensure your SSH and GPG keys for the user above are correctly set up in your
  machine. Check your ``~/.ssh`` and ``~/.gnupg`` directories.

* Retrieve the Juju Bundle Lib tarball from PyPI, e.g.::

    wget https://pypi.python.org/packages/source/j/jujubundlelib/jujubundlelib-0.1.7.tar.gz

* Rename the resulting archive, so that it can be used to create the packages::

    mv jujubundlelib-0.1.7.tar.gz jujubundlelib_0.1.7.orig.tar.gz

* Expand the archive::

    tar xvBf jujubundlelib_0.1.7.orig.tar.gz

* Clone the packaging repository, which includes the Debian files, inside the
  resulting directory::

    git clone git@github.com:juju/juju-bundlelib-packaging.git jujubundlelib-0.1.7/debian

* Update the package changelog, ensuring the version in the changelog reflects
  the PyPI one (in this examples it is 0.1.7) and the distribution is
  ubuntu+1 (wily atm)::

    cd jujubundlelib-0.1.7
    dch -v=0.1.7-1 --distribution=wily

* Commit your changes and push them to the master branch::

    cd debian
    git commit -a -m "Update for version 0.1.7" && git push

* Remove the git repository from the debian directory::

    rm -rf .git

* Build the package and sign it with your GPG key, for instance::

    cd ..
    debuild -S -kXXXXXXX

* Move back to the initial directory, where the dsc file has been created::

    cd ..

* Upload the package to the PPA, and wait for it to build::

    for release in `echo precise trusty vivid wily`; do
        backportpackage -u ppa:juju/stable -r -d "$release" -S "~ppa1" -y jujubundlelib_*.dsc
    done

* The building process can be followed at
  https://launchpad.net/~juju/+archive/ubuntu/stable/+packages
