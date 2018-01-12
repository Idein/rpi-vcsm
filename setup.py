from distutils.core import setup

# Note:
#   - For packaging, see http://www.diveintopython3.net/packaging.html
#   - Calculate version by using https://www.pakin.org/~scott/ltver.html

setup(
        name = "rpi-vcsm",
        packages = ["rpi_vcsm"],
        version = "2.0.0",
        description = "VideoCore Shared Memory (VCSM) driver for Raspberry Pi",
        author = "Sugizaki Yukimasa",
        author_email = "ysugi@idein.inc",
        url = "https://github.com/Idein/rpi-vcsm",
)
