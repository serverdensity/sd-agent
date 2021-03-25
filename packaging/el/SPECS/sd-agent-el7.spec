# SO references
# http://stackoverflow.com/questions/880227/what-is-the-minimum-i-have-to-do-to-create-an-rpm-file

# Init script references
# http://fedoraproject.org/wiki/Packaging/SysVInitScript#InitscriptScriptlets

%define        __spec_install_post %{nil}
%define          debug_package %{nil}
%define        __os_install_post %{_dbpath}/brp-compress
%global        __venv %{_tmppath}/venv
%global          longdescription %include description
%global        __sd_python_version 2.7

Summary: Server Density Monitoring Agent
Name: sd-agent
BuildArch: x86_64 i386
%include %{_topdir}/inc/version
%include %{_topdir}/inc/release
Requires: python >= 2.7, sysstat, libyaml, %{name}-forwarder, %{name}-sd-cpu-stats, %{name}-network, %{name}-disk
Conflicts: %{name}-ssh-check <= 2.3.0
BuildRequires: symlinks
License: Simplified BSD
Group: System/Monitoring
Source: %{name}-%{version}.tar.gz
URL: http://www.serverdensity.com/


BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root

%description
%{longdescription}

%prep
curl -LO https://raw.github.com/pypa/virtualenv/1.11.6/virtualenv.py
python2.7 virtualenv.py --no-site-packages --no-pip --no-setuptools %{__venv}
curl -LO https://bootstrap.pypa.io/ez_setup.py
%{__venv}/bin/python ez_setup.py --version="44.1.1"
curl -LO https://bootstrap.pypa.io/pip/2.7/get-pip.py
%{__venv}/bin/python get-pip.py

%setup -qn sd-agent
%{__venv}/bin/python %{__venv}/bin/pip install -r requirements.txt
PYCURL_SSL_LIBRARY=nss %{__venv}/bin/python %{__venv}/bin/pip install -r requirements-opt.txt

%build
%include %{_topdir}/inc/fix_virtualenv
%include %{_topdir}/inc/download_jmx_fetch
%include %{_topdir}/inc/install

%clean
rm -rf %{buildroot}

%post
chmod +x /etc/init.d/sd-agent
getent group sd-agent > /dev/null || groupadd -r sd-agent
getent passwd sd-agent > /dev/null || useradd -r -g sd-agent -d /usr/bin/sd-agent/ -s /bin/bash -c "Server Density Agent User" sd-agent
mkdir -p /var/log/sd-agent/
mkdir -p /var/run/sd-agent/
chown -R sd-agent:sd-agent /var/log/sd-agent/
chown -R sd-agent:sd-agent /var/run/sd-agent/
chown -R sd-agent:sd-agent /etc/sd-agent/
chown -R sd-agent:sd-agent /etc/sd-agent/config.cfg
chmod 0660 /etc/sd-agent/config.cfg
chown -R sd-agent:sd-agent /etc/sd-agent/plugins.cfg
chmod 0660 /etc/sd-agent/plugins.cfg
/sbin/chkconfig --add sd-agent
/etc/init.d/sd-agent restart

%pre
case "$1" in
  2)
    /sbin/service sd-agent stop >/dev/null 2>&1
  ;;
esac

%preun
case "$1" in
  0)
    /sbin/service sd-agent stop >/dev/null 2>&1
    /sbin/chkconfig --del /etc/init.d/sd-agent
    rm /etc/init.d/sd-agent
    rm -rf /var/log/sd-agent/
    rm -rf /var/run/sd-agent/
  ;;
esac

%include %{_topdir}/inc/files
%include %{_topdir}/inc/subpackages
%include %{_topdir}/inc/changelog
