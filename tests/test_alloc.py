
from time import monotonic
import random
import sys
import unittest

import rpi_vcsm.VCSM


class Test(unittest.TestCase):

    def test_alloc(self):

        print()

        with rpi_vcsm.VCSM.VCSM() as vcsm:
            size = 32000000

            print('Driver:', vcsm.get_driver())

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

    def test_speed(self, *, size=2 ** 20):

        cached_to_str = {
            rpi_vcsm.CACHE_NONE: 'none',
            rpi_vcsm.CACHE_HOST: 'host',
            rpi_vcsm.CACHE_VC: 'vc',
            rpi_vcsm.CACHE_BOTH: 'both',
        }

        print()

        for force in ['vcsm', 'vcsm-cma']:
            try:
                vcsm = rpi_vcsm.VCSM.VCSM(force=force)
            except FileNotFoundError:
                print('Skipping driver', force)
                continue
            for cached in [rpi_vcsm.CACHE_NONE, rpi_vcsm.CACHE_HOST,
                           rpi_vcsm.CACHE_VC, rpi_vcsm.CACHE_BOTH]:
                with self.subTest(force=force, cached=cached):
                    handle, bus_ptr, usr_ptr, usr_buf = \
                        vcsm.malloc_cache(size=size, cached=cached,
                                          name='test')

                    # warmup
                    usr_buf.read()
                    usr_buf.seek(0)

                    src = b'\x5a' * size

                    start = monotonic()
                    usr_buf.write(src)
                    t_write = monotonic() - start

                    usr_buf.seek(0)

                    start = monotonic()
                    dst = usr_buf.read()
                    t_read = monotonic() - start

                    self.assertEqual(src, dst)

                    vcsm.free(handle=handle, usr_buf=usr_buf)

                    print('driver = %-8s,' % force,
                          'cached = %-4s:' % cached_to_str[cached],
                          'read =', size / t_read * 1e-6, 'MB/s,',
                          'write =', size / t_write * 1e-6, 'MB/s')

            vcsm.close()

    def test_random(self, *, maxsize=65536, n=100):

        # random.randbytes() is introduced in Python 3.9.
        def randbytes(n):
            return random.getrandbits(8 * n).to_bytes(n, sys.byteorder)

        with rpi_vcsm.VCSM.VCSM() as vcsm:

            mem_list = []
            random.seed(42)

            for i in range(n):
                size = random.randint(1, maxsize)
                handle, bus_ptr, usr_ptr, usr_buf = \
                    vcsm.malloc_cache(size=size, cached=rpi_vcsm.CACHE_HOST,
                                      name='test')

                random.seed(i)
                usr_buf.write(randbytes(size))
                usr_buf.seek(0)

                mem_list.append((i, size, handle, usr_buf))

            random.shuffle(mem_list)

            for i, size, handle, usr_buf in mem_list:
                random.seed(i)
                self.assertEqual(usr_buf.read(), randbytes(size))
                vcsm.free(handle=handle, usr_buf=usr_buf)
