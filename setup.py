from setuptools import setup

import os
import os
_scripts_dir = os.path.dirname(os.path.realpath(__file__))
_requirements_file = os.path.join(_scripts_dir, "requirements.txt")
_readme_file = os.path.join(_scripts_dir, "README.md")

with open(_readme_file, 'r') as file:
    _readme = file.read()

with open(_requirements_file) as f:
    _requirements = f.read().splitlines()

setup(
    name='swjas',
    author='Francesco Zoccheddu',
    version='0.0.5',
    description='Simple WSGI JSON API Server',
    long_description=_readme,
    long_description_content_type='text/markdown',
    url='https://github.com/francescozoccheddu/swjas',
    license='MIT',
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
    ],
    packages=['swjas'],
    install_requires=_requirements
)
