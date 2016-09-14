# -*- coding: utf-8 -*-
"""
WebDAV wrapper for Baidu Yun cloud service
"""
from bcloud import auth, pcs
import json
import os.path
from util import UrlIO
from io import BytesIO
from wsgidav.util import joinUri
from wsgidav.dav_provider import DAVProvider, DAVNonCollection, DAVCollection
from wsgidav.dav_error import DAVError, HTTP_FORBIDDEN, HTTP_INTERNAL_ERROR,\
    PRECONDITION_CODE_ProtectedProperty
from wsgidav import util

__docformat__ = "reStructuredText"

_logger = util.getModuleLogger(__name__)

from util import _dircache
_last_path = None

_video_fmts = ['avi', 'mp4', 'mkv', 'mov']
MAX_FILES_IN_VIDEO_FOLDER = 10
MIN_SIZE_FOR_STREAM = 500*1024*1024

class BdyunCollection(DAVCollection):
    """Collection"""
    def __init__(self, path, environ):
        DAVCollection.__init__(self, path, environ)
        self.abspath = self.provider.sharePath + path
        try:
            self.nlist = _dircache[self.abspath]
        except KeyError:
            self.nlist = None
        
    def getDisplayInfo(self):
        return {"type": "Collection"}
    
    def getMemberNames(self):
        if self.nlist is None:
            self.nlist = pcs.list_dir_all(self.environ['bdyun.cookie'], self.environ['bdyun.tokens'], self.path)
            _dircache[self.abspath] = self.nlist
        names = [item['server_filename'].encode('utf-8') for item in self.nlist]
        if len(names) > MAX_FILES_IN_VIDEO_FOLDER:
            return names
        # m3u8
        global _video_fmts
        for name in names:
            rname, ext = os.path.splitext(name)
            if ext[1:].lower() in _video_fmts and item['size'] > MIN_SIZE_FOR_STREAM:
                names.append(rname+'.m3u8')
        return names
    
    def getMember(self, name):
        if self.nlist is None:
            self.nlist = pcs.list_dir_all(self.environ['bdyun.cookie'], self.environ['bdyun.tokens'], self.path)
            _dircache[self.abspath] = self.nlist
        global _video_fmts
        for item in self.nlist:
            bname = item['server_filename'].encode('utf-8')
            if bname == name:
                path = item['path'].encode('utf-8')
                if item['isdir']:
                    return BdyunCollection(path, self.environ)
                else:
                    return BdyunFile(path, self.environ, item)
            if name.endswith('.m3u8'):
                rname, ext = os.path.splitext(bname)
                if name.startswith(rname) and ext[1:].lower() in _video_fmts:
                    return BdyunStreamFile(joinUri(self.path, name), self.environ, item)
        return None


class BdyunFile(DAVNonCollection):
    """Represents a file."""
    def __init__(self, path, environ, file_info):
        DAVNonCollection.__init__(self, path, environ)
        self.file_info = file_info

    def getContentLength(self):
        return self.file_info['size']
    def getContentType(self):
        return util.guessMimeType(self.path)
    def getCreationDate(self):
        return self.file_info['local_ctime']
    def getDisplayName(self):
        return self.name
    def getDisplayInfo(self):
        return {"type": "File"}
    def getEtag(self):
        return None
    def getLastModified(self):
        return self.file_info['local_mtime']
    def supportRanges(self):
        return True

    def getContent(self):
        url = pcs.get_simple_download_link(self.path)
        return UrlIO(url, size=self.file_info['size'], cookies=self.environ['bdyun.cookie'], headers=pcs.default_headers)


class BdyunStreamFile(DAVNonCollection):
    """Represents a file."""
    def __init__(self, path, environ, file_info):
        DAVNonCollection.__init__(self, path, environ)
        self.file_info = file_info
        self.m3u = None

    def getContentLength(self):
        if self.m3u is None:
            txt = pcs.get_streaming_playlist(self.environ['bdyun.cookie'], self.file_info['path'])
            self.m3u = txt.encode('utf-8')
        return len(self.m3u)
    def getContentType(self):
        return util.guessMimeType(self.path)
    def getCreationDate(self):
        return None
    def getDisplayName(self):
        return self.name
    def getDisplayInfo(self):
        return {"type": "File"}
    def getEtag(self):
        return None
    def getLastModified(self):
        return None
    def supportRanges(self):
        return False

    def getContent(self):
        if self.m3u is None:
            txt = pcs.get_streaming_playlist(self.environ['bdyun.cookie'], self.file_info['path'])
            self.m3u = txt.encode('utf-8')
        return BytesIO(self.m3u)


def bdyun_login(username, password):
    cookie = auth.get_BAIDUID()
    token = auth.get_token(cookie)
    tokens = {'token':token}
    ubi = auth.get_UBI(cookie, tokens)
    cookie = auth.add_cookie(cookie, ubi, ['UBI','PASSID'])
    key_data = auth.get_public_key(cookie, tokens)
    pubkey = key_data['pubkey']
    rsakey = key_data['key']
    password_enc = auth.RSA_encrypt(pubkey, password)
    err_no, query = auth.post_login(cookie, tokens, username, password_enc, rsakey)
    if err_no == 257:
        vcodetype = query['vcodetype']
        codeString = query['codeString']
        vcode_path = auth.get_signin_vcode(cookie, codeString)
        print vcode_path
        verifycode = ""
        while len(verifycode) != 4:
            verifycode = raw_input("enter captcha from the above url... ")
    err_no, query = auth.post_login(cookie, tokens, username, password_enc, rsakey, verifycode, codeString)
    if err_no == 0:
        temp_cookie = query
        auth_cookie, bdstoken = auth.get_bdstoken(temp_cookie)
        if bdstoken:
            tokens['bdstoken'] = bdstoken
            return auth_cookie, tokens
    elif err_no == 4:
        print "Unknown user name"
    elif err_no == 6:
        print "Wrong password"
    print "Error: %d" % err_no
    return None


#===============================================================================
# DAVProvider
#===============================================================================
class BdyunProvider(DAVProvider):
    def __init__(self, username, userpw, cfgpath=None):
        super(BdyunProvider, self).__init__()
        do_login = True
        if cfgpath is not None:
            try:
                f = open(cfgpath)
                obj = json.load(f)
                cookie = obj['cookie']
                tokens = obj['tokens']
                do_login = False
            except:
                pass
        if do_login:
            result = bdyun_login(username, userpw)
            if result is None:
                import sys
                _logger.error("login fail")
                sys.exit(1)
            cookie, tokens = result
            # save
            f = open(cfgpath, 'w')
            json.dump({'cookie':cookie, 'tokens':tokens}, f)
        self.user_info = {"username":username,
                          "cookie":cookie,
                          "tokens":tokens
                         }

    def getResourceInst(self, path, environ):
        _logger.info("getResourceInst('%s')" % path)
        self._count_getResourceInst += 1
        global _last_path
        npath = self.sharePath + path
        if _last_path == npath:
            global _dircache
            #del _dircache[npath]
            _dircache.__delete__(npath)
        _last_path = npath
        environ['bdyun.cookie'] = self.user_info['cookie']
        environ['bdyun.tokens'] = self.user_info['tokens']
        root = BdyunCollection("/", environ)
        return root.resolve("", path)
