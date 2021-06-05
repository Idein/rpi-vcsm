
'''
A library for the VCSM (VideoCore shared memory service) and VCSM-CMA
(contiguous memory allocator) kernel drivers.

Different licenses are applied to each class depending on the original program,
so consult the comments in the head of it.

There is a dedicated official library named user-vcsm for them, but it is not
built for AArch64 for now due to compatibility issues, so we currently implement
ioctls for the drivers.

The plain VCSM driver has been disabled since the rpi-5.9.y kernel, and this
library at first attempts to use VCSM-CMA, which is the same behavior as the
user-vcsm library.
Users can provide an option to force which driver to use.

Raspberry Pi splits the main memory into two parts on boot, and the plain VCSM
driver allocates a memory in the GPU-side memory area.
The split size is determined by the gpu_mem= configuration in config.txt.
On the other hand, the VCSM-CMA driver allocates a memory in the CPU-side CMA,
of which size is determined by the dtoverlay= configurations in config.txt (e.g.
dtoverlay=vc4-kms-v3d,cma-192).

References:
- https://github.com/raspberrypi/userland/issues/688
- https://github.com/raspberrypi/userland/tree/master/host_applications/linux/libs/sm
- https://www.raspberrypi.org/documentation/configuration/config-txt/memory.md
- https://github.com/raspberrypi/linux/blob/rpi-5.10.y/arch/arm/boot/dts/overlays/README
'''


from abc import ABC, abstractmethod
from ctypes import addressof, Structure, c_byte, c_char, c_uint, c_uint8, c_uint16, c_int32, c_uint32, c_uint64, c_void_p
from fcntl import ioctl
import mmap
import os
import resource

from ioctl_opt import IOR, IOW

from . import *


class dma_buf:

    '''
    Methods and constants for the dma-buf subsystem.

    Copyright (c) 2015 Intel Ltd.

    This program is free software; you can redistribute it and/or modify it
    under the terms of the GNU General Public License version 2 as published by
    the Free Software Foundation.

    This program is distributed in the hope that it will be useful, but WITHOUT
    ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
    FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
    more details.

    You should have received a copy of the GNU General Public License along with
    this program.  If not, see <http://www.gnu.org/licenses/>.

    References:
    - https://github.com/raspberrypi/linux/blob/rpi-5.10.y/include/uapi/linux/dma-buf.h
    '''

    __MAGIC = ord('b')
    __CMD_SYNC = 0

    SYNC_READ = 1 << 0
    SYNC_WRITE = 2 << 0
    SYNC_RW = SYNC_READ | SYNC_WRITE
    SYNC_START = 0 << 2
    SYNC_END = 1 << 2

    class __st_sync(Structure):
        _fields_ = [
            ('flags', c_uint64),
        ]

    __IOCTL_SYNC = IOW(__MAGIC, __CMD_SYNC, __st_sync)

    @staticmethod
    def ioctl_sync(*, fd, flags):
        s = dma_buf.__st_sync(flags=flags)
        ioctl(fd, dma_buf.__IOCTL_SYNC, s)


class raw(ABC):

    @staticmethod
    def align(u, a):
        assert isinstance(u, int) and u >= 0
        assert isinstance(a, int) and a >= 1
        return (u + (a - 1)) & ~(a - 1)

    @abstractmethod
    def __init__(self):
        pass

    @abstractmethod
    def close(self):
        pass

    @abstractmethod
    def alloc(self, *, size, cached, name):
        pass

    @abstractmethod
    def free(self, *, handle, usr_buf):
        pass

    @abstractmethod
    def clean_invalid():  # Arguments differ from each class.
        pass


class raw_vcsm(raw):

    '''
    Methods and constants for the plain (non-CMA) VCSM kernel driver.

    Copyright (c) 2011 Broadcom Corporation. All rights reserved.

    Unless you and Broadcom execute a separate written software license
    agreement governing use of this software, this software is licensed to you
    under the terms of the GNU General Public License version 2, available at
    http://www.broadcom.com/licenses/GPLv2.php (the "GPL").

    Notwithstanding the above, under no circumstances may you combine this
    software in any way with any other Broadcom software provided under a
    license other than the GPL, without Broadcom's express prior written
    consent.

    Copyright (c) 2012 Broadcom Europe Ltd.

    Redistribution and use in source and binary forms, with or without
    modification, are permitted provided that the following conditions are met:
        * Redistributions of source code must retain the above copyright
          notice, this list of conditions and the following disclaimer.
        * Redistributions in binary form must reproduce the above copyright
          notice, this list of conditions and the following disclaimer in the
          documentation and/or other materials provided with the distribution.
        * Neither the name of the copyright holder nor the
          names of its contributors may be used to endorse or promote products
          derived from this software without specific prior written permission.

    THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
    ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
    WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
    DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY
    DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
    (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
    LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
    ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
    (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
    SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

    References:
    - https://github.com/raspberrypi/linux/blob/rpi-5.8.y/include/linux/broadcom/vmcs_sm_ioctl.h
    - https://github.com/raspberrypi/userland/blob/master/host_applications/linux/libs/sm/user-vcsm.c
    '''

    __MAGIC = ord('I')

    __CMD_ALLOC = 0x5a
    __CMD_LOCK = 0x5c
    __CMD_UNLOCK = 0x5e
    __CMD_FREE = 0x61
    __CMD_MAPPED_VC_ADDR_FROM_HDL = 0x6a
    __CMD_CLEAN_INVALID2 = 0x70

    class __st_alloc(Structure):
        _fields_ = [
            # user -> kernel
            ('size', c_uint),
            ('num', c_uint),
            ('cached', c_uint),
            ('name', c_char * 32),
            # kernel -> user
            ('handle', c_uint),
        ]

    class __st_free(Structure):
        _fields_ = [
            # user -> kernel
            ('handle', c_uint),
        ]

    class __st_lock_unlock(Structure):
        _fields_ = [
            # user -> kernel
            ('handle', c_uint),
            # kernel -> user
            ('addr', c_uint),
        ]

    class __st_map(Structure):
        _fields_ = [
            # user -> kernel
            ('pid', c_uint),
            ('handle', c_uint),
            ('addr', c_uint),
            # kernel -> user
            ('size', c_uint),
        ]

    class __st_clean_invalid2(Structure):
        class st_clean_invalid_block(Structure):
            _fields_ = [
                ('invalidate_mode', c_uint16),
                ('block_count', c_uint16),
                ('start_address', c_void_p),
                ('block_size', c_uint32),
                ('inter_block_stride', c_uint32),
            ]

        _fields_ = [
            # user -> kernel
            ('op_count', c_uint8),  # Must be 1 for now.
            ('zero', c_uint8 * 3),
            ('s', st_clean_invalid_block),
        ]

    __IOCTL_ALLOC = IOR(__MAGIC, __CMD_ALLOC, __st_alloc)
    __IOCTL_LOCK = IOR(__MAGIC, __CMD_LOCK, __st_lock_unlock)
    __IOCTL_UNLOCK = IOR(__MAGIC, __CMD_UNLOCK, __st_lock_unlock)
    __IOCTL_FREE = IOR(__MAGIC, __CMD_FREE, __st_free)
    __IOCTL_MAP_VC_ADDR_FR_HDL = IOR(__MAGIC, __CMD_MAPPED_VC_ADDR_FROM_HDL,
                                     __st_map)
    __IOCTL_CLEAN_INVALID2 = IOR(__MAGIC, __CMD_CLEAN_INVALID2,
                                 __st_clean_invalid2)

    def __ioctl_alloc(self, *, size, num, cached, name):
        s = self.__st_alloc(size=size, num=num, cached=cached, name=name)
        ioctl(self.__fd, self.__IOCTL_ALLOC, s)
        return s.handle

    def __ioctl_lock(self, *, handle):
        s = self.__st_lock_unlock(handle=handle)
        ioctl(self.__fd, self.__IOCTL_LOCK, s)
        return s.addr

    def __ioctl_unlock(self, *, handle):
        s = self.__st_lock_unlock(handle=handle)
        ioctl(self.__fd, self.__IOCTL_UNLOCK, s)
        return s.addr

    def __ioctl_free(self, *, handle):
        s = self.__st_free(handle=handle)
        ioctl(self.__fd, self.__IOCTL_FREE, s)

    def __ioctl_map_vc_addr_fr_hdl(self, *, pid, handle):
        s = self.__st_map(pid=pid, handle=handle)
        ioctl(self.__fd, self.__IOCTL_MAP_VC_ADDR_FR_HDL, s)
        return s.addr

    def __ioctl_clean_invalid2(self, *, invalidate_mode, block_count,
                               start_address, block_size, inter_block_stride):
        s = self.__st_clean_invalid2(
            op_count=1,
            s=self.__st_clean_invalid2.st_clean_invalid_block(
                invalidate_mode=invalidate_mode, block_count=block_count,
                start_address=start_address, block_size=block_size,
                inter_block_stride=inter_block_stride))
        ioctl(self.__fd, self.__IOCTL_CLEAN_INVALID2, s)

    def __init__(self, *, path=None):
        if path is None:
            path = '/dev/vcsm'
        self.__fd = os.open(path, os.O_NONBLOCK | os.O_RDWR)

    def close(self):
        os.close(self.__fd)
        del self.__fd

    def alloc(self, *, size, cached, name):
        size = self.align(size, resource.getpagesize())
        name = bytes(name, 'ascii')

        handle = self.__ioctl_alloc(size=size, num=1, cached=cached, name=name)

        usr_buf = mmap.mmap(fileno=self.__fd, length=size,
                            flags=mmap.MAP_SHARED,
                            prot=mmap.PROT_READ | mmap.PROT_WRITE,
                            offset=handle)

        usr_ptr = self.__ioctl_lock(handle=handle)

        bus_ptr = self.__ioctl_map_vc_addr_fr_hdl(pid=os.getpid(),
                                                  handle=handle)

        return handle, bus_ptr, usr_ptr, usr_buf

    def free(self, *, handle, usr_buf):
        usr_buf.close()
        self.__ioctl_unlock(handle=handle)
        self.__ioctl_free(handle=handle)

    def clean_invalid(self, *, op, usr_ptr, size):
        self.__ioctl_clean_invalid2(invalidate_mode=op, block_count=1,
                                    start_address=usr_ptr, block_size=size,
                                    inter_block_stride=0)


class raw_vcsm_cma(raw):

    '''
    Methods and constants for the VCSM-CMA kernel driver.

    Copyright (c) 2019 Raspberry Pi (Trading) Ltd. All rights reserved.

    This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; version 2.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program; if not, write to the Free Software
    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

    Copyright (c) 2012 Broadcom Europe Ltd.

    Redistribution and use in source and binary forms, with or without
    modification, are permitted provided that the following conditions are met:
        * Redistributions of source code must retain the above copyright
          notice, this list of conditions and the following disclaimer.
        * Redistributions in binary form must reproduce the above copyright
          notice, this list of conditions and the following disclaimer in the
          documentation and/or other materials provided with the distribution.
        * Neither the name of the copyright holder nor the
          names of its contributors may be used to endorse or promote products
          derived from this software without specific prior written permission.

    THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
    ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
    WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
    DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY
    DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
    (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
    LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
    ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
    (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
    SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

    References:
    - https://github.com/raspberrypi/linux/blob/rpi-5.10.y/drivers/staging/vc04_services/include/linux/broadcom/vc_sm_cma_ioctl.h
    - https://github.com/raspberrypi/userland/blob/master/host_applications/linux/libs/sm/user-vcsm.c
    '''

    __MAGIC = ord('J')
    __CMD_ALLOC = 0x5a
    __CMD_CLEAN_INVALID2 = 0x5c

    class __st_alloc(Structure):
        _fields_ = [
            # user -> kernel
            ('size', c_uint32),
            ('num', c_uint32),
            ('cached', c_uint32),
            ('pad', c_uint32),
            ('name', c_char * 32),
            # kernel -> user
            ('handle', c_int32),
            ('vc_handle', c_uint32),
            ('dma_addr', c_uint64),
        ]

    class __st_clean_invalid2(Structure):
        class st_clean_invalid_block(Structure):
            _fields_ = [
                ('invalidate_mode', c_uint32),
                ('block_count', c_uint32),
                ('start_address', c_void_p),
                ('block_size', c_uint32),
                ('inter_block_stride', c_uint32),
            ]

        _fields_ = [
            # user -> kernel
            ('op_count', c_uint32),  # Must be 1 for now.
            ('pad', c_uint32),
            ('s', st_clean_invalid_block),
        ]

    __IOCTL_ALLOC = IOR(__MAGIC, __CMD_ALLOC, __st_alloc)
    __IOCTL_CLEAN_INVALID2 = IOR(__MAGIC, __CMD_CLEAN_INVALID2,
                                 __st_clean_invalid2)

    def __ioctl_alloc(self, *, size, num, cached, pad, name):
        s = self.__st_alloc(size=size, num=num, cached=cached, pad=pad,
                            name=name)
        ioctl(self.__fd, self.__IOCTL_ALLOC, s)
        return s.handle, s.vc_handle, s.dma_addr

    def __init__(self, *, path=None):
        if path is None:
            path = '/dev/vcsm-cma'
        self.__fd = os.open(path, os.O_NONBLOCK | os.O_RDWR)

    def close(self):
        os.close(self.__fd)
        del self.__fd

    def alloc(self, *, size, cached, name):
        size_aligned = self.align(size, resource.getpagesize())
        name = bytes(name, 'ascii')

        handle, vc_handle, bus_ptr = self.__ioctl_alloc(size=size_aligned,
                                                        num=1, cached=cached,
                                                        pad=0, name=name)
        assert 0 <= bus_ptr < 2 ** 32

        usr_buf = mmap.mmap(fileno=handle, length=size, flags=mmap.MAP_SHARED,
                            prot=mmap.PROT_READ | mmap.PROT_WRITE, offset=0)

        dma_buf.ioctl_sync(fd=handle,
                           flags=dma_buf.SYNC_START | dma_buf.SYNC_RW)

        # The reference to this intermediate buffer is immediately removed, but
        # as long as the usr_buf is living, the memory address does not change.
        usr_ptr = addressof(c_byte.from_buffer(usr_buf))

        return handle, bus_ptr, usr_ptr, usr_buf

    def free(self, *, handle, usr_buf):
        dma_buf.ioctl_sync(fd=handle, flags=dma_buf.SYNC_END | dma_buf.SYNC_RW)
        usr_buf.close()
        os.close(handle)

    def clean_invalid(self, *, op, handle):
        if op == CACHE_OP_NOP:
            return
        elif op == CACHE_OP_INVALIDATE:
            flags = dma_buf.SYNC_START | dma_buf.SYNC_RW
        elif op == CACHE_OP_CLEAN or op == CACHE_OP_FLUSH:
            flags = dma_buf.SYNC_END | dma_buf.SYNC_RW
        dma_buf.ioctl_sync(fd=handle, flags=flags)


class VCSM:

    def __init__(self, *, force=None, path_vcsm=None, path_vcsm_cma=None):
        assert force in [None, 'vcsm', 'vcsm-cma']

        try:
            if force != 'vcsm':
                self.raw = raw_vcsm_cma(path=path_vcsm_cma)
        except FileNotFoundError as e:
            if force == 'vcsm-cma':
                raise e

        if not hasattr(self, 'raw'):
            self.raw = raw_vcsm(path=path_vcsm)

    def close(self):
        self.raw.close()
        del self.raw

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        return exc_value is None

    def get_driver(self):
        return 'vcsm' if isinstance(self.raw, raw_vcsm) else 'vcsm-cma'

    def malloc_cache(self, *, size, cached, name):
        return self.raw.alloc(size=size, cached=cached, name=name)

    def free(self, *, handle, usr_buf):
        self.raw.free(handle=handle, usr_buf=usr_buf)

    def clean_invalidate(self, *, op, handle=None, usr_ptr=None, size=None):
        if isinstance(self.raw, raw_vcsm):
            assert usr_ptr is not None
            assert size is not None
            self.raw.clean_invalid(op=op, usr_ptr=usr_ptr, size=size)
        else:
            assert handle is not None
            self.raw.clean_invalid(op=op, handle=handle)

    def invalidate(self, *, handle=None, usr_ptr=None, size=None):
        self.clean_invalidate(op=CACHE_OP_INVALIDATE, handle=handle,
                              usr_ptr=usr_ptr, size=size)

    def clean(self, *, handle=None, usr_ptr=None, size=None):
        self.clean_invalidate(op=CACHE_OP_CLEAN, handle=handle,
                              usr_ptr=usr_ptr, size=size)
