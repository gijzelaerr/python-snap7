Binary Wheel Installation
=========================

We advice you to install python-snap7 using a binary wheel. The binary wheels
should work on Windows 64x, OS X (intel), Linux x64 and Linux ARM.
python-snap7 is available on `PyPI <https://pypi.python.org/pypi/python-snap7/>`_. You can install
it by using pip::

  $ pip install python-snap7

 If you want to use the CLI interface for running an emulator, you should install it with::

  $ pip install "python-snap7[cli]"


Manual Installation (not recommended)
=====================================

If you are running an unsupported platform you need to do a bit more work.
This involves two steps. First, install the snap7 library,
followed by the installation of the python-snap7 package.

Snap7
-----

Ubuntu
~~~~~~

If you are using Ubuntu you can use the Ubuntu packages from our
`launchpad PPA <https://launchpad.net/~gijzelaar/+archive/snap7>`_. To install::

    $ sudo add-apt-repository ppa:gijzelaar/snap7
    $ sudo apt-get update
    $ sudo apt-get install libsnap7-1 libsnap7-dev

Windows
~~~~~~~

Download the zip file from the
`sourceforce page <https://sourceforge.net/projects/snap7/files/>`_.
Unzip the zip file, and copy ``release\\Windows\\Win64\\snap7.dll`` somewhere
in your system PATH, for example ``%systemroot%\System32\``. Alternatively you can
copy the file somewhere on your file system and adjust the system PATH.

OSX
~~~

The snap7 library is available on `Homebrew <https://brew.sh/>`_::

  $ brew install snap7


Compile from source
~~~~~~~~~~~~~~~~~~~

Download the latest source from
`the sourceforce page <https://sourceforge.net/projects/snap7/files/>`_ and do
a manual compile. Download the file and run::

     $ p7zip -d snap7-full-1.0.0.7z  # requires the p7 program
     $ cd build/<platform>           # where platform is unix or windows
     $ make -f <arch>.mk install     # where arch is your architecture, for example x86_64_linux

For more information about or help with compilation please check out the
documentation on the `snap7 website <https://snap7.sourceforge.net/>`_.


Python-Snap7
------------

Once snap7 is available in your library or system path, you can install it from the git
repository or from a source tarball. It is recommended to install it in a virtualenv.

To create a virtualenv and activate it::

  $ python3 -m venv venv
  $ source venv/bin/activate

Now you can install your python-snap7 package::

  $ pip3 install .
