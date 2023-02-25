FROM ubuntu:20.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
    && apt-get install -y software-properties-common python3-pip \
    && add-apt-repository ppa:gijzelaar/snap7 \
    && apt-get update \
    && apt-get install -y libsnap7-dev libsnap7-1
ADD . /code
WORKDIR /code
RUN pip3 install .
