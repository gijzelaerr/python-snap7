Installation
============

here you can find out how to install python-snap7 on your system.

Snap7
-----

To use python-snap7 you need to have the snap7 library installed.

Ubuntu
~~~~~~

If you are using Ubuntu you can use the Ubuntu packages from our
`launchpad PPA <https://launchpad.net/~gijzelaar/+archive/snap7>`_. To install::

    $ sudo sudo add-apt-repository ppa:gijzelaar/snap7
    $ sudo apt-get update
    $ sudo apt-get install snap71 snap7-dev

Compile from source
~~~~~~~~~~~~~~~~~~~

If you are not using Ubuntu or if you want to have more control you can
download the latest source from
`the sourceforce page <http://sourceforge.net/projects/snap7/files/>`_ and do
a manual compile. Download the file and run::

     $ p7zip -d snap7-full-1.0.0.7z  # requires the p7 program
     $ cd build/<platform>           # where platform is unix or windows
     $ make -f <arch>.mk             # where arch is your architecture, for example x86_64_linux

For more information about or help with compilation please check out the
documentation on the `snap7 website <http://snap7.sourceforge.net/>`_.

snap7-python
------------

python-snap7 is available on `PyPI <https://pypi.python.org>`_. You can install
it by using pip::

  $ pip install python-snap7

You can also install it from the git repository or from a source tarball::

  $ python ./setup.py install

