#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Copyright (c) 2022 Javier Escalada Gómez
All rights reserved.
License: BSD 3-Clause Clear License (see LICENSE for details)
"""

from setuptools import setup, find_packages
from pathlib import Path
from litterateur import __version__, __author__, __email__, __license__, __doc__

base = Path(__file__).parent
long_description = (base / "README.md").read_text()

setup(
    name="litterateur",
    version=__version__,
    url="https://github.com/Kerrigan29a/litterateur",
    project_urls={
        "Source": "https://github.com/Kerrigan29a/litterateur",
    },
    author=__author__,
    author_email=__email__,
    description=__doc__,
    long_description=long_description,
    long_description_content_type="text/markdown",

    install_requires=[],
    license='BSD 3-Clause Clear License',
    entry_points={
        'console_scripts': [
            'litterateur=litterateur:main',
        ],
    },
    # From https://pypi.org/classifiers/
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: End Users/Desktop",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3 :: Only",
        "Topic :: Utilities",
    ],
    platforms="any",
    keywords=["literate programming", "weaver", "tangler", "markdown"],
)
