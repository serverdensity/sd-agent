#!/bin/bash
set -ev

if [[ "$TRAVIS_TAG" ]]; then
    PACKAGES_DIR="/${TRAVIS_REPO_SLUG}/${TRAVIS_TAG}/"
else
    PACKAGES_DIR="/${TRAVIS_REPO_SLUG}/${TRAVIS_BUILD_ID}/"
fi
# Build requisites
#PATH=~/Library/Python/2.7/bin:$PATH

BUILD_DIR=/tmp/build
INSTALL_DIR=/tmp/installation
DEST_VENV=/usr/local/sd-agent/
DARWIN_SCRIPTS=packaging/darwin
PLUGIN_REPO_DIR=${TRAVIS_BUILD_DIR}sd-agent-core-plugins

source ${DARWIN_SCRIPTS}/darwin_version.sh
PKG_NAME="Server Density Agent Installer ${AGENT_VERSION}.pkg"

VENV_PYTHON_CMD="${BUILD_DIR}/bin/python"
VENV_PIP_CMD="${BUILD_DIR}/bin/pip"

# Prepare virtual environment
# macOS needs pip 9.0.3+, which is shipped with virtualenv 15.2.0 - https://stackoverflow.com/a/49748494
mkdir -p ${BUILD_DIR}
curl -LO https://pypi.python.org/packages/source/v/virtualenv/virtualenv-15.2.0.tar.gz
tar xzf virtualenv-15.2.0.tar.gz
/usr/bin/python3 virtualenv-15.2.0/virtualenv.py --no-site-packages --no-pip --no-setuptools ${BUILD_DIR}
curl -LO https://bootstrap.pypa.io/ez_setup.py
${VENV_PYTHON_CMD} ez_setup.py
curl -LO https://bootstrap.pypa.io/get-pip.py
${VENV_PYTHON_CMD} get-pip.py

$VENV_PIP_CMD install -r requirements.txt
PIP_COMMAND=${VENV_PIP_CMD} ./utils/pip-allow-failures.sh requirements-opt.txt
${VENV_PYTHON_CMD} setup.py build
${VENV_PYTHON_CMD} setup.py install

# Fix venv activate paths.
sed -i ".bak" "s|^VIRTUAL_ENV=.*|VIRTUAL_ENV=${DEST_VENV}|" ${BUILD_DIR}/bin/activate
sed -i "'.bak'" "s|^setenv VIRTUAL_ENV.*|setenv VIRTUAL_ENV ${DEST_VENV}|" ${BUILD_DIR}/bin/activate.csh
sed -i "'.bak'" "s|^set -gx VIRTUAL_ENV.*|set -gx VIRTUAL_ENV ${DEST_VENV}|" ${BUILD_DIR}/bin/activate.fish

# Fix venv shebangs
grep -l -r -e '^#!.*bin/\(env \)\?\(python\|pypy\|ipy\|jython\)' ${BUILD_DIR}/bin | xargs sed -i ".bak" 's|^#!.*bin/\(env \)\?.*|#!$(DEST_VENV)/bin/python|'
sed -i ".bak" 's|^#!.*bin/\(env \)\?.*|#!$(DEST_VENV)/bin/python|' agent.py

# Remove backup files
rm -f ${BUILD_DIR}/bin/*.bak

# Setup and copy plugins.
git clone https://github.com/serverdensity/sd-agent-core-plugins.git ${PLUGIN_REPO_DIR}

cd ${PLUGIN_REPO_DIR}

bundle install
export conf_dir=conf.d
export checks_dir=checks.d
export merge_requirements_to=.
rake copy_checks
PIP_COMMAND=${VENV_PIP_CMD} ${TRAVIS_BUILD_DIR}/utils/pip-allow-failures.sh check_requirements.txt

cd ${TRAVIS_BUILD_DIR}

mkdir -p ${INSTALL_DIR}/sd-agent/checks.d
mkdir -p ${INSTALL_DIR}/etc/sd-agent/conf.d
cp ${PLUGIN_REPO_DIR}/checks.d/* ${INSTALL_DIR}/sd-agent/checks.d
rm -rf ${PLUGIN_REPO_DIR}/conf.d/auto_conf
cp ${PLUGIN_REPO_DIR}/conf.d/* ${INSTALL_DIR}/etc/sd-agent/conf.d

mkdir -p ${INSTALL_DIR}/etc/sd-agent
cp config.cfg.example ${INSTALL_DIR}/etc/sd-agent/config.cfg
cp plugins.cfg.example ${INSTALL_DIR}/etc/sd-agent/plugins.cfg


# Copy main agent code.
mkdir -p ${INSTALL_DIR}/sd-agent
mkdir -p ${INSTALL_DIR}/sd-agent/lib/python3/site-packages
cp agent.py \
aggregator.py \
config.py \
daemon.py \
sdagent.py \
emitter.py \
graphite.py \
modules.py \
sd-cert.pem \
transaction.py \
jmxfetch.py \
util.py ${INSTALL_DIR}/sd-agent

cp -R utils ${INSTALL_DIR}/sd-agent/utils
cp -R checks ${INSTALL_DIR}/sd-agent/checks

# Copy the files to the install dir.

cp -a ${BUILD_DIR}/.Python ${INSTALL_DIR}/sd-agent/
cp -a ${BUILD_DIR}/bin ${INSTALL_DIR}/sd-agent/
cp -a ${BUILD_DIR}/include ${INSTALL_DIR}/sd-agent/
cp -a ${BUILD_DIR}/lib/python3*/*.py ${INSTALL_DIR}/sd-agent/lib/python3
cp -a ${BUILD_DIR}/lib/python3*/distutils ${INSTALL_DIR}/sd-agent/lib/python3
cp -a ${BUILD_DIR}/lib/python3*/encodings ${INSTALL_DIR}/sd-agent/lib/python3
cp -a ${BUILD_DIR}/lib/python3*/lib-dynload ${INSTALL_DIR}/sd-agent/lib/python3
cp -a ${BUILD_DIR}/lib/python3*/no-global-site-packages.txt ${INSTALL_DIR}/sd-agent/lib/python3
cp -a ${BUILD_DIR}/lib/python3*/orig-prefix.txt ${INSTALL_DIR}/sd-agent/lib/python3
cp -a ${BUILD_DIR}/lib/python3*/site-packages/* ${INSTALL_DIR}/sd-agent/lib/python3/site-packages
#cp -a ${BUILD_DIR}/lib/python3*/site-packages/backports* ${INSTALL_DIR}/sd-agent/lib/python3*/site-packages
#cp -a ${BUILD_DIR}/lib/python3*/site-packages/boto* ${INSTALL_DIR}/sd-agent/lib/python3*/site-packages
#cp -a ${BUILD_DIR}/lib/python3*/site-packages/*consul* ${INSTALL_DIR}/sd-agent/lib/python3*/site-packages
#cp -a ${BUILD_DIR}/lib/python3*/site-packages/dns* ${INSTALL_DIR}/sd-agent/lib/python3*/site-packages
#cp -a ${BUILD_DIR}/lib/python3*/site-packages/docker* ${INSTALL_DIR}/sd-agent/lib/python3*/site-packages
#cp -a ${BUILD_DIR}/lib/python3*/site-packages/easy-install* ${INSTALL_DIR}/sd-agent/lib/python3*/site-packages
#cp -a ${BUILD_DIR}/lib/python3*/site-packages/*etcd* ${INSTALL_DIR}/sd-agent/lib/python3*/site-packages
#cp -a ${BUILD_DIR}/lib/python3*/site-packages/ipaddress.py* ${INSTALL_DIR}/sd-agent/lib/python3*/site-packages
#cp -a ${BUILD_DIR}/lib/python3*/site-packages/_markerlib ${INSTALL_DIR}/sd-agent/lib/python3*/site-packages
#cp -a ${BUILD_DIR}/lib/python3*/site-packages/meld3* ${INSTALL_DIR}/sd-agent/lib/python3*/site-packages
#cp -a ${BUILD_DIR}/lib/python3*/site-packages/ntplib* ${INSTALL_DIR}/sd-agent/lib/python3*/site-packages
#cp -a ${BUILD_DIR}/lib/python3*/site-packages/pip* ${INSTALL_DIR}/sd-agent/lib/python3*/site-packages
#cp -a ${BUILD_DIR}/lib/python3*/site-packages/pkg_resources ${INSTALL_DIR}/sd-agent/lib/python3*/site-packages
#cp -a ${BUILD_DIR}/lib/python3*/site-packages/psutil* ${INSTALL_DIR}/sd-agent/lib/python3*/site-packages
#cp -a ${BUILD_DIR}/lib/python3*/site-packages/pycurl* ${INSTALL_DIR}/sd-agent/lib/python3*/site-packages
#cp -a ${BUILD_DIR}/lib/python3*/site-packages/PyYAML* ${INSTALL_DIR}/sd-agent/lib/python3*/site-packages
#cp -a ${BUILD_DIR}/lib/python3*/site-packages/requests* ${INSTALL_DIR}/sd-agent/lib/python3*/site-packages
#cp -a ${BUILD_DIR}/lib/python3*/site-packages/*scandir* ${INSTALL_DIR}/sd-agent/lib/python3*/site-packages
#cp -a ${BUILD_DIR}/lib/python3*/site-packages/sd_agent* ${INSTALL_DIR}/sd-agent/lib/python3*/site-packages
#cp -a ${BUILD_DIR}/lib/python3*/site-packages/setuptools* ${INSTALL_DIR}/sd-agent/lib/python3*/site-packages
#cp -a ${BUILD_DIR}/lib/python3*/site-packages/simplejson* ${INSTALL_DIR}/sd-agent/lib/python3*/site-packages
#cp -a ${BUILD_DIR}/lib/python3*/site-packages/six.py ${INSTALL_DIR}/sd-agent/lib/python3*/site-packages
#cp -a ${BUILD_DIR}/lib/python3*/site-packages/six-*-info ${INSTALL_DIR}/sd-agent/lib/python3*/site-packages
#cp -a ${BUILD_DIR}/lib/python3*/site-packages/tornado* ${INSTALL_DIR}/sd-agent/lib/python3*/site-packages
#cp -a ${BUILD_DIR}/lib/python3*/site-packages/uptime* ${INSTALL_DIR}/sd-agent/lib/python3*/site-packages
#cp -a ${BUILD_DIR}/lib/python3*/site-packages/urllib3* ${INSTALL_DIR}/sd-agent/lib/python3*/site-packages
#cp -a ${BUILD_DIR}/lib/python3*/site-packages/websocket* ${INSTALL_DIR}/sd-agent/lib/python3*/site-packages
#cp -a ${BUILD_DIR}/lib/python3*/site-packages/yaml ${INSTALL_DIR}/sd-agent/lib/python3*/site-packages

# Copy startup item
cp ${DARWIN_SCRIPTS}/com.serverdensity.agent.plist ${INSTALL_DIR}/sd-agent

# Package it up
pkgbuild --identifier com.serverdensity.agent-service \
--version ${AGENT_VERSION} \
--install-location "/usr/local/" \
--scripts ${DARWIN_SCRIPTS}/scripts \
--ownership recommended \
--root ${INSTALL_DIR} \
--component-plist ${DARWIN_SCRIPTS}/AgentComponents.plist \
"Server Density Agent Service.pkg"

# TODO: Package a preference pane as a separate component
mkdir -p diskimage

if [ ! -z "${DARWIN_INSTALLER_CN}" ]; then
    # Retrieve signing key from Travis environment and add it to a new default keychain
    echo ${DARWIN_INSTALLER_KEY} | base64 -D -o ServerDensity.p12
    KEYCHAIN_NAME=agent.keychain
    security create-keychain -p travis ${KEYCHAIN_NAME}
    security default-keychain -s ${KEYCHAIN_NAME}
    security unlock-keychain -p travis
    security set-keychain-settings -t 3600 -u
    security import ServerDensity.p12 -f pkcs12 -P "" -k ${KEYCHAIN_NAME} -T /usr/bin/productbuild
    security set-key-partition-list -S apple-tool:,apple: -s -k travis ${KEYCHAIN_NAME}
    # this may help when debugging, lists the known identities:
    security find-identity
    productbuild --distribution ${DARWIN_SCRIPTS}/distribution.xml \
        --identifier com.serverdensity.agent \
        --resources ${DARWIN_SCRIPTS}/Resources \
        --sign "${DARWIN_INSTALLER_CN}" \
        diskimage/"${PKG_NAME}"
    # Trust, but verify
    spctl --assess --type install diskimage/"${PKG_NAME}"
else
    echo "Signing disabled..."
    productbuild --distribution ${DARWIN_SCRIPTS}/distribution.xml \
        --identifier com.serverdensity.agent \
        --resources ${DARWIN_SCRIPTS}/Resources \
        diskimage/"${PKG_NAME}"
fi

# Add the icon
${DARWIN_SCRIPTS}/scripts/setIcon.py ${DARWIN_SCRIPTS}/Resources/sd-agent-installer.icns diskimage/"${PKG_NAME}"
if [ ! -d "$PACKAGES_DIR" ]; then
    sudo mkdir -p "$PACKAGES_DIR"/macOS
fi
# Package the disk image
# This may fail sometimes due to a "Resource busy" error, in that case re-running the job usually fixes it
hdiutil create -srcfolder diskimage -volname "Agent Installer" "sd-agent-${AGENT_VERSION}.dmg"

sudo cp sd-agent-${AGENT_VERSION}.dmg "$PACKAGES_DIR"/macOS/sd-agent-${AGENT_VERSION}.dmg

sudo find "$PACKAGES_DIR"
