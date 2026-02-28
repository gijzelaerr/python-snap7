FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive

LABEL org.opencontainers.image.source=https://github.com/gijzelaerr/python-snap7
LABEL org.opencontainers.image.description="Pure Python S7 communication library for interfacing with Siemens S7 PLCs."
LABEL org.opencontainers.image.licenses=MIT

RUN apt update \
    && apt install -y python3-pip python3-venv
ADD . /code
WORKDIR /venv
RUN python3 -m venv /venv
RUN . /venv/bin/activate
RUN /venv/bin/pip install /code
