#!/usr/bin/env python

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


setup(
    name = 'apfmon',
    version = '1.0',
    description = 'Webapp to monitor APF activity',
    author = 'Peter Love',
    url='https://github.com/ptrlv/apfmon',
    zip_safe=False,
    packages = ['api', 'kit', 'mon']
    license = 'ALv2',
)

