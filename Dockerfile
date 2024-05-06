FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive

LABEL org.opencontainers.image.source=https://github.com/gijzelaerr/python-snap7
LABEL org.opencontainers.image.description="The snap7 library is used to communicate with Siemens S7 PLCs. This is a Python wrapper for the snap7 library."
LABEL org.opencontainers.image.licenses=MIT

RUN apt update \
    && apt install -y software-properties-common python3-pip \
    && add-apt-repository ppa:gijzelaar/snap7 \
    && apt update \
    && apt install -y libsnap7-dev libsnap7-1
ADD . /code
WORKDIR /code
RUN pip3 install .
