FROM centos:7

RUN set -x  \
    && yum -y install \
       epel-release \
    && yum -y install \
       createrepo \
       python-pip

RUN set -x \
    && pip install \
       boto3


COPY *.py /mkrepo/
