FROM ubuntu:18.04
MAINTAINER gijs@pythonic.nl
ENV DEBIAN_FRONTEND noninteractive

# copy source to container
ADD . /snap7

# install ubuntu packages
RUN apt-get update
RUN apt-get install -y software-properties-common python-software-properties python-nose

# add the snap7 launchpad PPA
RUN add-apt-repository ppa:gijzelaar/snap7
RUN apt-get update

# install snap7
RUN apt-get install libsnap7-dev libsnap71
RUN ldconfig

# install python-snap7
RUN cd /snap7 && python ./setup.py install

#RUN cd /snap7 && ./run_tests.sh
