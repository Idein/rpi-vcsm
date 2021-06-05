# rpi-vcsm

A Python library for the VCSM (VideoCore Shared Memory service) and VCSM-CMA
(contiguous memory allocator) kernel drivers of Raspberry Pi.


## Requirements

This driver opens `/dev/vcsm-cma` or `/dev/vcsm`, which are the official devices
for the VCSM and VCSM-CMA, respectively.
The owner of the devices are usually `root.video`, and the permission is set as
`rw-rw----`, so you need to belong to `video` group or need to be `root` user.
If you choose the former, run the command below (re-login to take effect).

```bash
sudo usermod --append --groups video $USER
```


## Installation

```shell
$ sudo apt update
$ sudo apt install python3-pip git
$ python3 -m pip install --user -U pip setuptools wheel
$ python3 -m pip install --user git+https://github.com/Idein/rpi-vcsm.git
```


## Testing

```shell
$ sudo apt update
$ sudo apt install python3-pip git
$ python3 -m pip install --user -U pip setuptools wheel
$ git clone https://github.com/Idein/rpi-vcsm.git
$ cd rpi-vcsm/
$ python3 setup.py egg_info
$ python3 -m pip install --user -r rpi_vcsm.egg-info/requires.txt
$ python3 -m unittest -v tests/*.py
```
