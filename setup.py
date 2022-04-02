from setuptools import setup, find_packages
from litterateur import __version__

setup(
    name='litterateur',
    version=__version__,
    url='https://github.com/Kerrigan29a/litterateur.git',
    author='Javier Escalada Gómez',
    author_email='kerrigan29a@gmail.com',
    description='Quick-and-dirty "literate programming" tool to extract code from Markdown files',
    packages=find_packages(),    
    install_requires=[],
    license='Unlicense',
    entry_points={
        'console_scripts': [
            'litterateur=litterateur:main',
        ],
    },
)
