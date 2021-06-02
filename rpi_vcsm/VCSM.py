import mmap
import rpi_vcsm.raw


def align(u, a):
    return (u + (a - 1)) & ~(a - 1)


class VCSM(object):

    def __init__(self):
        self.raw = rpi_vcsm.raw.raw()

    def close(self):
        if self.raw:
            self.raw.close()
        self.raw = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        return exc_value is None

    # No align parameter? Yeah, the driver always aligns the address to 4096B.

    def malloc_cache(self, size, cache, name):
        size = align(int(size), mmap.PAGESIZE)
        if not name:
            name = ''
        handle = self.raw.alloc(size, 1, cache, name)
        usr_buf = mmap.mmap(fileno=self.raw.fd, length=size,
                            flags=mmap.MAP_SHARED,
                            prot=mmap.PROT_READ | mmap.PROT_WRITE,
                            offset=handle)
        usr_ptr = self.raw.lock(handle)
        bus_ptr = self.raw.map_vc_addr_fr_hdl(handle)
        return (handle, bus_ptr, usr_ptr, usr_buf)

    def free(self, handle, usr_buf):
        usr_buf.close()
        self.raw.unlock(handle)
        self.raw.free(handle)

    def invalidate_2d(self, usr_ptr, block_count, block_size, stride):
        self.raw.clean_invalid2(self.raw.OP_INVALIDATE, usr_ptr, block_count,
                                block_size, stride)

    def invalidate(self, usr_ptr, size):
        self.invalidate_2d(usr_ptr, 1, size, 0)

    def clean_2d(self, usr_ptr, block_count, block_size, stride):
        self.raw.clean_invalid2(self.raw.OP_CLEAN, usr_ptr, block_count,
                                block_size, stride)

    def clean(self, usr_ptr, size):
        self.clean_2d(usr_ptr, 1, size, 0)
