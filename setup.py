import os
from distutils.core import setup
from snap7 import __version__

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(name='python-snap7',
      version=__version__,
      description='Python wrapper for the snap7 library',
      author='Gijs Molenaar',
      author_email='gijs@pythonic.nl',
      url='https://github.com/gijzelaerr/python-snap7',
      packages=['snap7'],
      license='MIT licence, see LICENCE',
      long_description=read('README.rst'),
      scripts=['snap7/bin/snap7-server.py'],
)

