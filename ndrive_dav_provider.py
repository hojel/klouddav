# -*- coding: utf-8 -*-
"""
WebDAV wrapper for Naver Ndrive cloud service
"""
from ndrive import Ndrive
from ndrive.urls import ndrive_urls
import dateutil.parser
import time
import urllib
import urllib2
#from io import BytesIO
from util import RequestsIO
from wsgidav.util import joinUri
from wsgidav.dav_provider import DAVProvider, DAVNonCollection, DAVCollection
from wsgidav.dav_error import DAVError, HTTP_FORBIDDEN, HTTP_INTERNAL_ERROR,\
    PRECONDITION_CODE_ProtectedProperty
from wsgidav import util

__docformat__ = "reStructuredText"

_logger = util.getModuleLogger(__name__)

class NdriveCollection(DAVCollection):
    """Collection"""
    def __init__(self, path, environ, ndrive):
        DAVCollection.__init__(self, path, environ)
        self.ndrive = ndrive
        self.nlist = None
        
    def getDisplayInfo(self):
        return {"type": "Collection"}
    
    def getMemberNames(self):
        if self.nlist is None:
            self.nlist = self.ndrive.getList(self.path, type=3)
            if self.nlist is None:
                _logger.error("fail to read %s" % self.path)
                return []
        return [lastitem(item['href']) for item in self.nlist]
    
    def getMember(self, name):
        if self.nlist is None:
            self.nlist = self.ndrive.getList(self.path, type=3)
        for item in self.nlist:
            bname = lastitem(item['href'])
            #path = joinUrl(self.path, name)
            path = item['href'].encode('utf-8')
            _logger.debug(path)
            if bname == name:
                if item['resourcetype'] == "collection":
                    return NdriveCollection(path, self.environ, self.ndrive)
                else:
                    return NdriveFile(path, self.environ, self.ndrive, item)
        return None


class NdriveFile(DAVNonCollection):
    """Represents a file."""
    def __init__(self, path, environ, ndrive, info):
        DAVNonCollection.__init__(self, path, environ)
        self.ndrive = ndrive
        self.info = info

    def getContentLength(self):
        return self.info['getcontentlength']
    def getContentType(self):
        return util.guessMimeType(self.path)
    def getCreationDate(self):
        ts = dateutil.parser.parse(self.info['creationdate'])
        return time.mktime(ts.timetuple())
    def getDisplayName(self):
        return self.name
    def getDisplayInfo(self):
        return {"type": "File"}
    def getEtag(self):
        return None
    def getLastModified(self):
        ts = dateutil.parser.parse(self.info['getlastmodified'])
        return time.mktime(ts.timetuple())
    def supportRanges(self):
        return False

    def getContent(self):
        """from downloadFile() in ndrive/client.py"""
        url = ndrive_urls['download'] + self.path
        _logger.debug(url)
        data = {'attachment':2,
                'userid': self.ndrive.user_id,
                'useridx': self.ndrive.useridx,
                'NDriveSvcType': "NHN/ND-WEB Ver",
               }
        _logger.debug(self.ndrive.user_id)
        _logger.debug(self.ndrive.useridx)
        req = self.ndrive.session.get(url, params = data, stream=True)
        #return BytesIO(req.content)
        return RequestsIO(req)


def lastitem(path):
    return path.rstrip('/').split('/')[-1].encode('utf-8')

#===============================================================================
# DAVProvider
#===============================================================================
class NdriveProvider(DAVProvider):
    def __init__(self, username, userpw):
        super(NdriveProvider, self).__init__()
        self.ndrive = Ndrive()
        if self.ndrive.login(username, userpw):
            _logger.info("login ok")
        else:
            _logger.error("login fail")

    def getResourceInst(self, path, environ):
        _logger.info("getResourceInst('%s')" % path)
        self._count_getResourceInst += 1
        root = NdriveCollection("/", environ, self.ndrive)
        return root.resolve("", path)
