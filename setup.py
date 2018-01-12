from distutils.core import setup
from Cython.Build import cythonize

# Note:
#   - For packaging, see http://www.diveintopython3.net/packaging.html
#   - Calculate version by using https://www.pakin.org/~scott/ltver.html

setup(
        name = "rpi-vcsm",
        packages = ["rpi_vcsm"],
        version = "1.0.1",
        description = "VideoCore Shared Memory (VCSM) driver for Raspberry Pi",
        author = "Sugizaki Yukimasa",
        author_email = "ysugi@idein.inc",
        url = "https://github.com/Idein/rpi-vcsm",
        ext_modules = cythonize("rpi_vcsm/buffer.pyx"),
)
