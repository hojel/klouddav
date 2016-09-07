# -*- coding: utf-8 -*-
"""
WebDAV wrapper for Baidu Yun cloud service
"""
from bcloud import auth, pcs
import json
from util import RequestsIO
from lru import LRUCacheDict
from wsgidav.util import joinUri
from wsgidav.dav_provider import DAVProvider, DAVNonCollection, DAVCollection
from wsgidav.dav_error import DAVError, HTTP_FORBIDDEN, HTTP_INTERNAL_ERROR,\
    PRECONDITION_CODE_ProtectedProperty
from wsgidav import util

__docformat__ = "reStructuredText"

_logger = util.getModuleLogger(__name__)

_last_path = None
_user_info = None
_dircache = LRUCacheDict(max_size=10, expiration=30*60)

class BdyunCollection(DAVCollection):
    """Collection"""
    def __init__(self, path, environ):
        DAVCollection.__init__(self, path, environ)
        try:
            self.nlist = _dircache[path]
        except KeyError:
            self.nlist = None
        
    def getDisplayInfo(self):
        return {"type": "Collection"}
    
    def getMemberNames(self):
        if self.nlist is None:
            global _user_info
            self.nlist = pcs.list_dir_all(_user_info['cookie'], _user_info['tokens'], self.path)
            _dircache[self.path] = self.nlist
        return [item['server_filename'].encode('utf-8') for item in self.nlist]
    
    def getMember(self, name):
        if self.nlist is None:
            global _user_info
            self.nlist = pcs.list_dir_all(_user_info['cookie'], _user_info['tokens'], self.path)
            _dircache[self.path] = self.nlist
        for item in self.nlist:
            bname = item['server_filename'].encode('utf-8')
            if bname == name:
                path = item['path'].encode('utf-8')
                if item['isdir']:
                    return BdyunCollection(path, self.environ)
                else:
                    return BdyunFile(path, self.environ, item)
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
        return False

    def getContent(self):
        """from downloadFile() in ndrive/client.py"""
        global _user_info
        req = pcs.stream_download(_user_info['cookie'], _user_info['tokens'], self.path)
        return RequestsIO(req)


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
        #vcode_path = os.path.join(os.sep, 'mnt', 'c', 'Users', 'seung', 'Downloads', 'vcode.png')
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
            json.dump(f, {'cookie':cookie, 'tokens':tokens})
        global _user_info
        _user_info = {"username":username,
                      "cookie":cookie,
                      "tokens":tokens
                     }

    def getResourceInst(self, path, environ):
        _logger.info("getResourceInst('%s')" % path)
        self._count_getResourceInst += 1
        global _last_path
        if _last_path == path:
            global _dircache
            #del _dircache[path]
            _dircache.__delete__(path)
        _last_path = path
        root = BdyunCollection("/", environ)
        return root.resolve("", path)
