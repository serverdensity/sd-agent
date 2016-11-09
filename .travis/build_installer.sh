#!/bin/bash
set -ev

if [ "${TRAVIS_OS_NAME}" == "osx" ]; then

    # Only run on default flavor.
    ./packaging/darwin/build_installer.sh

else

    bundle install
    bundle package
    # Needed if no cache exists
    mkdir -p $INTEGRATIONS_DIR
    ls -al $INTEGRATIONS_DIR
    rake ci:run
    ls -al $INTEGRATIONS_DIR

fi
