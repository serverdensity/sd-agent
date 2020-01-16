FROM centos:8

RUN yum -y install yum-utils
RUN yum-config-manager --enable PowerTools
RUN yum -y install yum-utils rpm-build redhat-rpm-config make gcc python2-devel wget curl curl-devel postgresql-devel tar python2

RUN ( grep -q :20: /etc/group || groupadd -g 20 osx_staff ) && \
    ( grep -q :501: /etc/passwd || useradd -u 501 -g 20 osx_user ) && \
    ( grep -q :1000: /etc/group || groupadd -g 1000 ubuntu_group ) && \
    ( grep -q :1000: /etc/passwd || useradd  -u 1000 -g 1000 ubuntu_user )
COPY ./entrypoint.sh /
CMD ["/entrypoint.sh"]
