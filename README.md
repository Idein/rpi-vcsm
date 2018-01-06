# rpi-vcsm

A Python driver for VideoCore Shared Memory (VCSM) of Raspberry Pi.


## Requirements

```
Cython
ioctl-opt>=1.2
```

This driver opens `/dev/vcsm`, which is a official kernel device of VCSM.  The
owner of the device is `root.video` and the permission is `rw-rw----`, so you
need to belong to `video` group *or* use `sudo` to use this driver.


## Installation

```
$ pip install -r requirements.txt
$ git clone https://github.com/Idein/rpi-vcsm.git
$ cd rpi-vcsm/
$ sudo python setup.py install
```

You may need to update your Raspberry Pi firmware to use full functionality of
this driver:

```
$ sudo rpi-update
```


## Testing

```
$ sudo pip install nose
$ python setup.py build_ext --inplace
$ nosetests -v -s
```
