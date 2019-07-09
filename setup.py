from setuptools import setup

import os
_ROOT_PATH = os.path.dirname(os.path.realpath(__file__))
_README_PATH = os.path.join(_ROOT_PATH, "README.md")
with open(_README_PATH, 'r') as file:
    _README = file.read()

setup(
    name='swjas',
    author='Francesco Zoccheddu',
    version='0.0.3',
    description='Simple WSGI JSON API Server',
    long_description=_README,
    long_description_content_type='text/markdown',
    url='https://github.com/francescozoccheddu/swjas',
    license='MIT',
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
    ],
    packages=['swjas'],
)