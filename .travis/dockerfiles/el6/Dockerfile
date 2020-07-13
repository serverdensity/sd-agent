FROM centos:6
RUN yum -y install \
    yum-utils \
    rpm-build \
    redhat-rpm-config \
    make \
    gcc \
    wget \
    curl \
    libyaml-devel \
    curl-devel \
    postgresql-devel \
    tar \
    symlinks \
    epel-release
RUN wget https://repo.ius.io/ius-release-el6.rpm && \
    rpm -Uvh ius-release*.rpm && \
    yum -y install python27 python27-devel  --enablerepo=ius-archive --disablerepo=ius
RUN ( grep -q :20: /etc/group || groupadd -g 20 osx_staff ) && \
    ( grep -q :501: /etc/passwd || useradd -u 501 -g 20 osx_user ) && \
    ( grep -q :1000: /etc/group || groupadd -g 1000 ubuntu_group ) && \
    ( grep -q :1000: /etc/passwd || useradd  -u 1000 -g 1000 ubuntu_user )
COPY ./entrypoint.sh /
CMD ["/entrypoint.sh"]
