#!/usr/bin/env python
# coding: utf-8

import os
from setuptools import setup, find_packages

version = '0.1.0'


def read(filename: str) -> str:
    with open(os.path.join(os.path.dirname(__file__), filename)) as f:
        return f.read()


setup(
    name='blogme',
    version=version,
    author='jachinlin',
    author_email='linjx1000@gmail.com',
    url='https://github.com/jachinlin/blogme',
    description='blogme',
    long_description=read('README.md'),
    long_description_content_type='text/markdown',
    license='MIT',
    classifiers=[
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3 :: Only'
    ],
    keywords='blog',
    packages=find_packages(exclude=['examples', 'tests']),
    package_data={'blogme': ['templates/*', 'templates/blog/*', 'static/*']},
    install_requires=[
        'PyYAML', 'jinja2', 'docutils', 'babel',
        'werkzeug', 'blinker', 'pygments', 'markdown'
    ],
    entry_points={
        'console_scripts': [
            'blogme = blogme.__main__:main',
        ],
    }
)

