""" The portalpy module for working with the ArcGIS Online and Portal APIs."""
from __future__ import absolute_import
import io
import os
import re
import ssl
import sys
import json
import uuid
import zlib
import shutil
import logging
import tempfile
import mimetypes
import unicodedata
try:
    #PY2
    from cStringIO import StringIO
except ImportError:
    #PY3
    from io import StringIO
from io import BytesIO
from collections import OrderedDict

import six
from six.moves.urllib_parse import urlparse, urlunparse, parse_qsl
from six.moves.urllib_parse import quote, unquote, urlunsplit
from six.moves.urllib_parse import urlencode, urlsplit
from six.moves.urllib.error import HTTPError
from six.moves.urllib import request
from six.moves import http_cookiejar as cookiejar
from six.moves import http_client
from .common._utils import Error
__version__ = '1.0'
_log = logging.getLogger(__name__)

DEFAULT_TOKEN = uuid.uuid4()

########################################################################
class MultiPartForm(object):
    """Accumulate the data to be used when posting a form."""
    PY2 = sys.version_info[0] == 2
    PY3 = sys.version_info[0] == 3
    files = []
    form_fields = []
    boundary = None
    form_data = ""
    #----------------------------------------------------------------------
    def __init__(self, param_dict=None, files=None):
        if param_dict is None:
            param_dict = {}
        if files is None:
            files = {}
        self.boundary = None
        self.files = []
        self.form_data = ""
        if len(self.form_fields) > 0:
            self.form_fields = []

        if len(param_dict) == 0:
            self.form_fields = []
        else:
            for k,v in param_dict.items():
                self.form_fields.append((k,v))
                del k,v
        if isinstance(files, list):
            if len(files) == 0:
                self.files = []
            else:
                for key, filePath, fileName in files:
                    self.add_file(fieldname=key,
                                  filename=fileName,
                                  filePath=filePath,
                                  mimetype=None)
        elif isinstance(files, dict):
            for key, filepath in files.items():
                self.add_file(fieldname=key,
                              filename=os.path.basename(filepath),
                              filePath=filepath,
                              mimetype=None)
                del key, filepath
        self.boundary = "%s" % self._make_boundary()
    #----------------------------------------------------------------------
    def get_content_type(self):
        return 'multipart/form-data; boundary=%s' % self.boundary
    #----------------------------------------------------------------------
    def add_field(self, name, value):
        """Add a simple field to the form data."""
        self.form_fields.append((name, value))
    #----------------------------------------------------------------------
    def _make_boundary(self):
        """ creates a boundary for multipart post (form post)"""
        if six.PY2:
            return '----------------%s--' % uuid.uuid4().hex
        elif six.PY3:
            return '----------------%s--' % uuid.uuid4().hex
        else:
            from random import choice
            digits = "0123456789"
            letters = "abcdefghijklmnopqrstuvwxyz"
            return '----------------%s--'.join(choice(letters + digits) \
                                   for i in range(15))
    #----------------------------------------------------------------------
    def add_file(self, fieldname, filename, filePath, mimetype=None):
        """Add a file to be uploaded.
        Inputs:
           fieldname - name of the POST value
           fieldname - name of the file to pass to the server
           filePath - path to the local file on disk
           mimetype - MIME stands for Multipurpose Internet Mail Extensions.
             It's a way of identifying files on the Internet according to
             their nature and format. Default is None.
        """
        body = filePath
        if mimetype is None:
            mimetype = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
        self.files.append((fieldname, filename, mimetype, body))
    #----------------------------------------------------------------------
    @property
    def make_result(self):
        if self.PY2:
            self._2()
        elif self.PY3:
            self._3()
        return self.form_data
    #----------------------------------------------------------------------
    def _2(self):
        """python 2.x version of formatting body data"""
        boundary = self.boundary
        buf = StringIO()
        for (key, value) in self.form_fields:
            buf.write('--%s\r\n' % boundary)
            buf.write('Content-Disposition: form-data; name="%s"' % key)
            buf.write('\r\n\r\n%s\r\n' % value)
        for (key, filename, mimetype, filepath) in self.files:
            if os.path.isfile(filepath):
                buf.write('--{boundary}\r\n'
                          'Content-Disposition: form-data; name="{key}"; '
                          'filename="{filename}"\r\n'
                          'Content-Type: {content_type}\r\n\r\n'.format(
                              boundary=boundary,
                              key=key,
                              filename=filename,
                              content_type=mimetype))
                with open(filepath, "rb") as f:
                    shutil.copyfileobj(f, buf)
                buf.write('\r\n')
        buf.write('--' + boundary + '--\r\n\r\n')
        buf = buf.getvalue()
        self.form_data = buf
    #----------------------------------------------------------------------
    def _3(self):
        """ python 3 method"""
        boundary = self.boundary
        buf = BytesIO()
        textwriter = io.TextIOWrapper(
            buf, 'utf8', newline='', write_through=True)

        for (key, value) in self.form_fields:
            textwriter.write(
                '--{boundary}\r\n'
                'Content-Disposition: form-data; name="{key}"\r\n\r\n'
                '{value}\r\n'.format(
                    boundary=boundary, key=key, value=value))
        for(key, filename, mimetype, filepath) in self.files:
            if os.path.isfile(filepath):
                textwriter.write(
                    '--{boundary}\r\n'
                    'Content-Disposition: form-data; name="{key}"; '
                    'filename="{filename}"\r\n'
                    'Content-Type: {content_type}\r\n\r\n'.format(
                        boundary=boundary, key=key, filename=filename,
                        content_type=mimetype))
                with open(filepath, "rb") as f:
                    shutil.copyfileobj(f, buf)
                textwriter.write('\r\n')
        textwriter.write('--{}--\r\n\r\n'.format(boundary))
        self.form_data = buf.getvalue()
########################################################################
class HTTPSClientAuthHandler(request.HTTPSHandler):
    def __init__(self, key, cert):
        request.HTTPSHandler.__init__(self)
        self.key = key
        self.cert = cert
    def https_open(self, req):
        #Rather than pass in a reference to a connection class, we pass in
        # a reference to a function which, for all intents and purposes,
        # will behave as a constructor
        return self.do_open(self.getConnection, req)
    def getConnection(self, host, timeout=300):
        return  http_client.HTTPSConnection(host,
                                            key_file=self.key,
                                            cert_file=self.cert,
                                            timeout=timeout)
########################################################################
class _ArcGISConnection(object):
    """ A class users to manage connection to ArcGIS services (Portal and Server). """
    baseurl = None
    key_file = None
    cert_file = None
    all_ssl = None
    proxy_host = None
    proxy_port = None
    _token = None
    _product = None
    _referer = None
    _useragent = None
    _parsed_org_url = None
    _username = None
    _password = None
    _auth = None
    _tokenurl = None
    _token = None
    _refresh_token = None   # oauth
    _server_token = None
    _connection = None
    _portal_connection = None
    _service_url = None

    #----------------------------------------------------------------------
    def __init__(self, baseurl=None, tokenurl=None, username=None,
                 password=None, key_file=None, cert_file=None,
                 expiration=60, all_ssl=False, referer=None,
                 proxy_host=None, proxy_port=None,
                 connection=None, verify_cert=True,
                 client_id=None):
        """ The _ArcGISConnection constructor. Requires URL and optionally username/password. """
        if baseurl is None:
            self._is_arcpy = False
        else:
            self._is_arcpy = baseurl.lower() == "pro"
            self._auth = "PRO"
        if self._is_arcpy:
            try:
                import arcpy
                baseurl = arcpy.GetActivePortalURL()
                self.baseurl = self._validate_url(url=baseurl)
            except ImportError:
                raise Error("Could not import arcpy")
        else:
            self.baseurl = baseurl
        self._tokenurl = tokenurl
        '''_normalize_url(baseurl)'''
        self._product = self._check_product()
        self.key_file = key_file
        self.cert_file = cert_file
        self.all_ssl = all_ssl
        self.proxy_host = proxy_host
        self.proxy_port = proxy_port
        self.token = None
        self._server_token = None
        self._connection = connection # second connection

        self._verify_cert = verify_cert

        # Setup the referer and user agent
        if baseurl:
            if not referer:
                referer = "http"#urlparse(baseurl).netloc
            self._referer = referer
            self._useragent = 'geosaurus/' + __version__

            parsed_url = urlparse(self.baseurl)
            self._parsed_org_url = urlunparse((parsed_url[0], parsed_url[1], "", "", "", ""))

        self._username = username
        self._password = password

        self._client_id = client_id

        if client_id is not None:
            self._auth = 'OAUTH'
        elif cert_file is not None and key_file is not None:
            self._auth = "PKI"
        elif username is not None and password is not None:
            self._auth = "BUILTIN" # or BASIC (LDAP) or DIGEST
        else:
            self._auth = "ANON" # or IWA (NTLM or Kerberos) (self.login sets this up)

        if cert_file is None and key_file is None:
            self.login(username, password, expiration, client_id)

    #----------------------------------------------------------------------
    def _validate_url(self, url):
        """ensures the base url has the /sharing/rest"""
        if self._is_arcpy:
            if not url[-1] == '/':
                url += '/'
            if url.lower().find("www.arcgis.com") > -1:
                urlscheme = urlparse(url).scheme
                return "{scheme}://www.arcgis.com/sharing/rest/".format(scheme=urlscheme)
            elif url.lower().endswith("sharing/"):
                return url + 'rest/'
            elif url.lower().endswith("sharing/rest/"):
                return url
            else:
                return url + 'sharing/rest/'
        return url
    #----------------------------------------------------------------------
    @property
    def product(self):
        if self._product is None:
            self._product = self._check_product()
        return self._product
    #----------------------------------------------------------------------
    @property
    def connection(self):
        """gets/sets an additional connection object to get a token from"""
        return self._connection
    #----------------------------------------------------------------------
    @connection.setter
    def connection(self, value):
        """gets/sets an additional connection object to get a token from"""
        if self._connection != value:
            self._connection = value
            self._token = None
            self._server_token = None
    #----------------------------------------------------------------------
    @property
    def token(self):
        """gets/sets the token"""
        if self.connection and self.service_url:
            return self.connection.generate_portal_server_token(serverUrl=self.service_url)
        elif self._connection and self._server_token is None:
            #create a portalserver token
            if self._connection.product == "AGO":
                return self.connection.token
            return self.generate_portal_server_token(serverUrl=self.baseurl)
        elif self._connection and self._server_token:
            return self._server_token
        elif self._connection is None and self.product == "FEDERATED_SERVER":
            self._connection = _ArcGISConnection(baseurl=self.baseurl, connection=self)
            return self.token
        elif self._token:
            return self._token
        elif self._username and self._password:
            self.login(username=self._username, password=self._password, expiration=60)
            return self._token
        return None
    #----------------------------------------------------------------------
    @property
    def service_url(self):
        """gets/sets the service url"""
        return self._service_url
    #----------------------------------------------------------------------
    @service_url.setter
    def service_url(self, value):
        """gets/sets the service url"""
        if value:
            self._service_url = value
        else:
            self._service_url = None
    #----------------------------------------------------------------------
    @token.setter
    def token(self, value):
        """gets/sets the token"""
        if self._token != value:
            self._token = value
    #----------------------------------------------------------------------
    def generate_token(self, username, password, expiration=60, client_id=None):
        """ Generates and returns a new token, but doesn't re-login. """
        if self._is_arcpy and \
           self.product in ("PORTAL", "AGO"):
            try:
                import arcpy
                resp = arcpy.GetSigninToken()
                if 'referer' in resp:
                    self._referer = resp['referer']
                if 'token' in resp:
                    return resp['token']
                else:
                    raise arcpy.ExecuteError("Could not login using Pro Authentication")
            except ImportError as ie:
                raise Error("Could not import arcpy")
            except:
                raise arcpy.ExecuteError("Could not login using Pro Authentication")
        if self.product == "SERVER":
            postdata = { 'username': username,
                         'password': password,
                         'client': 'requestip',
                         'expiration': expiration,
                         'f': 'json' }
        else:
            postdata = { 'username': username, 'password': password,
                         'client': 'referer', 'referer': self._referer,
                         'expiration': expiration, 'f': 'json' }
        if client_id is not None:
            return self.oauth_authenticate(client_id, expiration)

        else:
            if self._tokenurl is None:
                if self.baseurl.endswith('/'):
                    resp = self.post('generateToken', postdata,
                                     ssl=True, add_token=False)
                else:
                    resp = self.post('/generateToken', postdata,
                                     ssl=True, add_token=False)
            else:
                resp = self.post(path=self._tokenurl, postdata=postdata,
                                 ssl=True, add_token=False)
            if resp:
                return resp.get('token')

    def oauth_authenticate(self, client_id, expiration):

        parameters = {
            'client_id': client_id,
            'response_type': 'code',
            'expiration': -1, # we want refresh_token to work for the life of the script
            'redirect_uri': 'urn:ietf:wg:oauth:2.0:oob'
        }

        code = None

        if self._username is not None and self._password is not None: # built-in user through OAUTH
            content = self.get('oauth2/authorize', parameters, ssl=True, try_json=False, add_token=False)
            import re
            import json
            from bs4 import BeautifulSoup
            pattern = re.compile('var oAuthInfo = ({.*?});', re.DOTALL)
            soup = BeautifulSoup(content, 'html.parser')
            for script in soup.find_all('script'):
                script_code = str(script.string).strip()
                matches = pattern.search(script_code)
                if not matches is None:
                    js_object = matches.groups()[0]
                    oauth_info = json.loads(js_object)
                    break

            parameters = {
                'user_orgkey': '',
                'username': self._username,
                'password': self._password,
                'oauth_state': oauth_info['oauth_state']
            }
            content = self.post('oauth2/signin', parameters, ssl=True, try_json=False, add_token=False)
            soup = BeautifulSoup(content, 'html.parser')

            if soup.title is not None:
                if 'SUCCESS' in soup.title.string:
                    code = soup.title.string[len('SUCCESS code='):]

        if code is None: # try interactive signin
            url = self.baseurl + 'oauth2/authorize'
            paramstring = urlencode(parameters)
            codeurl = "{}?{}".format(url, paramstring)

            import webbrowser
            import getpass

            print("Please sign in to your GIS and paste the code that is obtained below.")
            print("If a web browser does not automatically open, please navigate to the URL below yourself instead.")
            print("Opening web browser to navigate to: " + codeurl)
            webbrowser.open_new(codeurl)
            code = getpass.getpass("Enter code obtained on signing in using SAML: ")

        if code is not None:
            parameters = {
                'client_id': client_id,
                'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': 'urn:ietf:wg:oauth:2.0:oob'
            }
            token_info = self.post('oauth2/token', parameters, ssl=True, add_token=False)
            # print('******' + str(token_info))

            self._refresh_token = token_info['refresh_token']
            self._token = token_info['access_token']

            return self._token
        else:
            print("Unable to sign in using OAUTH")
            return None

    #----------------------------------------------------------------------
    def generate_portal_server_token(self, serverUrl, expiration=1440):
        """generates a server token using Portal token"""

        postdata = {'serverURL':serverUrl,
                    'token': self.token,
                    'expiration':str(expiration),
                    'f': 'json',
                    'request':'getToken',
                    'referer':self._referer}
        if self._tokenurl is None:
            if self.baseurl.endswith('/'):
                resp = self.post('generateToken', postdata,
                                 ssl=True, add_token=False)
            else:
                resp = self.post('/generateToken', postdata,
                                 ssl=True, add_token=False)
        else:
            resp = self.post(path=self._tokenurl, postdata=postdata,
                             ssl=True, add_token=False)
        if resp:
            return resp.get('token')
    #----------------------------------------------------------------------
    def login(self, username, password, expiration=60, client_id=None):
        """ Logs into the portal using username/password. """
        newtoken = None
        try:
            if self._is_arcpy: # PRO authentication
                newtoken = self.generate_token(username, password, expiration)
                if newtoken:
                    self._token = newtoken

            resp = self.post('', { 'f': 'json' }, add_token=False) # probe portal to find auth scheme
                                                  # if basic, digest, NTLM or Kerberos, etc is being used
                                                  # except handler will catch it and set self._auth appropriately

            if username is not None and password is not None:
                newtoken = self.generate_token(username, password, expiration, client_id)

                if newtoken:
                    self._token = newtoken
                    self._username = username
                    self._password = password
                    self._expiration = expiration

                    return newtoken

            elif client_id is not None:
                newtoken = self.generate_token(username, password, expiration, client_id)
                return newtoken

            elif self._is_arcpy:
                return newtoken

            else:
                self._auth = "ANON"

        except HTTPError as err:
            if err.code == 401:
                authhdr = err.headers.get('WWW-Authenticate')
                if authhdr is not None:
                    if authhdr.lower().startswith('basic'):
                        self._auth = "BASIC"
                    elif authhdr.lower().startswith('digest'):
                        self._auth = "DIGEST"
                    elif authhdr.lower().startswith('ntlm'):
                        self._auth = "IWA"
                    elif authhdr.lower().startswith('negotiate'):
                        self._auth = "IWA"
                    else:
                        _log.warn('Unsupported authentication scheme: ' + authhdr)

                    return newtoken

            else:
                raise
        except ValueError as ve:
            if str(ve) == "AbstractBasicAuthHandler does not support the following scheme: 'Negotiate'":
                self._auth = "IWA"


    #----------------------------------------------------------------------
    def relogin(self, expiration=60):
        """ Re-authenticates with the portal using the same username/password. """
        if self._refresh_token is not None and self._client_id is not None: # oauth2
            parameters = {
                'client_id': self._client_id,
                'grant_type': 'refresh_token',
                'refresh_token': self._refresh_token,
                'redirect_uri': 'urn:ietf:wg:oauth:2.0:oob'
            }
            token_info = self.post('oauth2/token', parameters, ssl=True, add_token=False)
            self._token = token_info['access_token']

            return self._token
        else:
            return self.login(self._username, self._password, expiration)
    #----------------------------------------------------------------------
    def logout(self):
        """ Logs out of the portal. """
        self._token = None
        self._server_token = None
    #----------------------------------------------------------------------
    @property
    def is_logged_in(self):
        """ Returns true if logged into the portal. """
        return self._token is not None or self._server_token is not None
    #----------------------------------------------------------------------
    def _mainType(self, resp):
        """ gets the main type from the response object"""
        if six.PY2:
            return resp.headers.maintype
        elif six.PY3:
            return resp.headers.get_content_maintype()
        else:
            return None
    #----------------------------------------------------------------------
    def _check_product(self):
        """
        determines if the product is portal, arcgis online or arcgis server
        """
        baseurl = self.baseurl
        if baseurl is None:
            return "UNKNOWN"
        if baseurl.lower().find("arcgis.com") > -1:
            return "AGO"
        elif baseurl.lower().find("/sharing/rest") > -1:
            return "PORTAL"
        else:
            #Brute Force Method
            root = baseurl.lower().split("/sharing")[0]
            root = baseurl.lower().split('/rest')[0]
            parts = ['/info', '/rest/info', '/sharing/rest/info']
            params = {"f" : "json"}
            for pt in parts:
                try:
                    res = self.get(path=root + pt, params=params)
                    if self._tokenurl is None and \
                       res is not None and \
                       'authInfo' in res and \
                       'tokenServicesUrl' in res['authInfo']:
                        self._tokenurl = res['authInfo']['tokenServicesUrl']
                except HTTPError as e:
                    res = ""
                if isinstance(res, dict) and \
                   "currentVersion" in res:
                    t_parsed = urlparse(self._tokenurl[1:]).path
                    b_parsed = urlparse(self.baseurl[1:]).path
                    if t_parsed.startswith("/"):
                        t_parsed = t_parsed[1:].split("/")[0]
                    else:
                        t_parsed = t_parsed.split("/")[0]
                    if b_parsed.startswith("/"):
                        b_parsed = b_parsed[1:].split("/")[0]
                    else:
                        b_parsed = b_parsed.split("/")[0]
                    if t_parsed.lower() != b_parsed.lower():
                        return "FEDERATED_SERVER"
                    return "SERVER"
                del pt
                del res
        return "PORTAL"
    #----------------------------------------------------------------------
    def _get_file_name(self, contentDisposition,
                       url, ext=".unknown"):
        """ gets the file name from the header or url if possible """
        if six.PY2:
            if contentDisposition is not None:
                return re.findall(r'filename[^;=\n]*=(([\'"]).*?\2|[^;\n]*)',
                                  contentDisposition.strip().replace('"', ''))[0][0]
            elif os.path.basename(url).find('.') > -1:
                return os.path.basename(url)
        elif six.PY3:
            if contentDisposition is not None:
                p = re.compile(r'filename[^;=\n]*=(([\'"]).*?\2|[^;\n]*)')
                return p.findall(contentDisposition.strip().replace('"', ''))[0][0]
            elif os.path.basename(url).find('.') > -1:
                return os.path.basename(url)

        if six.PY2:
            hex = '-===============%s==' % uuid.uuid4().get_hex()
        elif six.PY3:
            hex = '-===============%s==' % uuid.uuid4().hex

        return "%s.%s" % (hex, ext)
    #----------------------------------------------------------------------
    def _process_response(self, resp, out_folder=None,  file_name=None, force_bytes=False):
        """ processes the response object"""
        CHUNK = 4056
        maintype = self._mainType(resp)
        contentDisposition = resp.headers.get('content-disposition')
        contentType = resp.headers.get('content-type')
        contentLength = resp.headers.get('content-length')
        if not force_bytes and \
           (maintype.lower() in ('image', 'application/x-zip-compressed') or \
            contentType == 'application/x-zip-compressed' or \
           (contentDisposition is not None and contentDisposition.lower().find('attachment;') > -1)):
            fname = self._get_file_name(contentDisposition=contentDisposition, url=resp.geturl()).split('?')[0]
            if out_folder is None:
                out_folder = tempfile.gettempdir()
            if contentLength is not None:
                max_length = int(contentLength)
                if max_length < CHUNK:
                    CHUNK = max_length
            if file_name is None:
                file_name = os.path.join(out_folder, fname)
            else:
                file_name = os.path.join(out_folder, file_name)
            with open(file_name, 'wb') as writer:
                for data in self._chunk(response=resp):
                    writer.write(data)
                    del data
                del writer
            return file_name, True
        else:
            read = ""
            if file_name and out_folder:
                f_n_path = os.path.join(out_folder, file_name)
                with open(f_n_path, 'wb') as writer:
                    for data in self._chunk(response=resp, size=4096):
                        writer.write(data)
                        del data
                    writer.flush()
                    del writer
                return f_n_path, True
            else:
                for data in self._chunk(response=resp, size=4096):
                    if six.PY3 == True:
                        if read == "":
                            read = data
                        else:
                            read += data
                    else:
                        read += data
                    del data
            if six.PY3 and len(read) > 0:
                try:
                    read = read.decode("utf-8").strip()
                except:
                    pass
            try:
                return read.strip(), False
            except:
                return read, False
        return "", False
    #----------------------------------------------------------------------
    def _chunk(self, response, size=4096):
        """
        downloads a web response in pieces to ensure there are no
        memory issues.
        """
        method = response.headers.get("content-encoding")
        if method == "gzip":
            d = zlib.decompressobj(16+zlib.MAX_WBITS)
            b = response.read(size)
            while b:
                data = d.decompress(b)
                yield data
                b = response.read(size)
                del data
        else:
            while True:
                chunk = response.read(size)
                if not chunk: break
                yield chunk
    #----------------------------------------------------------------------
    def get(self, path, params=None, ssl=False,
            compress=True, try_json=True, is_retry=False,
            use_ordered_dict=False, out_folder=None,
            file_name=None, force_bytes=False, add_token=True,
            token=DEFAULT_TOKEN):
        """ Returns result of an HTTP GET. Handles token timeout and all SSL mode."""
        url = path
        if url.lower().find("https://") > -1 or\
           url.lower().find("http://") > -1:
            url = path
        elif len(url) == 0:
            url = self.baseurl
        elif (len(url) > 0 and url[0] == '/' ) == False and \
             self.baseurl.endswith('/') == False:
            url = "/{path}".format(path=url)

        if not url.startswith('http://') and \
           not url.startswith('https://'):
            url = self.baseurl + url
        if ssl or self.all_ssl:
            url = url.replace('http://', 'https://')

        if params is None:
            params = {}
        if try_json:
            params['f'] = 'json'


        if add_token:
            if token != DEFAULT_TOKEN: # use the provided token, if any
                if token is not None:
                    params['token'] = token
                else:
                    pass # no token, public access
            elif self.token is not None:
                params['token'] = self.token

        if len(params.keys()) > 0:
            url = "{url}?{params}".format(url=url,
                                          params=urlencode(params))
        _log.debug('REQUEST (get): ' + url)

        try:
            # Send the request and read the response
            headers = [('Referer', self._referer),
                       ('User-Agent', self._useragent)]
            if compress:
                headers.append(('Accept-encoding', 'gzip'))

            handlers = self.get_handlers()
            opener = request.build_opener(*handlers)
            opener.addheaders = headers
            resp = opener.open(url)

            resp_data, is_file = self._process_response(resp,
                                               out_folder=out_folder,
                                               file_name=file_name,
                                               force_bytes=force_bytes)

            # If is a file or we're not trying to parse to JSON, return response as is
            if is_file or not try_json:
                return resp_data

            try:
                if use_ordered_dict:
                    resp_json = json.loads(resp_data,
                                           object_pairs_hook=OrderedDict)
                else:
                    resp_json = json.loads(resp_data)

                # Check for errors, and handle the case where the token timed
                # out during use (and simply needs to be re-generated)
                try:
                    if resp_json:
                        if 'error' in resp_json:
                            errorcode = resp_json['error']['code'] if 'code' in resp_json['error'] else 0
                            if errorcode == 498 and not is_retry:
                                _log.info('Token expired during get request, ' \
                                          + 'fetching a new token and retrying')
                                newtoken = self.relogin()


                                self.token = newtoken

                                if token != DEFAULT_TOKEN: # was provided a FEDERATED SERVER token, that has expired
                                    newtoken = self.generate_portal_server_token(url)
                                else:
                                    newtoken = newtoken

                                newpath = self._url_add_token(path, newtoken)


                                return self.get(path=newpath, params=params, ssl=ssl, compress=compress, try_json=try_json, is_retry=True)
                            elif errorcode == 498:
                                raise RuntimeError('Invalid token')
                            self._handle_json_error(resp_json['error'], errorcode)
                            return None
                except AttributeError:
                    # Top-level JSON object isnt a dict, so can't have an error
                    pass

                # If the JSON parsed correctly and there are no errors,
                # return the JSON
                return resp_json

            # If we couldnt parse the response to JSON, return it as is
            except ValueError:
                return resp_data
            except TypeError as te:
                _log.info(te.args[0])
                return resp_data

        # If we got an HTTPError when making the request check to see if it's
        # related to token timeout, in which case, regenerate a token
        except HTTPError as e:
            if e.code == 498 and not is_retry:
                _log.info('Token expired during get request, fetching a new ' \
                          + 'token and retrying')
                self.logout()
                newtoken = self.relogin()
                newpath = self._url_add_token(path, newtoken)
                return self.get(newpath, ssl, try_json, is_retry=True)
            elif e.code == 498:
                raise RuntimeError('Invalid token')
            else:
                raise e
    #----------------------------------------------------------------------
    def _ensure_dir(self, f):
        if not os.path.exists(f):
            os.makedirs(f)
    #----------------------------------------------------------------------
    def _url_add_token(self, url, token):

        # Parse the URL and query string
        urlparts = urlparse(url)
        qs_list = parse_qsl(urlparts.query)

        # Update the token query string parameter
        replaced_token = False
        new_qs_list = []
        for qs_param in qs_list:
            if qs_param[0] == 'token':
                qs_param = ('token', token)
                replaced_token = True
            new_qs_list.append(qs_param)
        if not replaced_token:
            new_qs_list.append(('token', token))

        # Rebuild the URL from parts and return it
        return urlunparse((urlparts.scheme, urlparts.netloc,
                           urlparts.path, urlparts.params,
                           urlencode(new_qs_list),
                           urlparts.fragment))
    #----------------------------------------------------------------------
    def get_handlers(self, verify_cert=True):
        handlers = []
        if self._auth == "BASIC": # used by LDAP
            passman = request.HTTPPasswordMgrWithDefaultRealm()
            passman.add_password(None,
                                 self._parsed_org_url,
                                 self._username,
                                 self._password)
            handlers.append(request.HTTPBasicAuthHandler(passman))

        if self._auth == "DIGEST":
            passman = request.HTTPPasswordMgrWithDefaultRealm()
            passman.add_password(None,
                                 self._parsed_org_url,
                                 self._username,
                                 self._password)
            handlers.append(request.HTTPDigestAuthHandler(passman))

        elif self._auth == "IWA":
            if os.name == 'nt':
                try:
                    from .common._iwa import NtlmSspiAuthHandler, KerberosSspiAuthHandler

                    auth_NTLM = NtlmSspiAuthHandler()
                    auth_krb = KerberosSspiAuthHandler()

                    handlers.append(auth_NTLM)
                    handlers.append(auth_krb)

                except Error as err:
                    _log.error("pywin32 and kerberos-sspi packages are required for IWA authentication.")
                    _log.error("Please install them:\n\tconda install pywin32\n\tconda install kerberos-sspi")
                    _log.error(str(err))
            else:
                _log.error('The GIS uses Integrated Windows Authentication which is currently only supported on the Windows platform')

        elif self._auth == "PKI":
            handlers.append(HTTPSClientAuthHandler(self.key_file, self.cert_file))

        cj = cookiejar.CookieJar()
        handlers.append(request.HTTPCookieProcessor(cj))

        if not verify_cert or not self._verify_cert:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            handler = request.HTTPSHandler(context=ctx)
            handlers.append(handler)

        return handlers
    #----------------------------------------------------------------------

    def post(self, path, postdata=None, files=None, ssl=False, compress=True,
             is_retry=False, use_ordered_dict=False, add_token=True, verify_cert=True,
             token=DEFAULT_TOKEN, try_json=True, out_folder=None,
             file_name=None, force_bytes=False, add_headers=None):
        """ Returns result of an HTTP POST. Supports Multipart requests."""
        # prevent double encoding
        if not is_retry:
            path = quote(path, ':/')
        url = path
        if url.lower().find("https://") > -1 or\
           url.lower().find("http://") > -1:
            url = path
        elif len(url) == 0:
            url = self.baseurl
        elif (len(url) > 0 and url[0] == '/' ) == False and \
           self.baseurl.endswith('/') == False:
            url = "/{path}".format(path=url)

        if not url.startswith('http://') and \
           not url.startswith('https://'):
            url = self.baseurl + url

        if ssl or self.all_ssl:
            url = url.replace('http://', 'https://')
        #if verify_cert == False:
        #    import ssl
        #    ssl._create_default_https_context = ssl._create_unverified_context
        # Add the token if logged in
        if add_token:
            if token != DEFAULT_TOKEN: # use the provided token, if any
                if token is not None:
                    postdata['token'] = token
                else:
                    pass # no token, public access
            elif self.token is not None:
                postdata['token'] = self.token

        if _log.isEnabledFor(logging.DEBUG):
            msg = 'REQUEST: ' + url + ', ' + str(postdata)
            if files:
                msg += ', files=' + str(files)
            _log.debug(msg)

        # If there are files present, send a multipart request
        if files:
            #parsed_url = urlparse(url)
            mpf = MultiPartForm(param_dict=postdata, files=files)
            req = request.Request(url)
            body = mpf.make_result
            req.add_header('User-agent', self._useragent)
            req.add_header('Content-type', mpf.get_content_type())
            req.add_header('Content-length', len(body))
            if isinstance(add_headers, list):
                for ah in add_headers:
                    req.add_header(ah[0], ah[1])
            req.data = body
            headers = [('Referer', self._referer),
                       ('User-Agent', self._useragent),
                       ('Content-type', mpf.get_content_type()),
                       ('Content-length', len(body))]
            if isinstance(add_headers, list):
                for ah in add_headers:
                    headers.append(ah)
            if compress:
                headers.append(('Accept-encoding', 'gzip'))

            handlers = self.get_handlers(verify_cert)
            opener = request.build_opener(*handlers)

            opener.addheaders = headers

            resp = opener.open(req)
            resp_data, is_file = self._process_response(resp,
                                               out_folder=out_folder,
                                               file_name=file_name,
                                               force_bytes=force_bytes)
        # Otherwise send a normal HTTP POST request
        else:
            encoded_postdata = None
            if postdata:
                encoded_postdata = urlencode(postdata)
            headers = [('Referer', self._referer),
                       ('User-Agent', self._useragent)]
            if compress:
                headers.append(('Accept-encoding', 'gzip'))

            handlers = self.get_handlers(verify_cert)
            opener = request.build_opener(*handlers)

            opener.addheaders = headers
            #print("***"+url)
            resp = opener.open(url, data=encoded_postdata.encode())
            resp_data, is_file = self._process_response(resp,
                                               out_folder=out_folder,
                                               file_name=file_name,
                                               force_bytes=force_bytes)

        # Parse the response into JSON
        if _log.isEnabledFor(logging.DEBUG):
            _log.debug('RESPONSE: ' + url + ', ' + resp_data)
        # print(resp_data)

        # If is a file or we're not trying to parse to JSON, return response as is
        if is_file or not try_json:
            return resp_data

        if use_ordered_dict:
            resp_json = json.loads(resp_data, object_pairs_hook=OrderedDict)
        else:
            resp_json = json.loads(resp_data)


        # Check for errors, and handle the case where the token timed out
        # during use (and simply needs to be re-generated)
        try:
            if resp_json.get('error', None):

                errorcode = resp_json['error']['code'] if 'code' in resp_json['error'] else 0
                if errorcode == 498 and not is_retry:
                    _log.info('Token expired during post request, fetching a new '
                              + 'token and retrying')
                    self.logout()
                    newtoken = self.relogin()

                    self.token = newtoken
                    retry_token = None
                    if token != DEFAULT_TOKEN: # was provided a token, that has expired
                        newfedtoken = self.generate_portal_server_token(url)
                        retry_token = newfedtoken
                    else:
                        retry_token = newtoken

                    return self.post(path, postdata, files, ssl, compress, token=retry_token, verify_cert=verify_cert,
                                     is_retry=True)
                elif errorcode == 498:
                    raise RuntimeError('Invalid token')
                self._handle_json_error(resp_json['error'], errorcode)
                return None
        except AttributeError:
            # Top-level JSON object isnt a dict, so can't have an error
            pass

        return resp_json
    #----------------------------------------------------------------------
    def _get_content_type(self, filename):
        return mimetypes.guess_type(filename)[0] or 'application/octet-stream'
    #----------------------------------------------------------------------
    def _handle_json_error(self, error, errorcode):
        errormessage = error.get('message', 'Unknown Error')
        _log.error(errormessage)
        if 'details' in error and error['details'] is not None:
            for errordetail in error['details']:
                errormessage = errormessage + "\n" + errordetail
                _log.error(errordetail)

        errormessage = errormessage + "\n(Error Code: " + str(errorcode) +")"
        raise RuntimeError(errormessage)

class _StrictURLopener(request.FancyURLopener):
    def http_error_default(self, url, fp, errcode, errmsg, headers):
        if errcode != 200:
            raise HTTPError(url, errcode, errmsg, headers, fp)

def _normalize_url(url, charset='utf-8'):
    """ Normalizes a URL. Based on http://code.google.com/p/url-normalize."""
    def _clean(string):
        string = str(unquote(string), 'utf-8', 'replace')
        return unicodedata.normalize('NFC', string).encode('utf-8')

    default_port = {
        'ftp': 21,
        'telnet': 23,
        'http': 80,
        'gopher': 70,
        'news': 119,
        'nntp': 119,
        'prospero': 191,
        'https': 443,
        'snews': 563,
        'snntp': 563,
    }

    # if there is no scheme use http as default scheme
    if url[0] not in ['/', '-'] and ':' not in url[:7]:
        url = 'http://' + url


    # shebang urls support
    url = url.replace('#!', '?_escaped_fragment_=')

    # splitting url to useful parts
    scheme, auth, path, query, fragment = urlsplit(url.strip())
    (userinfo, host, port) = re.search('([^@]*@)?([^:]*):?(.*)', auth).groups()

    # Always provide the URI scheme in lowercase characters.
    scheme = scheme.lower()

    # Always provide the host, if any, in lowercase characters.
    host = host.lower()
    if host and host[-1] == '.':
        host = host[:-1]
    # take care about IDN domains
    host = host.decode(charset).encode('idna')  # IDN -> ACE

    # Only perform percent-encoding where it is essential.
    # Always use uppercase A-through-F characters when percent-encoding.
    # All portions of the URI must be utf-8 encoded NFC from Unicode strings
    path = quote(_clean(path), "~:/?#[]@!$&'()*+,;=")
    fragment = quote(_clean(fragment), "~")

    # note care must be taken to only encode & and = characters as values
    query = "&".join(["=".join([quote(_clean(t), "~:/?#[]@!$'()*+,;=") \
                                for t in q.split("=", 1)]) for q in query.split("&")])

    # Prevent dot-segments appearing in non-relative URI paths.
    if scheme in ["", "http", "https", "ftp", "file"]:
        output = []
        for part in path.split('/'):
            if part == "":
                if not output:
                    output.append(part)
            elif part == ".":
                pass
            elif part == "..":
                if len(output) > 1:
                    output.pop()
            else:
                output.append(part)
        if part in ["", ".", ".."]:
            output.append("")
        path = '/'.join(output)

    # For schemes that define a default authority, use an empty authority if
    # the default is desired.
    if userinfo in ["@", ":@"]:
        userinfo = ""

    # For schemes that define an empty path to be equivalent to a path of "/",
    # use "/".
    if path == "" and scheme in ["http", "https", "ftp", "file"]:
        path = "/"

    # For schemes that define a port, use an empty port if the default is
    # desired
    if port and scheme in list(default_port.keys()):
        if port.isdigit():
            port = str(int(port))
            if int(port) == default_port[scheme]:
                port = ''

    # Put it all back together again
    auth = (userinfo or "") + host
    if port:
        auth += ":" + port
    if url.endswith("#") and query == "" and fragment == "":
        path += "#"
    return urlunsplit((scheme, auth, path, query, fragment))

def _parse_hostname(url, include_port=False):
    """ Parses the hostname out of a URL."""
    if url:
        parsed_url = urlparse((url))
        return parsed_url.netloc if include_port else parsed_url.hostname

def _is_http_url(url):
    if url:
        return urlparse(url).scheme in ['http', 'https']

def _unpack(obj_or_seq, key=None, flatten=False):
    """ Turns a list of single item dicts in a list of the dict's values."""

    # The trivial case (passed in None, return None)
    if not obj_or_seq:
        return None

    # We assume it's a sequence
    new_list = []
    for obj in obj_or_seq:
        value = _unpack_obj(obj, key, flatten)
        new_list.extend(value)

    return new_list

def _unpack_obj(obj, key=None, flatten=False):
    try:
        if key:
            value = [obj.get(key)]
        else:
            value = list(obj.values())
    except AttributeError:
        value = [obj]

    # Flatten any lists if directed to do so
    if value and flatten:
        value = [item for sublist in value for item in sublist]

    return value

def _remove_non_ascii(s):
    return ''.join(i for i in s if ord(i) < 128)

def _tostr(obj):
    if not obj:
        return ''
    if isinstance(obj, list):
        return ', '.join(map(_tostr, obj))
    return str(obj)




# This function is a workaround to deal with what's typically described as a
# problem with the web server closing a connection. This is problem
# experienced with www.arcgis.com (first encountered 12/13/2012). The problem
# and workaround is described here:
# http://bobrochel.blogspot.com/2010/11/bad-servers-chunked-encoding-and.html
def _patch_http_response_read(func):
    def inner(*args):
        try:
            return func(*args)
        except http_client.IncompleteRead as e:
            return e.partial

    return inner
http_client.HTTPResponse.read = _patch_http_response_read(http_client.HTTPResponse.read)
