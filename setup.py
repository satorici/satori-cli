#!/usr/bin/env python3
from setuptools import setup, find_packages


setup(
    name='satori-ci',
    version='1.0',
    license='MIT',
    author="Satori CI",
    author_email='info@satori-ci.com',
    #packages=find_packages('classes'),
    package_dir={'main_package': 'src'},
    url='https://github.com/satorici/satori-cli',
    keywords='Satori CI CLI',
    install_requires=[
          'scikit-learn',
          'certifi>=2022.9.24',
          'charset-normalizer>=2.1.1',
          'idna>=3.4',
          'PyYAML>=6.0',
          'requests>=2.28.1',
          'urllib3>=1.26.12'
      ],

)
