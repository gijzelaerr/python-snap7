FROM ubuntu:20.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt update \
    && apt install -y software-properties-common python3-pip \
    && add-apt-repository ppa:gijzelaar/snap7 \
    && apt update \
    && apt install -y libsnap7-dev libsnap7-1
ADD . /code
WORKDIR /code
RUN pip3 install .
