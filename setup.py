#!/usr/bin/env pyhon3

from setuptools import setup, find_packages

setup(
    name='neonmeate',
    version='1.0',
    packages=find_packages(),
    entry_points={'console_scripts': ['neonmeate=neonmeate.main:main']},
    url='https://github.com/jnj/NeonMeate/',
    license='BSD',
    author='Josh Joyce',
    author_email='jnjoyce@pobox.com',
    description='A graphical client for mpd',
    install_requires=[
        'python-mpd2>=1.1.0',
        'pycairo>=1.16.2'
    ]
)
