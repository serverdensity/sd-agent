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
RUN yum -y install python34 python34-devel
RUN ( grep -q :20: /etc/group || groupadd -g 20 osx_staff ) && \
    ( grep -q :501: /etc/passwd || useradd -u 501 -g 20 osx_user ) && \
    ( grep -q :1000: /etc/group || groupadd -g 1000 ubuntu_group ) && \
    ( grep -q :1000: /etc/passwd || useradd  -u 1000 -g 1000 ubuntu_user )
COPY ./entrypoint.sh /
CMD ["/entrypoint.sh"]
