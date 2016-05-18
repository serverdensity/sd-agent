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
Requires: python >= 2.6, sysstat, libyaml, initscripts
BuildRequires: symlinks
License: Simplified BSD
Group: System/Monitoring
Source: %{name}-%{version}.tar.gz
URL: http://www.serverdensity.com/


BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root

%description
%{longdescription}

%prep
curl -LO https://pypi.python.org/packages/source/v/virtualenv/virtualenv-13.1.2.tar.gz
tar xzf virtualenv-13.1.2.tar.gz
python virtualenv-13.1.2/virtualenv.py %{__venv}

%setup -qn sd-agent
%{__venv}/bin/python %{__venv}/bin/pip install -r requirements.txt
%{__venv}/bin/python %{__venv}/bin/pip install -r requirements-opt.txt

%build
%{__venv}/bin/python setup.py build
%{__venv}/bin/python setup.py install
%include %{_topdir}/inc/fix_virtualenv

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

%preun
if [ $1 = 0 ] ; then
    /sbin/service sd-agent stop >/dev/null 2>&1
    /sbin/chkconfig --del /etc/init.d/sd-agent
    rm /etc/init.d/sd-agent
    rm -rf /var/log/sd-agent/
    rm -rf /var/run/sd-agent/
fi

%include %{_topdir}/inc/files
%include %{_topdir}/inc/subpackages
%include %{_topdir}/inc/changelog
