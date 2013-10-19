from distutils.core import setup

setup(name='snap7',
      version='0.1',
      description='Python wrapper for the snap7 library',
      author='Gijs Molenaar',
      author_email='gijs@pythonic.nl',
      url='https://github.com/gijzelaerr/python-snap7',
      packages=['snap7'],
      license='MIT licence, see LICENCE',
      long_description=open('README.rst').read(),
      scripts=['snap7/bin/snap7-server.py'],
)

