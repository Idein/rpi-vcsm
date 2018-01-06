import mmap
import rpi_vcsm.raw


def align(u, a):
    return (u + (a - 1)) & ~(a - 1)


class VCSM(object):

    pagesize = mmap.PAGESIZE

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
        handle = self.raw.alloc(int(size), 1, cache,
                                name if name is not None else '')
        usr_ptr = mmap.mmap(self.raw.fd, size, flags = mmap.MAP_SHARED,
                            prot = mmap.PROT_READ | mmap.PROT_WRITE,
                            offset = handle)
        bus_ptr = self.raw.lock(handle)
        return (handle, bus_ptr, usr_ptr)

    def free(self, handle, usr_ptr):
        usr_ptr.close()
        self.raw.unlock(handle)
        self.raw.free(handle)

    def invalidate_2d(self, usr_ptr, block_count, block_size, stride):
        self.raw.clean_invalid2(self.raw.OP_INVALIDATE, usr_ptr,
                block_count, block_size, stride)

    def invalidate(self, usr_ptr, size):
        self.invalidate_2d(usr_ptr, 1, size, 0)

    def clean_2d(self, usr_ptr, block_count, block_size, stride):
        self.raw.clean_invalid2(self.raw.OP_CLEAN, usr_ptr,
                block_count, block_size, stride)

    def clean(self, usr_ptr, size):
        self.clean_2d(usr_ptr, 1, size, 0)
