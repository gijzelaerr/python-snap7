import os

from setuptools import setup, find_packages, Extension

__version__ = "1.1"

tests_require = ['pytest', 'pytest-asyncio', 'mypy', 'pycodestyle', 'types-setuptools']

extras_require = {
    'test': tests_require,
    'doc': ['sphinx', 'sphinx_rtd_theme'],
}

ext_modules = []
if os.environ.get('BUILD_WHEEL_WITH_EXTENSION'):
    ext_modules = [
        Extension(
            "snap7.__dummy__",
            ["dummy.c"],
            libraries=['snap7'],
            include_dirs=['/usr/lib', '/usr/local/lib', 'src'],
        ),
    ]


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name='python-snap7',
    version=__version__,
    description='Python wrapper for the snap7 library',
    author='Gijs Molenaar',
    author_email='gijs@pythonic.nl',
    url='https://github.com/gijzelaerr/python-snap7',
    packages=find_packages(),
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
    ext_modules=ext_modules,
)
