FROM amazonlinux:2017.09-with-sources

RUN yum update -y \
    && yum install -y \
    python35 \
    python35-setuptools

RUN easy_install-3.5 pip
RUN mkdir /lambda_env
