FROM serverdensity/centos:6-i386
RUN yum install -y yum-plugin-ovl && yum clean all
RUN rpm -Uvh http://www.city-fan.org/ftp/contrib/yum-repo/rhel6/i386/city-fan.org-release-2-1.rhel6.noarch.rpm
RUN yum update -y
RUN yum install epel-release -y
RUN linux32 yum -y  --enablerepo=city-fan.org install yum-utils \
    rpm-build \
    redhat-rpm-config \
    make \
    gcc \
    python-devel \
    wget \
    curl \
    libyaml-devel \
    curl-devel \
    postgresql-devel \
    tar \
    symlinks \
    git \
    ca-certificates \
    python34 \
    python34-devel
RUN ( grep -q :20: /etc/group || groupadd -g 20 osx_staff ) && \
    ( grep -q :501: /etc/passwd || useradd -u 501 -g 20 osx_user ) && \
    ( grep -q :1000: /etc/group || groupadd -g 1000 ubuntu_group ) && \
    ( grep -q :1000: /etc/passwd || useradd  -u 1000 -g 1000 ubuntu_user )
COPY ./entrypoint.sh /
CMD ["/entrypoint.sh"]
