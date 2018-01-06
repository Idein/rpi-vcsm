import rpi_vcsm.VCSM
import rpi_vcsm.buffer

def test_alloc():
    with rpi_vcsm.VCSM.VCSM() as vcsm:
        size = 32000000

        (handle, bus, usr) = vcsm.malloc_cache(size, rpi_vcsm.CACHE_NONE, None)

        buffer = rpi_vcsm.buffer.buffer(usr)
        addr = buffer.get_addr()
        buffer.close()

        print('size=0x%08x' % size)
        print('Got handle:               0x%08x' % handle)
        print('Got bus address:          0x%08x' % bus)
        print('Got user virtual address: 0x%08x' % addr)

        vcsm.clean(usr, size)
        vcsm.invalidate(usr, size)
        vcsm.clean(usr, size)
        vcsm.invalidate(usr, size)
        vcsm.clean(usr, size)
        vcsm.invalidate(usr, size)

        vcsm.free(handle, usr)
