FROM amazonlinux:2017.09

RUN yum update -y \
    && yum install -y \
    python36 \
    python36-setuptools

RUN easy_install-3.6 pip
RUN mkdir /lambda_env
