import os

from setuptools import setup, find_packages, Extension
from sys import platform

__version__ = "0.11"

tests_require = ['pytest', 'pytest-asyncio', 'mypy', 'pycodestyle']

extras_require = {
    'test': tests_require,
    'doc': ['sphinx', 'sphinx_rtd_theme'],
}


# this is an empty module just here to trick the binary wheel helper tools
# to include the snap7 shared library
dummy = Extension('snap7.__dummy__', libraries=['snap7'], sources=['dummy.c'])


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


if platform == 'win32':
    package_data = {"monetdbe": ["*.dll"]}
else:
    package_data = {}


setup(
    name='python-snap7',
    version=__version__,
    description='Python wrapper for the snap7 library',
    author='Gijs Molenaar',
    author_email='gijs@pythonic.nl',
    url='https://github.com/gijzelaerr/python-snap7',
    packages=find_packages(),
    ext_modules=[dummy],
    license='MIT licence',
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
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
    python_requires='>=3.6',
    extras_require=extras_require,
    tests_require=tests_require,
    test_suite="tests",
    package_data=package_data,
)
