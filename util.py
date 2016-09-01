# -*- coding: utf-8 -*-
from io import BufferedIOBase

# file io wrapper for requests module
class RequestsIO(BufferedIOBase):
    def __init__(self, req):
        super(RequestsIO, self).__init__()
        self.req = req
        #self.rptr = self.req.iter_content(CONTENT_CHUNK_SIZE)

    def read(self, n=-1):
        if n == -1:
            return self.req.content
        return self.req.raw.read(n)

    def readinto(self, b):
        _b = self.req.raw.read(len(b))
        n = len(_b)
        b[:n] = _b
        return n

    def write(self, b):
        return 0
