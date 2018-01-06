from cpython.buffer cimport Py_buffer, PyBUF_SIMPLE, \
                            PyObject_GetBuffer, PyBuffer_Release

cdef class buffer:

    cdef Py_buffer buffer

    def __init__(self, object mem):

        cdef int err
        cdef Py_buffer buf
        err = PyObject_GetBuffer(mem, &buf, PyBUF_SIMPLE)
        if not err == 0:
            raise RuntimeError('Failed to get buffer from object: %d' % err)

        self.buffer = buf

    def close(self):
        PyBuffer_Release(&self.buffer)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, value, traceback):
        self.close();
        return exc_type is None

    def get_addr(self):
        return <int> self.buffer.buf
