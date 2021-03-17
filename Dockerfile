FROM ubuntu:20.04
RUN apt-get update
RUN apt-get install -y software-properties-common python3-pip
RUN add-apt-repository ppa:gijzelaar/snap7
RUN apt-get update
RUN apt-get install -y libsnap7-dev libsnap7-1
ADD . /code
WORKDIR /code
RUN pip3 install .
