
import unittest

import rpi_vcsm.VCSM


class Test(unittest.TestCase):

    def test_alloc(self):

        with rpi_vcsm.VCSM.VCSM() as vcsm:
            size = 32000000

            handle, bus, usr, buf = vcsm.malloc_cache(size, rpi_vcsm.CACHE_NONE,
                                                      None)

            print('size=0x%08x' % size)
            print('Got handle:               0x%08x' % handle)
            print('Got bus address:          0x%08x' % bus)
            print('Got user virtual address: 0x%08x' % usr)

            vcsm.clean(usr, size)
            vcsm.invalidate(usr, size)
            vcsm.clean(usr, size)
            vcsm.invalidate(usr, size)
            vcsm.clean(usr, size)
            vcsm.invalidate(usr, size)

            vcsm.free(handle, buf)
