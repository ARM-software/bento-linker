
from distutils.core import setup

setup(
    name='bento',
    version='0.1dev',
    packages=['bento'],
    install_requires=[
        'toml>=0.10'
    ],
    python_requires='>=3.6',
    #long_description=open('README.md').read()
    entry_points={
        'console_scripts': [
            'bento=bento.__main__:main'
        ]
    })
