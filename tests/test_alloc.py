
import unittest

import rpi_vcsm.VCSM


class Test(unittest.TestCase):

    def test_alloc(self):

        with rpi_vcsm.VCSM.VCSM() as vcsm:
            size = 32000000

            handle, bus_ptr, usr_ptr, usr_buf = \
                vcsm.malloc_cache(size=size, cached=rpi_vcsm.CACHE_NONE,
                                  name='test')

            print('size = 0x%08x' % size)
            print('handle  = 0x%08x' % handle)
            print('bus_ptr = 0x%08x' % bus_ptr)
            print('usr_ptr = 0x%08x' % usr_ptr)

            vcsm.clean(handle=handle, usr_ptr=usr_ptr, size=size)
            vcsm.invalidate(handle=handle, usr_ptr=usr_ptr, size=size)
            vcsm.clean(handle=handle, usr_ptr=usr_ptr, size=size)
            vcsm.invalidate(handle=handle, usr_ptr=usr_ptr, size=size)
            vcsm.clean(handle=handle, usr_ptr=usr_ptr, size=size)
            vcsm.invalidate(handle=handle, usr_ptr=usr_ptr, size=size)

            vcsm.free(handle=handle, usr_buf=usr_buf)
