
from setuptools import setup

setup(
    name='rpi-vcsm',
    packages=[
        'rpi_vcsm',
    ],
    version='3.0.0',
    install_requires=[
        'ioctl-opt ~= 1.2',
    ],
    description='A library for the VCSM (VideoCore Shared Memory service) and VCSM-CMA (contiguous memory allocator) kernel drivers',
    author='Yukimasa Sugizaki',
    author_email='ysugi@idein.jp',
    url='https://github.com/Idein/rpi-vcsm',
)
