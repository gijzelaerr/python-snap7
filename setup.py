import os
from setuptools import setup, find_packages

__version__ = "0.11"


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(name='python-snap7',
      version=__version__,
      description='Python wrapper for the snap7 library',
      author='Gijs Molenaar',
      author_email='gijs@pythonic.nl',
      url='https://github.com/gijzelaerr/python-snap7',
      packages=find_packages(),
      license='MIT licence, see LICENCE',
      long_description=read('README.rst'),
      scripts=['snap7/bin/snap7-server.py'],
      classifiers=[
          "Development Status :: 5 - Production/Stable",
          "Environment :: Console",
          "Topic :: System :: Hardware",
          "Intended Audience :: Developers",
          "Intended Audience :: Manufacturing",
          "License :: OSI Approved :: MIT License",
          "Operating System :: POSIX",
          "Programming Language :: Python :: 2.7",
          "Programming Language :: Python :: 3.4",
          "Programming Language :: Python :: 3.5",
          "Programming Language :: Python :: 3.6",
          "Programming Language :: Python :: 3.7",
          "Programming Language :: Python :: 3.8",
      ]
      )
