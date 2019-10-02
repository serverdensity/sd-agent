#!/bin/bash -xe

cat > $HOME/.rpmmacros << EOF_MACROS
%_topdir /root/el
%_tmppath %{_topdir}/tmp
EOF_MACROS

mkdir /root/el
cd /root/el
for dir in SOURCES BUILD RPMS SRPMS; do
    [ -d $dir ] || mkdir $dir
done
sd_agent_version=$(awk -F'"' '/^AGENT_VERSION/ {print $2}' /sd-agent/config.py)
tar -czf /root/el/SOURCES/sd-agent-${sd_agent_version}.tar.gz /sd-agent
cp -a /sd-agent/packaging/el/{SPECS,inc,description} /root/el
cd /root/el
chown -R `id -u`:`id -g` /root/el
function build {
    rpmdir=/root/build/result/$1
    yum-builddep -y SPECS/sd-agent-$1.spec
    rpmbuild -ba SPECS/sd-agent-$1.spec --define="_build_id_links none" && \
    (test -d $rpmdir || mkdir -p $rpmdir) && cp -a /root/el/RPMS/* $rpmdir
}
build "el8"
if [ ! -d /packages/el ]; then
    mkdir /packages/el
fi

if [ ! -d /packages/el/8 ]; then
    mkdir /packages/el/8
fi

if [ ! -d /packages/src ]; then
    mkdir /packages/src
fi
cp -r /root/el/RPMS/* /packages/el/8
cp -r /root/el/SRPMS/* /packages/src
