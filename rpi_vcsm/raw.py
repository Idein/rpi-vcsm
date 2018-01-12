"""VideoCore Shared Memory (VCSM) driver for Raspberry Pi"""

import os
from fcntl import ioctl
from ctypes import Structure, c_char, c_uint, c_uint8, c_uint16, c_uint32, \
                   c_void_p
from ioctl_opt import IOR


class raw(object):

    MAGIC = ord('I')
    CMD_ALLOC                   = 0x5a
    CMD_LOCK                    = 0x5c
    CMD_UNLOCK                  = 0x5e
    CMD_FREE                    = 0x61
    CMD_MAPPED_VC_ADDR_FROM_HDL = 0x6a
    CMD_CLEAN_INVALID2          = 0x70

    OP_NOP              = 0
    OP_INVALIDATE       = 1
    OP_CLEAN            = 2
    OP_CLEAN_INVALIDATE = 3

    class st_alloc(Structure):
        _fields_ = [
                # user -> kernel
                ('size', c_uint),
                ('num', c_uint),
                ('cached', c_uint),
                ('name', c_char * 32),
                # kernel -> user
                ('handle', c_uint),
        ]
        pass

    class st_free(Structure):
        _fields_ = [
                # user -> kernel
                ('handle', c_uint),
        ]
        pass

    class st_lock_unlock(Structure):
        _fields_ = [
                # user -> kernel
                ('handle', c_uint),
                # kernel -> user
                ('addr', c_uint),
        ]
        pass

    class st_size(Structure):
        _fields_ = [
                # user -> kernel
                ('handle', c_uint),
                # kernel -> user
                ('size', c_uint),
        ]
        pass

    class st_map(Structure):
        _fields_ = [
                # user -> kernel
                ('pid', c_uint),
                ('handle', c_uint),
                ('addr', c_uint),
                # kernel -> user
                ('size', c_uint),
        ]
        pass

    class st_clean_invalid2(Structure):
        class st_clean_invalid_block(Structure):
            _fields_ = [
                    ('invalidate_mode', c_uint16),
                    ('block_count', c_uint16),
                    ('start_address', c_void_p),
                    ('block_size', c_uint32),
                    ('inter_block_stride', c_uint32),
            ]
            pass

        _fields_ = [
                # user -> kernel
                ('op_count', c_uint8),  # Must be 1 for now... Sigh...
                ('zero', c_uint8 * 3),
                ('s', st_clean_invalid_block),
        ]
        pass

    IOCTL_ALLOC              = IOR(MAGIC, CMD_ALLOC,
                                   st_alloc)
    IOCTL_LOCK               = IOR(MAGIC, CMD_LOCK,
                                   st_lock_unlock)
    IOCTL_UNLOCK             = IOR(MAGIC, CMD_UNLOCK,
                                   st_lock_unlock)
    IOCTL_FREE               = IOR(MAGIC, CMD_FREE,
                                   st_free)
    IOCTL_MAP_VC_ADDR_FR_HDL = IOR(MAGIC, CMD_MAPPED_VC_ADDR_FROM_HDL,
                                   st_map)
    # Dirty hack! No more zero-sized arrays I hope!
    IOCTL_CLEAN_INVALID2     = IOR(MAGIC, CMD_CLEAN_INVALID2,
                                   c_uint8 * 4)


    def __init__(self):
        self.fd = os.open('/dev/vcsm', os.O_NONBLOCK | os.O_RDWR)

    def close(self):
        if self.fd:
            os.close(self.fd)
        self.fd = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        return exc_value is None


    def alloc(self, size, num, cached, name):
        s = self.st_alloc(
                size = size,
                num = num,
                cached = cached,
                name = bytes(name, 'ascii')
        )
        ioctl(self.fd, self.IOCTL_ALLOC, s)
        return s.handle

    def lock(self, handle):
        s = self.st_lock_unlock(
                handle = handle
        )
        ioctl(self.fd, self.IOCTL_LOCK, s)
        return s.addr

    def unlock(self, handle):
        s = self.st_lock_unlock(
                handle = handle
        )
        ioctl(self.fd, self.IOCTL_UNLOCK, s)

    def free(self, handle):
        s = self.st_free(
                handle = handle
        )
        ioctl(self.fd, self.IOCTL_FREE, s)

    def map_vc_addr_fr_hdl(self, handle):
        s = self.st_map(
                pid = os.getpid(),
                handle = handle
        )
        ioctl(self.fd, self.IOCTL_MAP_VC_ADDR_FR_HDL, s)
        return s.addr

    def clean_invalid2(self, op, usr_ptr, block_count, block_size, stride):
        s = self.st_clean_invalid2(
                op_count = 1,
                s = self.st_clean_invalid2.st_clean_invalid_block(
                        invalidate_mode = op,
                        block_count = block_count,
                        start_address = usr_ptr,
                        block_size = block_size,
                        inter_block_stride = stride
                )
        )
        ioctl(self.fd, self.IOCTL_CLEAN_INVALID2, s)
