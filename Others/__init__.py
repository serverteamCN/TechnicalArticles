"""
The **gis** module provides an information model for GIS hosted
within ArcGIS Online or ArcGIS Enterprise.
This module provides functionality to manage
(create, read, update and delete) GIS users, groups and content. This module
is the most important and provides the entry point into the GIS.
"""
from __future__ import absolute_import

import base64
import datetime
import json
import locale
import logging
import os
import re
import tempfile
import zipfile
import configparser
from contextlib import contextmanager

import arcgis._impl.portalpy as portalpy
import arcgis.env
from arcgis._impl.common._mixins import PropertyMap
from arcgis._impl.common._utils import _DisableLogger
from arcgis._impl.connection import _is_http_url
from six.moves.urllib.error import HTTPError
_log = logging.getLogger(__name__)

class Error(Exception): pass

@contextmanager
def _tempinput(data):
    temp = tempfile.NamedTemporaryFile(delete=False)
    temp.write((bytes(data, 'UTF-8')))
    temp.close()
    yield temp.name
    os.unlink(temp.name)

def _lazy_property(fn):
    '''Decorator that makes a property lazy-evaluated.
    '''
    # http://stevenloria.com/lazy-evaluated-properties-in-python/
    attr_name = '_lazy_' + fn.__name__

    @property
    def _lazy_property(self):
        if not hasattr(self, attr_name):
            setattr(self, attr_name, fn(self))
        return getattr(self, attr_name)
    return _lazy_property

class GIS(object):
    """
    .. _gis:

    A GIS is representative of ArcGIS Online or ArcGIS Enterprise. The GIS object provides helper objects to manage
    (search, create, retrieve) GIS resources such as content, users and groups.

    Additionally, the GIS object has properties to query it's state, accessible using the properties attribute.

    The GIS provides a mapping widget that can be used in the Jupyter notebook environment for visualizing GIS content
    as well as the results of your analysis. To create a new map, call the map() method.
    """
    _server_list = None
    # admin = None
    # oauth = None
    def __init__(self, url=None, username=None, password=None, key_file=None, cert_file=None,
                 verify_cert=True, set_active=True, client_id=None, profile=None):
        """
        Constructs a GIS object given a url and user credentials to ArcGIS Online
        or an ArcGIS Portal. User credentials can be passed in using username/password
        pair, or key_file/cert_file pair (in case of PKI). Supports built-in users, LDAP,
        PKI, Integrated Windows Authentication (using NTLM and Kerberos) and Anonymous access.

        If no url is provided, ArcGIS Online is used. If username/password
        or key/cert files are not provided, logged in user credentials (IWA) or anonymous access is used.

        A persisted profile for the GIS can be created by giving the GIS and it's authorization credentials and
        specifying a profile name. The profile is stored in the users home directory in a config file named .arcgisprofile
        The profile is NOT ENCRYPTED and you need to take care to protect the saved profile using operating system security
        or other means. Once a profile has been saved, passing the profile parameter by itself uses the authorization credentials
        saved in the configuration file by that profile name.
        """
        from arcgis._impl.tools import _Tools

        if profile is not None:
            if url is None and username is None and password is None and \
                key_file is None and cert_file is None and \
                client_id is None:
                # read
                cfg = os.path.expanduser("~") + '/.arcgisprofile'
                config = configparser.ConfigParser()
                config.read(cfg)

                if profile in config:
                    url = rot13(config[profile].get('url'))
                    username = rot13(config[profile].get('username'))
                    password = rot13(config[profile].get('password'))
                    key_file = rot13(config[profile].get('key_file'))
                    cert_file = rot13(config[profile].get('cert_file'))
                    client_id = rot13(config[profile].get('client_id'))
                else:
                    raise RuntimeError('No such profile was found.')
            else:
                # write
                config = configparser.ConfigParser()
                config[profile] = {
                }

                if url is not None:
                    config[profile]['url']= rot13(url)
                if username is not None:
                    config[profile]['username']= rot13(username)
                if password is not None:
                    config[profile]['password']= rot13(password)
                if key_file is not None:
                    config[profile]['key_file']= rot13(key_file)
                if cert_file is not None:
                    config[profile]['cert_file']= rot13(cert_file)
                if client_id is not None:
                    config[profile]['client_id']= rot13(client_id)

                cfg = os.path.expanduser("~") + '/.arcgisprofile'
                with os.fdopen(os.open(cfg, os.O_WRONLY | os.O_CREAT, 0o600), 'w') as configfile:
                    config.write(configfile)

        if url is None:
            url = "http://www.arcgis.com"

        if username is not None and password is None:
            from getpass import getpass
            password = getpass('Enter password: ')

        self._url = url
        self._username = username
        self._password = password
        self._key_file = key_file
        self._cert_file = cert_file
        self._portal = None
        self._con = None
        self._verify_cert = verify_cert
        self._client_id = client_id
        self._datastores_list = None
        self._portal = portalpy.Portal(self._url, self._username, self._password, self._key_file, self._cert_file,
                                       verify_cert=self._verify_cert, client_id=self._client_id)
        if url.lower().find("www.arcgis.com") > -1 and \
           self._portal.is_logged_in:
            from six.moves.urllib_parse import urlparse
            props = self._portal.get_properties(force=True)
            url = "%s://%s.%s" % (urlparse(self._url).scheme,
                                  props['urlKey'],
                                  props['customBaseUrl'])
            self._url = url
            self._portal = portalpy.Portal(url,
                                           self._username,
                                           self._password,
                                           self._key_file,
                                           self._cert_file,
                                           verify_cert=self._verify_cert,
                                           client_id=self._client_id)
        self._lazy_properties = PropertyMap(self._portal.get_properties(force=False))

        if self._url.lower() == "pro":
            self._url = self._portal.url

        self._con = self._portal.con

        if self._con._auth.lower() != 'anon' and \
           self._con._auth is not None and \
           hasattr(self.users.me, 'role') and \
           self.users.me.role == "org_admin":
            if self.properties.isPortal == True:
                from .admin.portaladmin import PortalAdminManager
                self.admin = PortalAdminManager(url="%s/portaladmin" % self._portal.url,
                                                gis=self)
            else:
                from .admin.agoladmin import AGOLAdminManager
                self.admin = AGOLAdminManager(gis=self)
        self._tools = _Tools(self)
        if set_active:
            arcgis.env.active_gis = self

    #@property
    #def _servers(self):
        #"""
        #The list of server objects for servers federated with the GIS.
        #"""
        #if self._con._auth is None or \
           #self._con._auth.lower() == "anon":
            #return None
        #from arcgis.gis.server import Server
        #if self._server_list:
            #return self._server_list

        #self._server_list = []
        #try:
            #is_portal = self.properties.isPortal
            #if self.properties.isPortal == False:
                #res = self._portal.con.post("portals/self/urls", {"f": "json"})
                #if 'urls' in res:
                    #urls = res['urls']
                    #servers = []
                    #for stype in ['features', 'tiles']:
                        #if stype in urls:
                            #for scheme in ['http', 'https']:
                                #if scheme in urls[stype]:
                                    #for url in urls[stype][scheme]:
                                        #surl = "{scheme}://{url}/{portalid}/ArcGIS/rest/services".format(
                                            #scheme=scheme,
                                            #portalid=self.properties.id,
                                            #url=url)
                                        #admin_surl = "{scheme}://{url}/{portalid}/ArcGIS/rest/admin".format(
                                            #scheme=scheme,
                                            #portalid=self.properties.id,
                                            #url=url)
                                        #servers.append(
                                            ##surl
                                            #Server(url=surl,
                                                   #gis=self,
                                                   #is_agol=True)
                                        #)
                    #self._server_list = servers
            #else:
                #res = self._portal.con.post("portals/self/servers", {"f": "json"})
                #servers = res['servers']
                #admin_url = None
                #for server in servers:
                    #admin_url = server['adminUrl']
                    #try:
                        #self._server_list.append(Server(url=admin_url, gis=self))
                    #except:
                        #_log.error("Could not access the servers at: " + admin_url)

        #except:
            #_log.error("Could not access the servers associated with this site.")
        #return self._server_list

    @_lazy_property
    def users(self):
        """
        The resource manager for GIS users
        """
        return UserManager(self)

    @_lazy_property
    def groups(self):
        """
        The resource manager for GIS groups
        """
        return GroupManager(self)

    @_lazy_property
    def content(self):
        """
        The resource manager for GIS content
        """
        return ContentManager(self)

    # @_lazy_property
    # def ux(self):
    #     return UX(self)

    @_lazy_property
    def _datastores(self):
        """
        The list of datastores resource managers for sites federated with the GIS.
        """
        if self._datastores_list is not None:
            return self._datastores_list

        self._datastores_list = []
        try:
            res = self._portal.con.post("portals/self/servers", {"f": "json"})

            servers = res['servers']
            admin_url = None
            for server in servers:
                admin_url = server['adminUrl'] + '/admin'
                self._datastores_list.append(DatastoreManager(self, admin_url, server))
        except:
            pass
        return self._datastores_list

    @_lazy_property
    def properties(self):
        """
        The properties of the GIS
        """
        return PropertyMap(self._get_properties(force=True))

    def update_properties(self, properties_dict):
        """Updates the GIS's properties from those in properties_dict"""
        postdata = self._portal._postdata()
        postdata.update(properties_dict)

        resp = self._portal.con.post('portals/self/update', postdata)
        if resp:
            self._lazy_properties = PropertyMap(self._portal.get_properties(force=True))
            # delattr(self, '_lazy_properties') # force refresh of properties when queried next
            return resp.get('success')

    def __str__(self):
        return 'GIS @ ' + self._url

    def _repr_html_(self):
        """
        HTML Representation for IPython Notebook
        """
        return 'GIS @ <a href="' + self._url + '">' + self._url + '</a>'

    def _get_properties(self, force=False):
        """ Returns the portal properties (using cache unless force=True). """
        return self._portal.get_properties(force)

    def map(self, location=None, zoomlevel=None):
        """Creates a map widget centered at the location (Address or (lat, long) tuple)
        with the specified zoom-level(integer). If an Address is provided, it is geocoded
        using the GIS's configured geocoders and if a match is found, the geographic
        extent of the matched address is used as the map extent. If a zoomlevel is also
        provided, the map is centered at the matched address instead and the map is zoomed
        to the specified zoomlevel.

        Note: The map widget is only supported within Jupyter Notebook.
        """
        try:
            from arcgis.widgets import MapView
            from arcgis.geocoding import get_geocoders, geocode
        except Error as err:
            _log.error("ipywidgets packages is required for the map widget.")
            _log.error("Please install it:\n\tconda install ipywidgets")

        if isinstance(location, Item) and location.type == 'Web Map':
            mapwidget = MapView(gis=self, item=location)
        else:
            mapwidget = MapView(gis=self)

            # Geocode the location
            if isinstance(location, str):
                for geocoder in get_geocoders(self):
                    locations = geocode(location, out_sr=4326, max_locations=1, geocoder=geocoder)
                    if len(locations) > 0:
                        if zoomlevel is not None:
                            loc = locations[0]['location']
                            mapwidget.center = loc['y'], loc['x']
                            mapwidget.zoom = zoomlevel
                        else:
                            mapwidget.extent = locations[0]['extent']
                        break

            # Center the map at the location
            elif isinstance(location, (tuple, list)):
                if all(isinstance(el, list) for el in location):
                    extent = {
                        'xmin': location[0][0],
                        'ymin': location[0][1],
                        'xmax': location[1][0],
                        'ymax': location[1][1]
                    }
                    mapwidget.extent = extent
                else:
                    mapwidget.center = location

            elif isinstance(location, dict): # geocode result
                if 'extent' in location and zoomlevel is None:
                    mapwidget.extent = location['extent']
                elif 'location' in location:
                    mapwidget.center = location['location']['y'], location['location']['x']
                    if zoomlevel is not None:
                        mapwidget.zoom = zoomlevel

            elif location is not None:
                print("location must be an address(string) or (lat, long) pair as a tuple")

        if zoomlevel is not None:
            mapwidget.zoom = zoomlevel

        return mapwidget

class _PortalResourceManager(object):
    """Helper class to manage portal resources in a GIS"""

    def __init__(self, gis):
        """Creates helper object to manage custom roles in the GIS"""
        self._gis = gis
        self._portal = gis._portal
        self._is_portal = self._gis.properties.isPortal


    def add(self, key=None, path=None, text=None, **kwargs):
        """
        The add resource operation allows the administrator to add a file
        resource, for example, the organization's logo or custom banner.
        The resource can be used by any member of the organization. File
        resources use storage space from your quota and are scanned for
        viruses.

        Parameters:
         :key: look up key for file
         :path: file path to the resource to upload
         :text: text value to add to the site's resources
         :access: (optional) sets the resources access level the default
         is public. Values: public, org, orgprivate
        Output:
         boolean
        """
        access = kwargs.pop("access", None)
        files = None
        if key is None and path:
            key = os.path.basename(path)
        elif key is None and path is None:
            raise ValueError("key must be populated is path is null")
        url = "portals/self/addresource"
        postdata = {
            "f" : "json",
                "key" : key,
        }
        if path:
            files = {
                'file' : path
            }
        if text:
            if isinstance(text, dict):
                postdata['text'] = json.dumps(text)
            elif isinstance(text, str):
                from arcgis._impl.common._utils import _to_utf8
                postdata['text'] = _to_utf8(text)
        else:
            if self._portal.is_arcgisonline == False:
                postdata['text'] = ""
        if self._is_portal == False:
            url = "portals/%s/addResource" % self._gis.properties.id
            if text is None:
                postdata['text'] = ""
            if access:
                postdata['access'] = access
            else:
                postdata['access'] = 'public'

        resp = self._portal.con.post(url,
                                     postdata, files=files)
        if 'success' in resp:
            return resp['success']
        return resp

    def delete(self, key):
        """
        The Remove Resource operation allows the administrator to remove
        a file resource.

        Parameters:
         :key: The name of the resource to delete.
        Output:
         boolean
        """
        postdata = {
                "f" : "json",
                "key" : key,
            }
        resp = self._portal.con.post('portals/self/removeresource',
                                     postdata)
        if 'success' in resp:
            return resp['success']
        return resp

    #----------------------------------------------------------------------
    def list(self, start=1, num=100):
        """
        returns a list of resources uploaded to portal.  The items can be
        images, files and other content used to stylize and modify a
        portal's appearance.
        """
        postdata = {
            "f" : "json",
            'start' : start,
            'num' : num
        }
        resp = self._portal.con.post('portals/self/resources',
                                     postdata)
        if 'resources' in resp:
            return resp['resources']
        return resp


###########################################################################
class Datastore(dict):
    """
    Represents a datastore (folder, database or bigdata fileshare) within the GIS's data store
    """
    def __init__(self, datastore, path):
        dict.__init__(self)
        self._datastore = datastore
        self._portal = datastore._portal
        self._admin_url = datastore._admin_url

        self.datapath = path


        params = { "f" : "json" }
        path = self._admin_url + "/data/items" + self.datapath

        datadict = self._portal.con.post(path, params, verify_cert=False)

        if datadict:
            self.__dict__.update(datadict)
            super(Datastore, self).update(datadict)

    def __getattr__(self, name): # support group attributes as group.access, group.owner, group.phone etc
        try:
            return dict.__getitem__(self, name)
        except:
            raise AttributeError("'%s' object has no attribute '%s'" % (type(self).__name__, name))

    def __getitem__(self, k): # support group attributes as dictionary keys on this object, eg. group['owner']
        try:
            return dict.__getitem__(self, k)
        except KeyError:
            params = { "f" : "json" }
            path = self._admin_url + "/data/items" + self.datapath

            datadict = self._portal.con.post(path, params, verify_cert=False)
            super(Datastore, self).update(datadict)
            self.__dict__.update(datadict)
            return dict.__getitem__(self, k)

    def __str__(self):
        return self.__repr__()
        # state = ["   %s=%r" % (attribute, value) for (attribute, value) in self.__dict__.items()]
        # return '\n'.join(state)

    def __repr__(self):
        return '<%s title:"%s" type:"%s">' % (type(self).__name__, self.path, self.type)

    @property
    def manifest(self):
        """
        The manifest resource for bigdata fileshares,
        """
        data_item_manifest_url = self._admin_url + '/data/items' + self.datapath + "/manifest"

        params = {
            'f': 'json',
        }
        res = self._portal.con.post(data_item_manifest_url, params, verify_cert=False)
        return res

    @manifest.setter
    def manifest(self, value):
        """
        Updates the manifest resource for bigdata fileshares
        """
        manifest_upload_url =  self._admin_url + '/data/items' + self.datapath + '/manifest/update'

        with _tempinput(json.dumps(value)) as tempfilename:
            # Build the files list (tuples)
            files = []
            files.append(('manifest', tempfilename, os.path.basename(tempfilename)))

            postdata = {
                'f' : 'pjson'
            }

            resp = self._portal.con.post(manifest_upload_url, postdata, files, verify_cert=False)

            if resp['status'] == 'success':
                return True
            else:
                print(str(resp))
                return False

    @property
    def ref_count(self):
        """
        The total number of references to this data item that exist on the server. You can use this property to determine if this data item can be safely deleted (or taken down for maintenance).
        """
        data_item_manifest_url = self._admin_url + '/data/computeTotalRefCount'

        params = {
            'f': 'json',
            'itemPath': self.datapath
        }
        res = self._portal.con.post(data_item_manifest_url, params, verify_cert=False)
        return res["totalRefCount"]

    def delete(self):
        """
        Unregisters this data item from the data store
        """
        params = {
            "f" : "json" ,
            "itempath" : self.datapath,
            "force": True
        }
        path = self._admin_url + "/data/unregisterItem"

        resp = self._portal.con.post(path, params, verify_cert=False)
        if resp:
            return resp.get('success')
        else:
            return False

    def update(self, item):
        """
        Edits this data item to update its connection information.

        Input
            item - the dict representation of the updated item
        Output:
              True if successful
        """
        params = {
            "f" : "json" ,
            "item" : item
        }
        path = self._admin_url +  "/data/items" + self.datapath +  "/edit"

        resp = self._portal.con.post(path, params, verify_cert=False)
        if resp ['status'] == 'success':
            return True
        else:
            return False

    def validate(self):
        """
        Validates that this data item's path (for file shares) or connection string (for databases)
        is accessible to every server node in the site

        Output:
              True if successful
        """
        params = { "f" : "json" }
        path = self._admin_url + "/data/items" + self.datapath

        datadict = self._portal.con.post(path, params, verify_cert=False)

        params = {
            "f" : "json",
            "item": datadict
        }
        path = self._admin_url + "/data/validateDataItem"

        res = self._portal.con.post(path, params, verify_cert=False)
        return res['status'] == 'success'

    @property
    def datasets(self):
        """
        Returns the datasets in the data store (currently implemented for big data file shares.)
        """
        data_item_manifest_url = self._admin_url + '/data/items' + self.datapath + "/manifest"

        params = {
            'f': 'json',
        }
        res = self._portal.con.post(data_item_manifest_url, params, verify_cert=False)

        return res['datasets']

class DatastoreManager(object):
    """
    Helper class for managing the GIS data stores in on-premises ArcGIS Portals.
    This class is not created by users directly.
    Instances of this class are returned from arcgis.geoanalytics.get_datastores() and
    arcgis.raster.analytics.get_datastores() functions to get the corresponding datastores.
    Users call methods on this 'datastores' object to manage the datastores in a site federated with the portal.
    """
    def __init__(self, gis, admin_url, server):
        self._gis = gis
        self._portal = gis._portal
        self._admin_url = admin_url
        self._server = server

    def __str__(self):
        return '<%s for %s>' % (type(self).__name__, self._admin_url)

    def __repr__(self):
        return '<%s for %s>' % (type(self).__name__, self._admin_url)

    @property
    def config(self):
        """
        The data store configuration properties affect the behavior of the data holdings of the server. The properties include:
        blockDataCopy—When this property is False, or not set at all, copying data to the site when publishing services from a client application is allowed. This is the default behavior.
        When this property is True, the client application is not allowed to copy data to the site when publishing. Rather, the publisher is required to register data items through which the service being published can reference data. Values: True | False
        Note:
        If you specify the property as True, users will not be able to publish geoprocessing services and geocode services from composite locators. These service types require data to be copied to the server. As a workaround, you can temporarily set the property to False, publish the service, and then set the property back to True.
        """
        params = {"f" : "json"}
        path = self._admin_url + "/data/config"
        res = self._portal.con.post(path, params, verify_cert=False)
        return res

    @config.setter
    def config(self, value):
        """
        The data store configuration properties affect the behavior of the data holdings of the server. The properties include:
        blockDataCopy—When this property is False, or not set at all, copying data to the site when publishing services from a client application is allowed. This is the default behavior.
        When this property is True, the client application is not allowed to copy data to the site when publishing. Rather, the publisher is required to register data items through which the service being published can reference data. Values: True | False
        Note:
        If you specify the property as True, users will not be able to publish geoprocessing services and geocode services from composite locators. These service types require data to be copied to the server. As a workaround, you can temporarily set the property to False, publish the service, and then set the property back to True.
        """
        params = {"f" : "json"}
        params['datastoreConfig'] = value
        path = self._admin_url + "/data/config/update"
        res = self._portal.con.post(path, params)
        return res

    def add_folder(self,
                   name,
                   server_path,
                   client_path=None):
        """
        Registers a folder with the data store.
        Input
            name - unique fileshare name on the server
            server_path - the path to the folder from the server (and client, if shared path)
            client_path - if folder is replicated, the path to the folder from the client
            if folder is shared, don't set this parameter
        Output:
              the data item is registered successfully, None otherwise
        """
        conn_type = "shared"
        if client_path is not None:
            conn_type = "replicated"

        item = {
            "type" : "folder",
            "path" : "/fileShares/" + name,
            "info" : {
                "path" : server_path,
                "dataStoreConnectionType" : conn_type
            }
        }

        if client_path is not None:
            item['clientPath'] = client_path

        params = {
            "f" : "json",
            "item" : item
        }
        path = self._admin_url + "/data/registerItem"
        res = self._portal.con.post(path, params, verify_cert=False)
        if res['status'] == 'success' or res['status'] == 'exists':
            return Datastore(self, "/fileShares/" + name)
        else:
            print(str(res))
            return None

    def add_bigdata(self,
                    name,
                    server_path=None):
        """
        Registers a bigdata fileshare with the data store.
        Input
            name - unique bigdata fileshare name on the server
            server_path - the path to the folder from the server
        Output:
              the data item if registered successfully, None otherwise
        """
        output = None
        path = self._admin_url + "/data/registerItem"

        pattern = r'\\\\[a-zA-Z]+'
        if re.match(pattern, server_path) is not None:  # starts with double backslash, double the backslashes
            server_path = server_path.replace('\\', '\\\\')

        path_str = '{"path":"' + server_path + '"}'
        params = {
            'f': 'json',
            'item' : json.dumps({
                "path": "/bigDataFileShares/" + name,
                "type": "bigDataFileShare",

                "info": {
                    "connectionString": path_str,
                    "connectionType": "fileShare"
                }
            })
        }
        res = self._portal.con.post(path, params, verify_cert=False)

        if res['status'] == 'success' or res['status'] == 'exists':
            output = Datastore(self, "/bigDataFileShares/" + name)

        if res['success']:
            print("Created Big Data file share for " + name)
        elif res['status'] == 'exists':
            print("Big Data file share exists for " + name)

        return output

    def add_database(self,
                     name,
                     conn_str,
                     client_conn_str=None,
                     conn_type="shared"):
        """
        Registers a database with the data store.
        Input
            name - unique database name on the server
            conn_str - the path to the folder from the server (and client, if shared or serverOnly database)
            client_conn_str: connection string for client to connect to replicated enterprise database>
            conn_type - "<shared|replicated|serverOnly>"
        Output:
            the data item is registered successfully, None otherwise
        """

        item = {
            "type" : "egdb",
            "path" : "/enterpriseDatabases/" + name,
            "info" : {
                "connectionString" : conn_str,
                "dataStoreConnectionType" : conn_type
            }
        }

        if client_conn_str is not None:
            item['info']['clientConnectionString'] = client_conn_str

        is_managed = False
        if conn_type == "serverOnly":
            is_managed = True

        item['info']['isManaged'] = is_managed

        params = {
            "f" : "json",
            "item" : item
        }
        path = self._admin_url + "/data/registerItem"
        res = self._portal.con.post(path, params, verify_cert=False)
        if res['status'] == 'success' or res['status'] == 'exists':
            return Datastore(self, "/enterpriseDatabases/" + name)
        else:
            print(str(res))
            return None

    def add(self,
            name,
            item):
        """
        Registers a new data item with the data store.
        Input
            item - The disct representing the data item.
            See http://resources.arcgis.com/en/help/arcgis-rest-api/index.html#//02r3000001s9000000
        Output:
              True if the data item is registered successfully, False otherwise
        """
        params = {
            "f" : "json"
        }

        params['item'] = item

        path = self._admin_url + "/data/registerItem"
        res = self._portal.con.post(path, params, verify_cert=False)
        if res['status'] == 'success' or res['status'] == 'exists':
            return Datastore(self, "/enterpriseDatabases/" + name)
        else:
            print(str(res))
            return None

    def get(self, path):
        """ Returns the data item object at the given path

        Arguments
            path        required string, the data item path
        :return:
            None if the data item is not found at that path and the data item object if its found
        """
        params = { "f" : "json" }
        urlpath = self._admin_url + "/data/items" + path

        datadict = self._portal.con.post(urlpath, params, verify_cert=False)
        if 'status' not in datadict:
            return Datastore(self, path)
        else:
            print(datadict['messages'])
            return None

    def search(self, parent_path=None, ancestor_path=None,
               types=None, id=None):
        """
           You can use this operation to search through the various data
           items registered in the server's data store. Searching without specifying the parent_path and other parameters returns a lists of all registered data items
           Inputs:
              parentPath - The path of the parent under which to find items. To get the root data items, pass '/'
              ancestorPath - The path of the ancestor under which to find
                             items.
              types - A comma separated filter for the type of the items. Types include folder, egdb, bigDataFileShare, datadir
              id - A filter to search by the ID of the item

            :return:
            Returns a list of data items matching the specified query
        """
        params = {
            "f" : "json",
        }
        if parent_path is None and ancestor_path is None and types is None and id is None:
            ancestor_path = '/'
        if parent_path is not None:
            params['parentPath'] = parent_path
        if ancestor_path is not None:
            params['ancestorPath'] = ancestor_path
        if types is not None:
            params['types'] = types
        if id is not None:
            params['id'] = id


        path = self._admin_url + "/data/findItems"


        dataitems = []

        res = self._portal.con.post(path, params, verify_cert=False)
        for item in res['items']:
            dataitems.append(Datastore(self, item['path']))
        return dataitems

    def validate(self):
        """
        Validates all items in the datastore and returns True if validated.

        In order for a data item to be registered and used successfully within the GIS's data store,
        you need to make sure that the path (for file shares) or connection string (for databases)
        is accessible to every server node in the site. To validate all registered data items all
        at once, you can invoke this operation.
        """
        params = {"f" : "json"}
        path = self._admin_url + "/data/validateAllDataItems"
        res = self._portal.con.post(path, params, verify_cert=False)
        return res['status'] == 'success'
###########################################################################
class UserManager(object):
    """
    Helper class for managing GIS users. This class is not created by users directly.
    An instance of this class, called 'users', is available as a property of the Gis object.
    Users call methods on this 'users' object to manipulate (create, get, search...) users.
    """
    def __init__(self, gis):
        self._gis = gis
        self._portal = gis._portal

    def create(self, username, password, firstname, lastname, email, description=None, role='org_user',
               provider='arcgis', idp_username=None, level=2):
        """ This operation is used to pre-create built-in or enterprise accounts within the portal,
        or built-in users in an ArcGIS Online organization account.

        The provider parameter is used to indicate the type of user account. Only an administrator
        can call this method.

        To create a viewer account, choose role='org_viewer' and level=1

        .. note:
            When Portal for ArcGIS is connected to an enterprise identity store, enterprise users sign
            into portal using their enterprise credentials. By default, new installations of Portal for
            ArcGIS do not allow accounts from an enterprise identity store to be registered to the portal
            automatically. Only users with accounts that have been pre-created can sign in to the portal.
            Alternatively, you can configure the portal to register enterprise accounts the first time
            the user connects to the website.

        ================  ===============================================================================
        **Argument**      **Description**
        ----------------  -------------------------------------------------------------------------------
        username          required string, must be unique in the Portal,
                          >=6 characters, =<24 characters
        ----------------  -------------------------------------------------------------------------------
        password          required string, must be >= 8 characters. This is a required parameter only if
                          the provider is arcgis; otherwise, the password parameter is ignored.
                          If creating an account in an ArcGIS Online org, it can be set as None to let
                          the user set their password by clicking on a link that is emailed to him/her.
        ----------------  -------------------------------------------------------------------------------
        firstname         required string, the first name for the user
        ----------------  -------------------------------------------------------------------------------
        lastname          required string, the last name for the user
        ----------------  -------------------------------------------------------------------------------
        email             required string, must be an email address
        ----------------  -------------------------------------------------------------------------------
        description       An optional description string for the user account.
        ----------------  -------------------------------------------------------------------------------
        role              The role for the user account. The default value is org_user.
                          Values: org_user | org_publisher | org_admin | org_viewer
        ----------------  -------------------------------------------------------------------------------
        provider          The provider for the account. The default value is arcgis.
                          Values: arcgis | enterprise
        ----------------  -------------------------------------------------------------------------------
        idp_username       The name of the user as stored by the enterprise user store. This parameter is
                          only required if the provider parameter is enterprise.
        ----------------  -------------------------------------------------------------------------------
        level             The account level.
                          See http://server.arcgis.com/en/portal/latest/administer/linux/roles.htm
        ================  ===============================================================================

        :return:
            the user, if created, else None

        """
        #map role parameter of a viewer to the internal value for org viewer.
        if role == 'org_viewer':
            role = 'iAAAAAAAAAAAAAAA'

        if self._gis._portal.is_arcgisonline:
            email_text = '''<html><body><p>''' + self._gis.properties.user.fullName + \
                         ''' has invited you to join an ArcGIS Online Organization, ''' + self._gis.properties.name + \
                         '''</p>
<p>Please click this link to finish setting up your account and establish your password: <a href="https://www.arcgis.com/home/newuser.html?invitation=@@invitation.id@@">https://www.arcgis.com/home/newuser.html?invitation=@@invitation.id@@</a></p>
<p>Note that your account has already been created for you with the username, <strong>@@touser.username@@</strong>.  </p>
<p>If you have difficulty signing in, please contact ''' + self._gis.properties.user.fullName + \
                         '(' + self._gis.properties.user.email + '''). Be sure to include a description of the problem, the error message, and a screenshot.</p>
<p>For your reference, you can access the home page of the organization here: <br>''' + self._gis.properties.user.fullName + '''</p>
<p>This link will expire in two weeks.</p>
<p style="color:gray;">This is an automated email. Please do not reply.</p>
</body></html>'''

            params = {
                'f': 'json',
                'invitationList' : {'invitations' : [ {
                    'username': username,
                    'firstname': firstname,
                    'lastname': lastname,
                    'fullname': firstname + ' ' + lastname,
                    'email': email,
                    'role': role,
                    'level': level
                } ] },
                'subject' : 'An invitation to join an ArcGIS Online organization, ' + self._gis.properties.name,
                'html' : email_text
            }

            if password is not None:
                params['invitationList']['invitations'][0]['password'] = password

            resp = self._portal.con.post('portals/self/invite', params, ssl=True)
            if resp and resp.get('success'):
                if username in resp['notInvited']:
                    print('Unable to create ' + username)
                    _log.error('Unable to create ' + username)
                    return None
                else:
                    return self.get(username)
        else:
            createuser_url = self._portal.url + "/portaladmin/security/users/createUser"
            #print(createuser_url)
            params = {
                'f': 'json',
                'username' : username,
                'password' : password,
                'firstname' : firstname,
                'lastname' : lastname,
                'email' : email,
                'description' : description,
                'role' : role,
                'provider' : provider,
                'idpUsername' : idp_username,
                'level' : level
            }
            self._portal.con.post(createuser_url, params)
            return self.get(username)


    def signup(self, username, password, fullname, email):
        """ Signs up users to an instance of Portal for ArcGIS.

        .. note:
            This method only applies to Portal and not ArcGIS
            Online.  This method can be called anonymously, but
            keep in mind that self-signup can also be disabled
            in a Portal.  It also only creates built-in
            accounts, it does not work with enterprise
            accounts coming from ActiveDirectory or your
            LDAP.

        ================  ========================================================
        **Argument**      **Description**
        ----------------  --------------------------------------------------------
        username          required string, must be unique in the Portal,
                          >4 characters
        ----------------  --------------------------------------------------------
        password          required string, must be >= 8 characters.
        ----------------  --------------------------------------------------------
        fullname          required string, name of the user
        ----------------  --------------------------------------------------------
        email             required string, must be an email address
        ================  ========================================================

        :return:
            the user, if created, else None

        """
        success = self._portal.signup(username, password, fullname, email)
        if success:
            return User(self._gis, username)
        else:
            return None

    def get(self, username):
        """ Returns the user object for the specified username.

        Arguments
            username        required string, the username whose user object you want.
        :return:
            None if the user is not found and returns a user object if the user is found
        """
        try:
            with _DisableLogger():
                user = self._portal.get_user(username)
        except RuntimeError as re:
            if re.args[0].__contains__("User does not exist or is inaccessible"):
                return None
            else:
                raise re

        if user is not None:
            return User(self._gis, user['username'], user)
        return None

    def search(self, query=None, sort_field='username', sort_order='asc', max_users=100, outside_org=False):
        """ Searches portal users.

        Returns a list of users matching the specified query

        .. note::
            A few things that will be helpful to know.

            1. The query syntax has quite a few features that can't
               be adequately described here.  The query syntax is
               available in ArcGIS help.  A short version of that URL
               is http://bitly.com/1fJ8q31.

            2. Searching without specifying a query parameter returns
               a list of all users in your organization.

            3. Most of the time when searching users you want to
               search within your organization in ArcGIS Online
               or within your Portal.  As a convenience, the method
               automatically appends your organization id to the query by
               default.  If you don't want the API to append to your query
               set outside_org to True.  If you use this feature with an
               OR clause such as field=x or field=y you should put this
               into parenthesis when using outside_org.

        ================  ========================================================
        **Argument**      **Description**
        ----------------  --------------------------------------------------------
        query             optional string, query string.  See notes. pass None
                          to get list of all users in the org
        ----------------  --------------------------------------------------------
        sort_field        optional string, valid values can be username or created
        ----------------  --------------------------------------------------------
        sort_order        optional string, valid values are asc or desc
        ----------------  --------------------------------------------------------
        max_users         optional int, maximum number of users returned
        ----------------  --------------------------------------------------------
        outside_org       optional boolean, controls whether to search outside
                          your org (default is False)
        ================  ========================================================

        :return:
            A list of users:
        """
        if query is None:
            users = self._portal.get_org_users(max_users)
            return [User(self._gis, u['username'], u) for u in users]
        else:
            userlist = []

            users = self._portal.search_users(query, sort_field, sort_order, max_users, outside_org)
            for user in users:
                userlist.append(User(self._gis, user['username'], user))
            return userlist

        #TODO: remove org users, invite users

    @property
    def me(self):
        """ Returns the logged in user
        """
        meuser = self._portal.logged_in_user()
        if meuser is not None:
            return User(self._gis, meuser['username'], meuser)
        else:
            return None

    @property
    def roles(self):
        """Helper object to manage custom roles for users"""
        return RoleManager(self._gis)


class RoleManager(object):
    """Helper class to manage custom roles for users in a GIS"""

    def __init__(self, gis):
        """Creates helper object to manage custom roles in the GIS"""
        self._gis = gis
        self._portal = gis._portal


    def create(self, name, description, privileges=None):
        """Creates and returns a custom role with the specified parameters"""
        if self.exists(role_name=name) == False:
            role_id = self._portal.create_role(name, description)
            if role_id is not None:
                role_data = {
                  "id": role_id,
                  "name": name,
                  "description": description
                }
                role = Role(self._gis, role_id, role_data)
                role.privileges = privileges
                return role
            else:
                return None
        else:
            n = str(name.lower())
            roles = [r for r in self.all() \
                     if r.name.lower() == n]
            return roles[0]
        return None

    def exists(self, role_name):
        """
        Checks to see if a role exists by it's name
        :role_name: name of the role to look up
        Returns:
         boolean
        """
        for role in self.all():
            if role.name.lower() == role_name.lower():
                return True
        return False

    def all(self, max_roles=1000):
        """
        Returns list of all roles in the GIS
        :param max_roles: the maximum number of roles to be returned
        :return: list of all roles in the GIS
        """
        roles = self._portal.get_org_roles(max_roles)
        return [Role(self._gis, role['id'], role) for role in roles]


    def get_role(self, role_id):
        """
        Returns the role with the specified role id. Returns list of all roles in the
        GIS if a role_id is not specified
        :param role_id: the role id of the role to get. Leave None to get all roles
        :return: the role with the specified role id or a list of all roles
        """
        role = self._portal.con.post('portals/self/roles/' + role_id, self._portal._postdata())
        return Role(self._gis, role['id'], role)


class Role(object):
    """A custom role in the GIS"""
    def __init__(self, gis, role_id, role):
        """Create a custom role"""
        self._gis = gis
        self._portal = gis._portal
        self.role_id = role_id
        if role is not None:
            self._name = role['name']
            self._description = role['description']

    def __repr__(self):
        return '<Role name: ' + self.name + ', description: ' + self.description + '>'

    def ___str___(self):
        return 'Custom Role name: ' + self.name + ', description: ' + self.description

    @property
    def name(self):
        """Name of the custom role"""
        return self._name

    @name.setter
    def name(self, value):
        """Name of the custom role"""
        self._name = value
        self._update_role()

    @property
    def description(self):
        """Description of the custom role"""
        return self._description

    @description.setter
    def description(self, value):
        """Description of the custom role"""
        self._description = value
        self._update_role()

    def _update_role(self):
        """Updates the name or description of this role"""
        postdata = self._portal._postdata()
        postdata['name'] = self._name
        postdata['description'] = self._description

        resp = self._portal.con.post('portals/self/roles/' + self.role_id + '/update', postdata)
        if resp:
            return resp.get('success')

    @property
    def privileges(self):
        """
        Privileges for the custom role as a list of strings

        Supported privileges with predefined permissions are:
        Administrative Privileges:

        Members

        - portal:admin:viewUsers: grants the ability to view full member account information within organization.
        - portal:admin:updateUsers: grants the ability to update member account information within organization.
        - portal:admin:deleteUsers: grants the ability to delete member accounts within organization.
        - portal:admin:inviteUsers: grants the ability to invite members to organization. (This privilege is only applicable to ArcGIS Online.)
        - portal:admin:disableUsers: grants the ability to enable and disable member accounts within organization.
        - portal:admin:changeUserRoles: grants the ability to change the role a member is assigned within organization; however, it does not grant the ability to promote a member to, or demote a member from, the Administrator role. That privilege is reserved for the Administrator role alone.
        - portal:admin:manageLicenses: grants the ability to assign licenses to members of organization.
        - portal:admin:reassignUsers: grants the ability to assign all groups and content of a member to another within organization.

        Groups

        - portal:admin:viewGroups: grants the ability to view all groups within organization.
        - portal:admin:updateGroups: grants the ability to update groups within organization.
        - portal:admin:deleteGroups: grants the ability to delete groups within organization.
        - portal:admin:reassignGroups: grants the ability to reassign groups to other members within organization.
        - portal:admin:assignToGroups: grants the ability to assign members to, and remove members from, groups within organization.
        - portal:admin:manageEnterpriseGroups: grants the ability to link group membership to an enterprise group. (This privilege is only applicable to Portal for ArcGIS.)

        Content

        - portal:admin:viewItems: grants the ability to view all content within organization.
        - portal:admin:updateItems: grants the ability to update content within organization.
        - portal:admin:deleteItems: grants the ability to delete content within organization.
        - portal:admin:reassignItems: grants the ability to reassign content to other members within organization.
        - portal:admin:shareToGroup: grants the ability to share other member's content to groups the user belongs to.
        - portal:admin:shareToOrg: grants the ability to share other member's content to organization.
        - portal:admin:shareToPublic: grants the ability to share other member's content to all users of the portal.

        ArcGIS Marketplace Subscriptions

        - marketplace:admin:purchase: grants the ability to request purchase information about apps and data in ArcGIS Marketplace. (This privilege is only applicable to ArcGIS Online.)
        - marketplace:admin:startTrial: grants the ability to start trial subscriptions in ArcGIS Marketplace. (This privilege is only applicable to ArcGIS Online.)
        - marketplace:admin:manage: grants the ability to create listings, list items and manage subscriptions in ArcGIS Marketplace. (This privilege is only applicable to ArcGIS Online.)

        Publisher Privileges:

        Content

        - portal:publisher:publishFeatures: grants the ability to publish hosted feature layers from shapefiles, CSVs, etc.
        - portal:publisher:publishTiles: grants the ability to publish hosted tile layers from tile packages, features, etc.
        - portal:publisher:publishScenes: grants the ability to publish hosted scene layers.

        User Privileges:

        Groups

        - portal:user:createGroup: grants the ability for a member to create, edit, and delete their own groups.
        - portal:user:joinGroup: grants the ability to join groups within organization.
        - portal:user:joinNonOrgGroup: grants the ability to join groups external to the organization. (This privilege is only applicable to ArcGIS Online.)

        Content

        - portal:user:createItem: grants the ability for a member to create, edit, and delete their own content.

        Sharing

        - portal:user:shareToGroup: grants the ability to share content to groups.
        - portal:user:shareToOrg: grants the ability to share content to organization.
        - portal:user:shareToPublic: grants the ability to share content to all users of portal.
        - portal:user:shareGroupToOrg: grants the ability to make groups discoverable by the organization.
        - portal:user:shareGroupToPublic: grants the ability to make groups discoverable by all users of portal.

        Premium Content

        - premium:user:geocode: grants the ability to perform large-volume geocoding tasks with the Esri World Geocoder such as publishing a CSV of addresses as hosted feature layer.
        - premium:user:networkanalysis: grants the ability to perform network analysis tasks such as routing and drive-time areas.
        - premium:user:geoenrichment: grants the ability to geoenrich features.
        - premium:user:demographics: grants the ability to make use of premium demographic data.
        - premium:user:spatialanalysis: grants the ability to perform spatial analysis tasks.
        - premium:user:elevation: grants the ability to perform analytical tasks on elevation data.

        Features

        - features:user:edit: grants the ability to edit features in editable layers, according to the edit options enabled on the layer.
        - features:user:fullEdit: grants the ability to add, delete, and update features in a hosted feature layer regardless of the editing options enabled on the layer.

        Open Data

        - opendata:user:openDataAdmin: grants the ability to manage Open Data Sites for the organization. (This privilege is only applicable to ArcGIS Online.)
        - opendata:user:designateGroup: grants the ability to designate groups within organization as being available for use in Open Data. (This privilege is only applicable to ArcGIS Online.)

        """
        resp = self._portal.con.post('portals/self/roles/' + self.role_id + '/privileges', self._portal._postdata())
        if resp:
            return resp.get('privileges')
        else:
            return None

    @privileges.setter
    def privileges(self, value):
        """Privileges for the custom role as a list of strings"""
        postdata = self._portal._postdata()
        postdata['privileges'] = { 'privileges' : value }

        resp = self._portal.con.post('portals/self/roles/' + self.role_id + '/setPrivileges', postdata)
        if resp:
            return resp.get('success')

    def delete(self):
        """Deletes this role and returns True if the operation was successful"""
        resp = self._portal.con.post('portals/self/roles/' + self.role_id + '/delete', self._portal._postdata())
        if resp:
            return resp.get('success')


class GroupManager(object):
    """
    Helper class for managing GIS groups. This class is not created by users directly.
    An instance of this class, called 'groups', is available as a property of the Gis object.
    Users call methods on this 'groups' object to manipulate (create, get, search...) users.
    """
    def __init__(self, gis):
        self._gis = gis
        self._portal = gis._portal

    def create(self, title, tags, description=None,
               snippet=None, access='public', thumbnail=None,
               is_invitation_only=False, sort_field='avgRating',
               sort_order='desc', is_view_only=False, ):
        """ Creates a group and returns it if successful.

        ================  =========================================================
        **Argument**      **Description**
        ----------------  ---------------------------------------------------------
        title             required string, name of the group
        ----------------  ---------------------------------------------------------
        tags              required, comma-delimited list of tags, or list of tags
                          as strings
        ----------------  ---------------------------------------------------------
        description       optional string, describes group in detail
        ----------------  ---------------------------------------------------------
        snippet           optional string, <250 characters summarizes group
        ----------------  ---------------------------------------------------------
        access            optional string, can be private, public, or org
        ----------------  ---------------------------------------------------------
        thumbnail         optional string, URL to group image
        ----------------  ---------------------------------------------------------
        is_invitation_only  optional boolean, defines whether users can join by
                          request.
        ----------------  ---------------------------------------------------------
        sort_field        optional string, specifies how shared items with
                          the group are sorted.
        ----------------  ---------------------------------------------------------
        sort_order        optional string, asc or desc for ascending or descending.
        ----------------  ---------------------------------------------------------
        is_view_only      optional boolean, defines whether the group is searchable
        ================  =========================================================

        :return:
            the group, if created, or None
        """
        if type(tags) is list:
            tags = ",".join(tags)
        group = self._portal.create_group_from_dict({
            'title' : title, 'tags' : tags, 'description' : description,
            'snippet' : snippet, 'access' : access, 'sortField' : sort_field,
            'sortOrder' : sort_order, 'isViewOnly' : is_view_only,
            'isinvitationOnly' : is_invitation_only}, thumbnail)
        #print(groupid)
        if group is not None:
            return Group(self._gis, group['id'], group)
        else:
            return None

    def create_from_dict(self, dict):
        """
        Create a group with parameters specified in the dict
        See help of create() method for parameters
        :return:
            the group, if created, or None
        """
        thumbnail = dict.pop("thumbnail", None)

        if 'tags' in dict:
            if type(dict['tags']) is list:
                dict['tags'] = ",".join(dict['tags'])

        group = self._portal.create_group_from_dict(dict, thumbnail)
        if group is not None:
            return Group(self._gis, group['id'], group)
        else:
            return None

    def get(self, groupid):
        """ Returns the group object for the specified groupid.

        Arguments
            groupid        required string, the group identifier
        :return:
            None if the group is not found and returns a group object if the group is found
        """
        try:
            group = self._portal.get_group(groupid)
        except RuntimeError as re:
            if re.args[0].__contains__("Group does not exist or is inaccessible"):
                return None
            else:
                raise re

        if group is not None:
            return Group(self._gis, groupid, group)
        return None

    def search(self, query='', sort_field='title', sort_order='asc',
               max_groups=1000, outside_org=False):
        """ Searches for portal groups.

        .. note::
            A few things that will be helpful to know.

            1. The query syntax has quite a few features that can't
                be adequately described here.  The query syntax is
                available in ArcGIS help.  A short version of that URL
                is http://bitly.com/1fJ8q31.

            2. Searching without specifying a query parameter returns
               a list of all groups in your organization.

            2. Most of the time when searching groups you want to
                search within your organization in ArcGIS Online
                or within your Portal.  As a convenience, the method
                automatically appends your organization id to the query by
                default.  If you don't want the API to append to your query
                set outside_org to True.

        ================  ========================================================
        **Argument**      **Description**
        ----------------  --------------------------------------------------------
        query             optional query string on Portal, required for Online.
                          If not specified, all groups will be searched. See notes
        ----------------  --------------------------------------------------------
        sort_field        optional string, valid values can be title, owner,
                          created
        ----------------  --------------------------------------------------------
        sort_order        optional string, valid values are asc or desc
        ----------------  --------------------------------------------------------
        max_groups        optional int, maximum number of groups returned
        ----------------  --------------------------------------------------------
        outside_org       optional boolean, controls whether to search outside
                          your org
        ================  ========================================================

        :return:
        Returns a list of groups matching the specified query
        """
        grouplist = []
        groups = self._portal.search_groups(query, sort_field, sort_order, max_groups, outside_org)
        for group in groups:
            grouplist.append(Group(self._gis, group['id'], group))
        return grouplist


def _is_shapefile(data):
    try:
        if zipfile.is_zipfile(data):
            zf = zipfile.ZipFile(data, 'r')
            namelist = zf.namelist()
            for name in namelist:
                if name.endswith('.shp') or name.endswith('.SHP'):
                    return True
        return False
    except:
        return False


class ContentManager(object):
    """
    Helper class for managing GIS content. This class is not created by users directly.
    An instance of this class, called 'content', is available as a property of the Gis object.
    Users call methods on this 'content' object to manipulate (create, get, search...) items.
    """
    def __init__(self, gis):
        self._gis = gis
        self._portal = gis._portal

    def add(self, item_properties, data=None, thumbnail=None, metadata=None, owner=None, folder=None):
        """ Adds content to the GIS by creating an item.

            .. note::
                That content can be a file (such as a service definition, shapefile, CSV, layer package,
                file geodatabase, geoprocessing package, map package) or it can be a URL (to an ArcGIS Server
                service, WMS service, or an application).

                If you are uploading a package or other file, provide a path or URL
                to the file in the data argument.

                From a technical perspective, none of the item properties below are required.  However,
                it is strongly recommended that title, type, typeKeywords, tags, snippet, and description
                be provided.


            ===============     ====================================================
            **Argument**        **Description**
            ---------------     ----------------------------------------------------
            item_properties     required dictionary, see below for the keys and
                                values
            ---------------     ----------------------------------------------------
            data                optional string, either a path or URL to the data
            ---------------     ----------------------------------------------------
            thumbnail           optional string, either a path or URL to an image
            ---------------     ----------------------------------------------------
            metadata            optional string, either a path or URL to metadata.
            ---------------     ----------------------------------------------------
            owner               optional string, defaults to logged in user.
            ---------------     ----------------------------------------------------
            folder              optional string, name of folder where placing item
            ===============     ====================================================


            =================  ============================================================================
             **Key**            **Value**
            -----------------  ----------------------------------------------------------------------------
            type               optional string, indicates type of item.  See URL 1 below for valid values.
            -----------------  ----------------------------------------------------------------------------
            typeKeywords       optinal string list.  Lists all sub-types.  See URL 1 for valid values.
            -----------------  ----------------------------------------------------------------------------
            description        optional string.  Description of the item.
            -----------------  ----------------------------------------------------------------------------
            title              optional string.  Name of the item.
            -----------------  ----------------------------------------------------------------------------
            url                optional string.  URL to item that are based on URLs.
            -----------------  ----------------------------------------------------------------------------
            text               optional string.  For text based items such as Feature Collections & WebMaps
            -----------------  ----------------------------------------------------------------------------
            tags               optional string of comma-separated values, or list of strings.
                               Used for searches on items.
            -----------------  ----------------------------------------------------------------------------
            snippet            optional string.  Provides a very short summary of the what the item is.
            -----------------  ----------------------------------------------------------------------------
            extent             optional string with comma separated values for min x, min y, max x, max y.
            -----------------  ----------------------------------------------------------------------------
            spatialReference   optional string.  Coordinate system that the item is in.
            -----------------  ----------------------------------------------------------------------------
            accessInformation  optional string.  Information on the source of the content.
            -----------------  ----------------------------------------------------------------------------
            licenseInfo        optinal string, any license information or restrictions regarding content.
            -----------------  ----------------------------------------------------------------------------
            culture            optional string.  Locale, country and language information.
            -----------------  ----------------------------------------------------------------------------
            access             optional string.  Valid values: private, shared, org, or public.
            -----------------  ----------------------------------------------------------------------------
            commentsEnabled    optional boolean.  Default is true.  Controls whether comments are allowed.
            -----------------  ----------------------------------------------------------------------------
            culture            optional string.  Language and country information.
            =================  ============================================================================


        URL 1: http://resources.arcgis.com/en/help/arcgis-rest-api/index.html#//02r3000000ms000000

            :return:
                 The item if successfully added, None if unsuccessful.
            """

        if data is not None:
            title = os.path.splitext(os.path.basename(data))[0]
            extn = os.path.splitext(os.path.basename(data))[1].upper()

            filetype = None
            if (extn == '.CSV'):
                filetype = 'CSV'
            elif (extn == '.SD'):
                filetype = 'Service Definition'
            elif title.upper().endswith('.GDB'):
                filetype = 'File Geodatabase'
            elif (extn in ('.SLPK', '.SPK')):
                filetype = 'Scene Package'
            elif (extn in ('.LPK', '.LPKX')):
                filetype = 'Layer Package'
            elif (extn in ('.GPK', '.GPKX')):
                filetype = 'Geoprocessing Package'
            elif (extn == '.GCPK'):
                filetype = 'Locator Package'
            elif (extn == '.TPK'):
                filetype = 'Tile Package'
            elif (extn in ('.MPK', '.MPKX')):
                filetype = 'Map Package'
            elif (extn == '.MMPK'):
                filetype = 'Mobile Map Package'
            elif (extn == '.APTX'):
                filetype = 'Project Template'
            elif (extn == '.VTPK'):
                filetype = 'Vector Tile Package'
            elif (extn == '.PPKX'):
                filetype = 'Project Package'
            elif (extn == '.RPK'):
                filetype = 'Rule Package'
            elif (extn == '.MAPX'):
                filetype = 'Pro Map'

            if _is_shapefile(data):
                filetype = 'Shapefile'

            if not 'type' in item_properties:
                if filetype is not None:
                    item_properties['type'] = filetype
                else:
                    raise RuntimeError('Specify type in item_properties')
            if not 'title' in item_properties:
                item_properties['title'] = title

        owner_name = owner
        if isinstance(owner, User):
            owner_name = owner.username

        if 'tags' in item_properties:
            if type(item_properties['tags']) is list:
                item_properties['tags'] = ",".join(item_properties['tags'])

        itemid = self._portal.add_item(item_properties, data, thumbnail, metadata, owner_name, folder)

        if itemid is not None:
            return Item(self._gis, itemid)
        else:
            return None

    def create_service(self, name,
                       service_description="",
                       has_static_data=False,
                       max_record_count = 1000,
                       supported_query_formats = "JSON",
                       capabilities = None,
                       description = "",
                       copyright_text = "",
                       wkid=102100,
                       create_params=None,
                       service_type="featureService",
                       owner=None, folder=None, item_properties=None):
        """ Creates a service in the Portal

        Arguments
            name                    required string, the unique name of the service
            service_description     optional string, description of the service
            has_static_data         optional boolean, indicating whether the data changes
            max_record_count        optional int, ,maximum number of records in query operations
            supported_query_formats optional string, formats in which query results are returned
            capabilities            optional string, Specify service capabilities.
                                    If left unspecified, 'Image,Catalog,Metadata,Download,Pixels'
                                    are used for image services, and 'Query'
                                    are used for feature services, and 'Query' otherwise
            description             optional string, a user-friendly description for the published dataset.
            copyright_text          optional string, copyright information associated with the dataset.
            wkid                    optional int, the well known id of the spatial reference for the service.
                                    All layers added to a hosted feature service need to have the same spatial reference defined for the feature service. When creating a new empty service without specifying its spatial reference, the spatial reference of the hosted feature service is set to the first layer added to that feature service.

            create_params           optional dict, containing all create parameters. If this parameter is used, all the parameters above are ignored

            service_type            optional string, the type of service to be created, imageService, featureService

            owner                   optional string, the username of the owner
            folder                  optional string, name of folder in which to create the service
            item_properties         optional dict, see below for the keys and values

            =================  ============================================================================
             **Key**            **Value**
            -----------------  ----------------------------------------------------------------------------
            type               optional string, indicates type of item.  See URL 1 below for valid values.
            -----------------  ----------------------------------------------------------------------------
            typeKeywords       optional string list.  Lists all sub-types.  See URL 1 for valid values.
            -----------------  ----------------------------------------------------------------------------
            description        optional string.  Description of the item.
            -----------------  ----------------------------------------------------------------------------
            title              optional string.  Name of the item.
            -----------------  ----------------------------------------------------------------------------
            url                optional string.  URL to item that are based on URLs.
            -----------------  ----------------------------------------------------------------------------
            tags               optional string of comma-separated values, or list of strings.
                               Used for searches on items.
            -----------------  ----------------------------------------------------------------------------
            snippet            optional string.  Provides a very short summary of the what the item is.
            -----------------  ----------------------------------------------------------------------------
            extent             optional string with comma separated values for min x, min y, max x, max y.
            -----------------  ----------------------------------------------------------------------------
            spatialReference   optional string.  Coordinate system that the item is in.
            -----------------  ----------------------------------------------------------------------------
            accessInformation  optional string.  Information on the source of the content.
            -----------------  ----------------------------------------------------------------------------
            licenseInfo        optinal string, any license information or restrictions regarding content.
            -----------------  ----------------------------------------------------------------------------
            culture            optional string.  Locale, country and language information.
            -----------------  ----------------------------------------------------------------------------
            access             optional string.  Valid values: private, shared, org, or public.
            -----------------  ----------------------------------------------------------------------------
            commentsEnabled    optional boolean.  Default is true.  Controls whether comments are allowed.
            -----------------  ----------------------------------------------------------------------------
            culture            optional string.  Language and country information.
            =================  ============================================================================

            :return:
                 The item for the service, if successfully created, None if unsuccessful.
        """
        if capabilities is None:
            if service_type == 'imageService':
                capabilities = 'Image,Catalog,Metadata,Download,Pixels'
            elif service_type == 'featureService':
                capabilities = 'Query'
            else:
                capabilities = 'Query'

        itemid = self._portal.create_service(name,
                                             service_description,
                                             has_static_data,
                                             max_record_count,
                                             supported_query_formats,
                                             capabilities,
                                             description,
                                             copyright_text,
                                             wkid,
                                             service_type,
                                             create_params,
                                             owner, folder, item_properties)
        if itemid is not None:
            return Item(self._gis, itemid)
        else:
            return None

    def get(self, itemid):
        """ Returns the item object for the specified itemid.

        Arguments
            itemid        required string, the item identifier
        :return:
            None if the item is not found and returns an item object if the item is found
        """
        try:
            item = self._portal.get_item(itemid)
        except RuntimeError as re:
            if re.args[0].__contains__("Item does not exist or is inaccessible"):
                return None
            else:
                raise re

        if item is not None:
            return Item(self._gis, itemid, item)
        return None

    def search(self, query, item_type=None, sort_field='avgRating', sort_order='desc', max_items=10, outside_org=False):
        """ Searches for portal items.

        .. note::
            A few things that will be helpful to know.

            1. The query syntax has quite a few features that can't
                be adequately described here.  The query syntax is
                available in ArcGIS help.  A short version of that URL
                is http://bitly.com/1fJ8q31.

            2. Most of the time when searching items you want to
                search within your organization in ArcGIS Online
                or within your Portal.  As a convenience, the method
                automatically appends your organization id to the query by
                default.  If you want content from outside your org
                set outside_org to True.

        ================  ===================================================================================
        **Argument**      **Description**
        ----------------  -----------------------------------------------------------------------------------
        query             required string, query string.  See notes.
        ----------------  -----------------------------------------------------------------------------------
        item_type         optional string, set type of item to search.
                          http://resources.arcgis.com/en/help/arcgis-rest-api/index.html#//02r3000000ms000000
        ----------------  -----------------------------------------------------------------------------------
        sort_field        optional string, valid values can be title, uploaded, type, owner, modified,
                          avgRating, numRatings, numComments, and numViews.
        ----------------  -----------------------------------------------------------------------------------
        sort_order        optional string, valid values are asc or desc
        ----------------  -----------------------------------------------------------------------------------
        max_items         optional int, maximum number of items returned, default is 10
        ----------------  -----------------------------------------------------------------------------------
        outside_org       optional boolean, controls whether to search outside your org (default is False)
        ================  ===================================================================================

        :return:
        Returns a list of items matching the specified query
        """
        itemlist = []
        if query is not None and query != '' and item_type is not None:
            query += ' AND '

        if item_type is not None:
            item_type = item_type.lower()
            if item_type == "web map":
                query += ' (type:"web map" NOT type:"web mapping application")'
            elif item_type == "web scene":
                query += ' (type:"web scene" NOT type:"CityEngine Web Scene")'
            elif item_type == "feature layer":
                query += ' (type:"feature service")'
            elif item_type == "geoprocessing tool":
                query += ' (type:"geoprocessing service")'
            elif item_type == "geoprocessing toolbox":
                query += ' (type:"geoprocessing service")'
            elif item_type == "feature layer collection":
                query += ' (type:"feature service")'
            elif item_type == "image layer":
                query += ' (type:"image service")'
            elif item_type == "imagery layer":
                query += ' (type:"image service")'
            elif item_type == "vector tile layer":
                query += ' (type:"vector tile service")'
            elif item_type == "scene layer":
                query += ' (type:"scene service")'
            elif item_type == "layer":
                query += ' (type:"layer" NOT type:"layer package" NOT type:"Explorer Layer")'
            elif item_type == "feature collection":
                query += ' (type:"feature collection" NOT type:"feature collection template")'
            elif item_type == "desktop application":
                query += ' (type:"desktop application" NOT type:"desktop application template")'
            else:
                query += ' (type:"' + item_type +'")'

        items = self._portal.search(query, sort_field=sort_field, sort_order=sort_order, max_results=max_items, outside_org=outside_org)
        for item in items:
            itemlist.append(Item(self._gis, item['id'], item))
        return itemlist
    # q: (type:"web map" NOT type:"web mapping applications") AND accountid:0123456789ABCDEF

    def create_folder(self, folder, owner=None):
        """ Creates a folder with the given name, for the given owner. Does nothing if the
        folder already exists. If owner is not specified, does so for the logged in user.

        ================  ===============================================================
        **Argument**      **Description**
        ----------------  ---------------------------------------------------------------
        folder            required string, the name of the folder to create for the owner
        ----------------  ---------------------------------------------------------------
        owner             optional string or User, folder owner, None for logged in user
        ================  ===============================================================

        :return:
            a json object like the following:
            {"username" : "portaladmin","id" : "bff13218991c4485a62c81db3512396f","title" : "testcreate"} if the folder was created, None otherwise.
        """
        if folder != '/': # we don't create root folder
            if owner is None:
                owner = self._portal.logged_in_user()['username']
                owner_name = owner
            elif isinstance(owner, User):
                owner_name = owner.username
            else:
                owner_name = owner
            if self._portal.get_folder_id(owner_name, folder) is None:
                return self._portal.create_folder(owner_name, folder)
            else:
                print('Folder already exists.')
        return None

    def delete_folder(self, folder, owner=None):
        """ Deletes a folder for the given owner (logged in user by default) with the given folder name.

        ================  ===============================================================
        **Argument**      **Description**
        ----------------  ---------------------------------------------------------------
        folder            required string, the name of the folder to delete
        ----------------  ---------------------------------------------------------------
        owner             optional string or User, folder owner, None for logged in user
        ================  ===============================================================

        :return:
            True if succeeded, False otherwise
        """
        if folder != '/':
            if owner is None:
                owner = self._portal.logged_in_user()['username']
                owner_name = owner
            elif isinstance(owner, User):
                owner_name = owner.username
            else:
                owner_name = owner
            return self._portal.delete_folder(owner_name, folder)

    def import_data(self, df, address_fields=None, **kwargs):
        """
        Imports a Pandas data frame, that has an address column, or an arcgis spatial dataframe
        into the GIS.

        Spatial dataframes are imported into the GIS and published as feature layers.
        Pandas dataframes that have an address column are imported as an in memory feature collection.
        Note: By default, there is a limit of 1,000 rows/features for Pandas dataframes. This limit isn't there for spatial dataframes.

        df : pandas dataframe or arcgis.SpatialDataFrame
        address_fields : dict containing mapping of df columns to address fields, eg: { "CountryCode" : "Country"} or { "Address" : "Address" }
        title: optional title of the item. This is used for spatial dataframe objects.
        tags: optional tags when publishing a spatial dataframe to the the GIS
        Returns feature collection or feature layer, that can be used for analysis, visualization or published to the GIS as an item
        """
        from arcgis.features import FeatureCollection, SpatialDataFrame, FeatureSet

        from arcgis._impl.common._utils import zipws

        import shutil
        from uuid import uuid4
        import pandas as pd
        try:
            import arcpy
            has_arcpy = True
        except ImportError:
            has_arcpy = False
        try:
            import shapefile
            has_pyshp = True
        except ImportError:
            has_pyshp = False
        if isinstance(df, FeatureSet):
            df = df.df
        if has_arcpy == False and \
           has_pyshp == False and \
           isinstance(df, SpatialDataFrame):
            raise Exception("SpatialDataFrame's must have either pyshp or" + \
                            " arcpy available to use import_data")
        elif isinstance(df, SpatialDataFrame):
            temp_dir = os.path.join(tempfile.gettempdir(), "a" + uuid4().hex[:7])
            title = kwargs.pop("title", uuid4().hex)
            tags = kwargs.pop('tags', 'FGDB')
            os.makedirs(temp_dir)
            temp_zip = os.path.join(temp_dir, "%s.zip" % "a" + uuid4().hex[:5])
            if has_arcpy:
                fgdb = arcpy.CreateFileGDB_management(out_folder_path=temp_dir,
                                                      out_name="publish.gdb")[0]
                ds = df.to_featureclass(out_location=fgdb,
                                        out_name=os.path.basename(temp_dir))
                zip_fgdb = zipws(path=fgdb, outfile=temp_zip, keep=True)
                item = self.add(
                    item_properties={
                        "title" : title,
                        "type" : "File Geodatabase",
                        "tags" : tags},
                    data=zip_fgdb)
                shutil.rmtree(temp_dir,
                              ignore_errors=True)
                return item.publish()
            elif has_pyshp:
                ds = df.to_featureclass(out_location=temp_dir,
                                        out_name="export.shp")
                zip_shp = zipws(path=temp_dir, outfile=temp_zip, keep=False)
                item = self.add(
                    item_properties={
                        "title":title,
                        "tags":tags},
                    data=zip_shp)
                shutil.rmtree(temp_dir,
                              ignore_errors=True)
                return item.publish()
            return
        elif isinstance(df, pd.DataFrame):
            # CSV WORKFLOW
            path = "content/features/analyze"

            postdata = {
                "f": "pjson",
                "text" : df.to_csv(),
                "filetype" : "csv",

                "analyzeParameters" : {
                    "enableGlobalGeocoding": "true",
                    "sourceLocale":"en-us",
                    #"locationType":"address",
                    "sourceCountry":"",
                    "sourceCountryHint":"",
                    "geocodeServiceUrl":self._gis.properties.helperServices.geocode[0]['url']
                }
            }

            if address_fields is not None:
                postdata['analyzeParameters']['locationType'] = 'address'

            res = self._portal.con.post(path, postdata)
            #import json
            #json.dumps(res)
            if address_fields is not None:
                res['publishParameters'].update({"addressFields":address_fields})

            path = "content/features/generate"
            postdata = {
                "f": "pjson",
                "text" : df.to_csv(),
                "filetype" : "csv",
                "publishParameters" : json.dumps(res['publishParameters'])
            }

            res = self._portal.con.post(path, postdata)#, use_ordered_dict=True) - OrderedDict >36< PropertyMap

            fc = FeatureCollection(res['featureCollection']['layers'][0])
            return fc
        return None

    def is_service_name_available(self, service_name, service_type):
        """
        Returns True is the specified service_name is available for the specified service_type
        """
        path = "portals/self/isServiceNameAvailable"

        postdata = {
            "f": "pjson",
            "name" : service_name,
            "type" : service_type
        }

        res = self._portal.con.post(path, postdata)
        return res['available']

class ResourceManager(object):
    """
    Helper class for managing resource files of an item. This class is not created by users directly.
    An instance of this class, called 'resources', is available as a property of the Item object.
    Users call methods on this 'resources' object to manage (add, remove, update, list, get) item resources.
    """

    def __init__(self, item, gis):
        self._gis = gis
        self._portal = gis._portal
        self._item = item

    def add(self, file, folder_name=None, file_name=None, text=None, archive=False):
        """The add resources operation adds new file resources to an existing item. For example, an image that is
        used as custom logo for Report Template. All the files are added to 'resources' folder of the item. File
        resources use storage space from your quota and are scanned for viruses. The item size is updated to
        include the size of added resource files. Each file added should be no more than 25 Mb.

        Supported item types that allow adding file resources are: Vector Tile Service, Vector Tile Package,
        Style, Code Attachment, Report Template, Web Mapping Application, Feature Service, Web Map,
        Statistical Data Collection, Scene Service, and Web Scene.

        Supported file formats are: JSON, XML, TXT, PNG, JPEG, GIF, BMP, PDF, MP3, MP4, and ZIP.
        This operation is only available to the item owner and the organization administrator.

        ================  ===============================================================
        **Argument**      **Description**
        ----------------  ---------------------------------------------------------------
        file              required string, path to the file that needs to be added
        ----------------  ---------------------------------------------------------------
        folder_name       optional string, provide a folder name if the file has to be
                          added to a folder under resources
        ----------------  ---------------------------------------------------------------
        file_name         optional string, file name used to rename an existing file
                          resource uploaded, or to be used together with text as file name for it.
        ----------------  ---------------------------------------------------------------
        text              optional string, text input to be added as a file resource,
                          used together with file_name.
        ----------------  ---------------------------------------------------------------
        archive           optional bool, default = False.  If True, file resources
                          added are extracted and files are uploaded to respective folders.
        ================  ===============================================================

        :return:
            Python dict like the following if succeeded:
            {
                "success": True,
                "itemId": "<item id>",
                "owner": "<owner username>",
                "folder": "<folder id>"
            }

            else like the following if it failed:
            {"error": {
                        "code": 400,
                        "messageCode": "CONT_0093",
                        "message": "File type not allowed for addResources",
                        "details": []
                        }
            }
        """

        query_url = 'content/users/'+ self._item.owner +\
                        '/items/' + self._item.itemid + '/addResources'

        files = [] #create a list of named tuples to hold list of files
        if not os.path.isfile(os.path.abspath(file)):
            raise RuntimeError("File(" + file + ") not found.")
        files.append(('file',file, os.path.basename(file)))

        params = {}
        params['f'] = 'json'

        if folder_name is not None:
            params['resourcesPrefix'] = folder_name
        if file_name is not None:
            params['fileName'] = file_name
        if text is not None:
            params['text'] = text
        params['archive'] = 'true' if archive else 'false'

        resp = self._portal.con.post(query_url, params, files=files, compress=False)
        return resp

    def update(self, file, folder_name=None, file_name=None, text=None):
        """The update resources operation allows to update existing file resources of an item.
        File resources use storage space from your quota and are scanned for viruses. The item size
        is updated to include the size of updated resource files.

        Supported file formats are: JSON, XML, TXT, PNG, JPEG, GIF, BMP, PDF, and ZIP.
        This operation is only available to the item owner and the organization administrator.

        ================  ===============================================================
        **Argument**      **Description**
        ----------------  ---------------------------------------------------------------
        file              required string, path to the file on disk to be used for overwriting
                          an existing file resource
        ----------------  ---------------------------------------------------------------
        folder_name       optional string, provide a folder name if the file resource
                          being updated resides in a folder
        ----------------  ---------------------------------------------------------------
        file_name         optional string, destination name for the file used to update
                          an existing resource, or to be used together with text parameter
                          as file name for it.

                          For example, you can use fileName=banner.png to update an existing
                          resource banner.png with a file called billboard.png without
                          renaming the file locally.
        ----------------  ---------------------------------------------------------------
        text              optional string, text input to be added as a file resource,
                          used together with file_name.
        ================  ===============================================================

        :return:
            Python dict like the following if succeeded:
            {
                "success": True,
                "itemId": "<item id>",
                "owner": "<owner username>",
                "folder": "<folder id>"
            }

            else like the following if it failed:
            {"error": {
                        "code": 404,
                        "message": "Resource does not exist or is inaccessible.",
                        "details": []
                        }
            }
        """

        query_url = 'content/users/' + self._item.owner + \
                    '/items/' + self._item.itemid + '/updateResources'

        files = []  # create a list of named tuples to hold list of files
        if not os.path.isfile(os.path.abspath(file)):
            raise RuntimeError("File(" + file + ") not found.")
        files.append(('file', file, os.path.basename(file)))

        params = {}
        params['f'] = 'json'

        if folder_name is not None:
            params['resourcesPrefix'] = folder_name
        if file_name is not None:
            params['fileName'] = file_name
        if text is not None:
            params['text'] = text

        resp = self._portal.con.post(query_url, params, files=files)
        return resp

    def list(self):
        """
        Lists all file resources of an existing item. This resource is only available to
        the item owner and the organization administrator.
        :return:
            A Python list of dictionaries of the form:
            [
                {
                  "resource": "<resource1>"
                },
                {
                  "resource": "<resource2>"
                },
                {
                  "resource": "<resource3>"
                }
            ]
        """
        query_url = 'content/items/' + self._item.itemid + '/resources'
        params = {'f':'json',
                  'num': 1000}
        resp = self._portal.con.get(query_url, params)
        resp_resources = resp.get('resources')
        count = int(resp.get('num'))
        next_start = int(resp.get('nextStart'))

        # loop through pages
        while next_start > 0:
            params2 = {'f':'json',
                       'num':1000,
                       'start':next_start + 1}

            resp2 = self._portal.con.get(query_url, params2)
            resp_resources.extend(resp2.get('resources'))
            count += int(resp2.get('num'))
            next_start = int(resp2.get('nextStart'))

        return resp_resources

    def get(self, file, try_json = True, out_folder = None, out_file_name = None):
        """Gets a specific file resource of an existing item.

        ================  ===============================================================
        **Argument**      **Description**
        ----------------  ---------------------------------------------------------------
        file              required string, path to the file for download.
                          For files in the root, just specify the file name. For files in
                          folders (prefixes), specify using the format
                          <foldername>/<foldername>./../<filename>
        ----------------  ---------------------------------------------------------------
        try_json          optional bool. If True, will attempt to convert JSON files to
                          Python dictionary objects. Default is True.
        ----------------  ---------------------------------------------------------------
        out_folder        optional string. Specify the folder into which the file has to
                          saved. Default is user's temporary directory.
        ----------------  ---------------------------------------------------------------
        out_file_name     optional string. Specify the name to use when downloading the
                          file. Default is the resource file's name.
        ================  ===============================================================

        This operation is only available to the item owner and the organization administrator.

        :return:
            Path to the downloaded file if getting a binary file (like a jpeg or png file) or if
             try_jon = False when getting a JSON file.

            If file is a JSON, returns as a Python dictionary.
        """

        safe_file_format = file.replace(r'\\','/')
        safe_file_format = safe_file_format.replace('//', '/')

        query_url = 'content/items/' + self._item.itemid + '/resources/' + safe_file_format

        return self._portal.con.get(query_url, try_json = try_json, out_folder=out_folder,
                                    file_name = out_file_name)

    def remove(self, file = None):
        """Removes a single resource file or all resources. The item size is updated once resource files are deleted.

        ================  ===============================================================
        **Argument**      **Description**
        ----------------  ---------------------------------------------------------------
        file              optional string, path to the file for removal.
                          For files in the root, just specify the file name. For files in
                          folders (prefixes), specify using the format
                          <foldername>/<foldername>./../<filename>

                          If not specified, all resource files will be removed
        ================  ===============================================================

        This operation is only available to the item owner and the organization administrator.

        :return:
            If succeeded a Python dictionary of the form
            { 'success': True }

            else a dictionary with error info
            {"error": {"code": 404,
                        "message": "Resource does not exist or is inaccessible.",
                        "details": []
                      }
            }
        """
        safe_file_format = ""
        delete_all = 'false'
        if file:
            safe_file_format = file.replace(r'\\','/')
            safe_file_format = safe_file_format.replace('//', '/')
        else:
            delete_all = 'true'

        query_url = 'content/users/'+ self._item.owner +\
                        '/items/' + self._item.itemid + '/removeResources'
        params = {'f':'json',
                  'resource': safe_file_format if safe_file_format else "",
                  'deleteAll':delete_all}

        return self._portal.con.post(query_url, postdata=params)

class Group(dict):
    """
    Represents a group (for example, San Bernardino Fires) within the GIS (ArcGIS Online or Portal for ArcGIS)
    """
    def __init__(self, gis, groupid, groupdict=None):
        dict.__init__(self)
        self._gis = gis
        self._portal = gis._portal
        self.groupid = groupid
        self.thumbnail = None
        self._workdir = tempfile.gettempdir()
        # groupdict = self._portal.get_group(self.groupid)
        self._hydrated = False
        if groupdict:
            self.__dict__.update(groupdict)
            super(Group, self).update(groupdict)

    def _hydrate(self):
        groupdict = self._portal.get_group(self.groupid)
        self._hydrated = True
        super(Group, self).update(groupdict)
        self.__dict__.update(groupdict)

    def __getattr__(self, name): # support group attributes as group.access, group.owner, group.phone etc
        if not self._hydrated and not name.startswith('_'):
            self._hydrate()
        try:
            return dict.__getitem__(self, name)
        except:
            raise AttributeError("'%s' object has no attribute '%s'" % (type(self).__name__, name))



    def __getitem__(self, k): # support group attributes as dictionary keys on this object, eg. group['owner']
        try:
            return dict.__getitem__(self, k)
        except KeyError:
            if not self._hydrated and not k.startswith('_'):
                self._hydrate()
            return dict.__getitem__(self, k)

    def __str__(self):
        return self.__repr__()
        # state = ["   %s=%r" % (attribute, value) for (attribute, value) in self.__dict__.items()]
        # return '\n'.join(state)

    def __repr__(self):
        return '<%s title:"%s" owner:%s>' % (type(self).__name__, self.title, self.owner)

    def get_thumbnail_link(self):
        """ URL to the thumbnail image """
        thumbnail_file = self.thumbnail
        if thumbnail_file is None:
            return self._portal.url + '/home/images/group-no-image.png'
        else:
            thumbnail_url_path = self._portal.con.baseurl + 'community/groups/' + self.groupid + '/info/' + thumbnail_file
            return thumbnail_url_path

    def _repr_html_(self):
        thumbnail = self.thumbnail
        if self.thumbnail is None or not self._portal.is_logged_in:
            thumbnail = self.get_thumbnail_link()
        else:
            b64 = base64.b64encode(self.get_thumbnail())
            thumbnail = "data:image/png;base64," + str(b64,"utf-8") + "' "

        title = 'Not Provided'
        snippet = 'Not Provided'
        description = 'Not Provided'
        owner = 'Not Provided'
        try:
            title = self.title
        except:
            title = 'Not Provided'

        try:
            description = self.description
        except:
            description = 'Not Provided'

        try:
            snippet = self.snippet
        except:
            snippet = 'Not Provided'

        try:
            owner = self.owner
        except:
            owner = 'Not available'

        url = self._portal.url  + "/home/group.html?id=" + self.groupid
        return """<div class="9item_container" style="height: auto; overflow: hidden; border: 1px solid #cfcfcf; border-radius: 2px; background: #f6fafa; line-height: 1.21429em; padding: 10px;">
                    <div class="item_left" style="width: 210px; float: left;">
                       <a href='""" + str(url) + """' target='_blank'>
                        <img src='""" + str(thumbnail) + """' class="itemThumbnail">
                       </a>
                    </div>

                    <div class="item_right" style="float: none; width: auto; overflow: hidden;">
                        <a href='""" + str(url) + """' target='_blank'><b>""" + str(title) + """</b>
                        </a>
                        <br/>
                        <br/><b>Summary</b>: """ + str(snippet) + """
                        <br/><b>Description</b>: """ + str(description)  + """
                        <br/><b>Owner</b>: """ + str(owner)  + """
                        <br/><b>Created</b>: """ + str(datetime.datetime.fromtimestamp(self.created/1000).strftime("%B %d, %Y")) + """

                    </div>
                </div>
                """

    def content(self, max_items=1000):
        """Returns a list of items shared with this group."""
        itemlist = []
        items = self._portal.search('group:' + self.groupid, max_results=max_items, outside_org=True)
        for item in items:
            itemlist.append(Item(self._gis, item['id'], item))
        return itemlist

    def delete(self):
        """ Deletes this group.

        Returns
            a boolean indicating whether it was successful.

        """
        return self._portal.delete_group(self.groupid)

    def get_thumbnail(self):
        """ Returns the bytes that make up the thumbnail for this group.

        Arguments
            None

        Returns
            bytes that represent the image.

        Example

        .. code-block:: python

            response = group.get_thumbnail()
            f = open(filename, 'wb')
            f.write(response)
        """
        return self._portal.get_group_thumbnail(self.groupid)

    def download_thumbnail(self, save_folder=None):
        """ Downloads the group thumbnail for this group, returns file path. """
        if self.thumbnail is None:
            self._hydrate()
        thumbnail_file = self.thumbnail
        # Only proceed if a thumbnail exists
        if thumbnail_file:
            thumbnail_url_path = 'community/groups/' + self.groupid + '/info/' + thumbnail_file
            if thumbnail_url_path:
                if not save_folder:
                    save_folder = self._workdir
                file_name = os.path.split(thumbnail_file)[1]
                if len(file_name) > 50: #If > 50 chars, truncate to last 30 chars
                    file_name = file_name[-30:]

                file_path = os.path.join(save_folder, file_name)
                self._portal.con.get(path=thumbnail_url_path, try_json=False,
                                            out_folder=save_folder,
                                            file_name=file_name)
                return file_path

        else:
            return None

    def add_users(self, usernames):
        """ Adds users to this group.
        .. note::
            This method will only work if the user for the
            Portal object is either an administrator for the entire
            Portal or the owner of the group.

        ============  ======================================
        **Argument**  **Description**
        ------------  --------------------------------------
        usernames     list of usernames
        ============  ======================================

        :return:
             A dictionary with a key of "not_added" which contains the users that were not
             added to the group.
        """
        return self._portal.add_group_users(usernames, self.groupid)

    def remove_users(self, usernames):
        """ Remove users from this group.

        ================  ========================================================
        **Argument**      **Description**
        ----------------  --------------------------------------------------------
        usernames         required string, comma-separated list of users
        ================  ========================================================

        :return:
            a dictionary with a key notRemoved that is a list of users not removed.

        """
        return self._portal.remove_group_users(usernames, self.groupid)

    def invite_users(self, usernames, role='group_member', expiration=10080):
        """ Invites users to this group.

        .. note::
            A user who is invited to this group will see a list of invitations
            in the "Groups" tab of portal listing invitations.  The user
            can either accept or reject the invitation.

        Requires
            The user executing the command must be group owner

        ================  ========================================================
        **Argument**      **Description**
        ----------------  --------------------------------------------------------
        usernames:        a required string list of users to invite
        ----------------  --------------------------------------------------------
        role:             an optional string, either group_member or group_admin
        ----------------  --------------------------------------------------------
        expiration:       an optional int, specifies how long the invitation is
                          valid for in minutes.
        ================  ========================================================

        :return:
            a boolean that indicates whether the call succeeded.

        """
        return self._portal.invite_group_users(usernames, self.groupid, role, expiration)

    def reassign_to(self, target_owner):
        """ Reassigns this group to another owner.

        ================  ========================================================
        **Argument**      **Description**
        ----------------  --------------------------------------------------------
        target_owner      required string, username of new group owner
        ================  ========================================================

        :return:
            a boolean, indicating success

        """
        return self._portal.reassign_group(self.groupid, target_owner)

    def get_members(self):
        """ Returns members of this group.

        Arguments
            None.

        Returns
            a dictionary with keys: owner, admins, and users.

            ================  ========================================================
            **Key**           **Value**
            ----------------  --------------------------------------------------------
            owner             string value, the group's owner
            ----------------  --------------------------------------------------------
            admins            list of strings, typically this is the same as the owner
            ----------------  --------------------------------------------------------
            users             list of strings, the members of the group
            ================  ========================================================

        Example (to print users in a group)

        .. code-block:: python

            response = group.get_members()
            for user in response['users'] :
                print user

        """
        return self._portal.get_group_members(self.groupid)

    def update(self, title=None, tags=None, description=None, snippet=None, access=None,
               is_invitation_only=None, sort_field=None, sort_order=None, is_view_only=None,
               thumbnail=None):
        """ Updates this group.

        .. note::
            Only provide the values for the arguments you wish to update.

        ==================  =========================================================
        **Argument**        **Description**
        ------------------  ---------------------------------------------------------
        title               optional string, name of the group
        ------------------  ---------------------------------------------------------
        tags                optional string (comma-delimited list of tags) or
                            list of tags as strings
        ------------------  ---------------------------------------------------------
        description         optional string, describes group in detail
        ------------------  ---------------------------------------------------------
        snippet             optional string, <250 characters summarizes group
        ------------------  ---------------------------------------------------------
        access              optional string, can be private, public, or org
        ------------------  ---------------------------------------------------------
        thumbnail           optional string, URL or file location to group image
        ------------------  ---------------------------------------------------------
        is_invitation_only  optional boolean, defines whether users can join by
                            request.
        ------------------  ---------------------------------------------------------
        sort_field          optional string, specifies how shared items with the
                            group are sorted.
        ------------------  ---------------------------------------------------------
        sort_order          optional string, asc or desc for ascending or descending.
        ------------------  ---------------------------------------------------------
        is_view_only        optional boolean, defines whether the group is searchable
        ==================  =========================================================

        :return:
            a boolean indicating success
        """
        if tags is not None:
            if type(tags) is list:
                tags = ",".join(tags)
        resp = self._portal.update_group(self.groupid, title, tags, description, snippet, access, is_invitation_only, sort_field, sort_order, is_view_only, thumbnail)
        if resp:
            self._hydrate()
        return resp

    def leave(self):
        """ Removes the logged in user from the specified group.

        Requires:
            User must be logged in.

        Arguments:
             None.

        :return:
             a boolean indicating whether the operation was successful.
        """
        return self._portal.leave_group(self.groupid)

    def join(self):
        """
        Users apply to join a group using the Join Group operation. This
        creates a new group application, which the group administrators
        accept or decline. This operation also creates a notification for
        the user indicating that they have applied to join this group.
        Available only to authenticated users.
        Users can only apply to join groups to which they have access. If
        the group is private, users will not be able to find it to ask to
        join it.
        Information pertaining to the applying user, such as their full
        name and username, can be sent as part of the group application.
        """
        url = "community/groups/%s/join" % (self.groupid)
        params = {"f" : "json"}
        res = self._portal.con.post(url, params)
        if 'success' in res:
            return res['success'] == True
        return res
    #----------------------------------------------------------------------
    @property
    def applications(self):
        """
        Lists the group applications for the given group. Available to
        administrators of the group or administrators of an organization if
        the group is part of one.
        """
        apps = []
        try:
            path = "%scommunity/groups/%s/applications" % (self._portal.resturl, self.groupid)
            params = {"f" : "json"}
            res = self._portal.con.post(path, params)
            if 'applications' in res:
                for app in res['applications']:
                    url = "%s/%s" % (path, app['username'])
                    apps.append(GroupApplication(url=url, gis=self._gis))
        except:
            print()
        return apps

class GroupApplication(object):
    """
    Represents a single group application on the GIS (ArcGIS Online or
    Portal for ArcGIS)
    """
    _con = None
    _portal =  None
    _gis = None
    _url = None
    _properties = None
    def __init__(self, url, gis, **kwargs):
        initialize = kwargs.pop('initialize', False)
        self._url = url
        self._gis = gis
        self._portal = gis._portal
        self._con = self._portal.con
        if initialize:
            self._init()

    def _init(self):
        """loads the properties"""
        try:
            res = self._con.get(self._url, {'f':'json'})
            self._properties = PropertyMap(res)
            self._json_dict = res
        except:
            self._properties = PropertyMap({})
            self._json_dict = {}

    @property
    def properties(self):
        if self._properties is None:
            self._init()
        return self._properties

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return '<%s for %s>' % (type(self).__name__, self.properties.username)

    def accept(self):
        """
        When a user applies to join a group, a group application is
        created. Group administrators choose to accept this application
        using the Accept Group Application operation. This operation adds
        the applying user to the group then deletes the application. This
        operation also creates a notification for the user indicating that
        the user's group application was accepted. Available only to group
        owners and admins.
        """
        url = "%s/accept" % self._url
        params = {"f" : "json"}
        res = self._con.post(url, params)
        if 'success' in res:
            return res['success'] == True
        return res

    def decline(self):
        """
        When a user applies to join a group, a group application is
        created. Group administrators can decline this application using
        the Decline Group Application operation (POST only). This operation
        deletes the application and creates a notification for the user
        indicating that the user's group application was declined. The
        applying user will not be added to the group. Available only to
        group owners and admins.
        """
        url = "%s/decline" % self._url
        params = {"f" : "json"}
        res = self._con.post(url, params)
        if 'success' in res:
            return res['success'] == True
        return res

class User(dict):
    """
    Represents a registered user of the GIS (ArcGIS Online, or Portal for ArcGIS).
    """
    def __init__(self, gis, username, userdict=None):
        dict.__init__(self)
        self._gis = gis
        self._portal = gis._portal
        self.username = username
        self.thumbnail = None
        self._workdir = tempfile.gettempdir()
        # userdict = self._portal.get_user(self.username)
        self._hydrated = False
        if userdict:
            if 'groups' in userdict and len(userdict['groups']) == 0: # groups aren't set unless hydrated
                del userdict['groups']
            self.__dict__.update(userdict)
            super(User, self).update(userdict)

    # Using http://code.activestate.com/recipes/52308-the-simple-but-handy-collector-of-a-bunch-of-named/?in=user-97991

    def _hydrate(self):
        userdict = self._portal.get_user(self.username)
        self._hydrated = True
        super(User, self).update(userdict)
        self.__dict__.update(userdict)

    def __getattr__(self, name): # support user attributes as user.access, user.email, user.role etc
        if not self._hydrated and not name.startswith('_'):
            self._hydrate()
        try:
            return dict.__getitem__(self, name)
        except:
            raise AttributeError("'%s' object has no attribute '%s'" % (type(self).__name__, name))


    def __getitem__(self, k): # support user attributes as dictionary keys on this object, eg. user['role']
        try:
            return dict.__getitem__(self, k)
        except KeyError:
            if not self._hydrated and not k.startswith('_'):
                self._hydrate()
            return dict.__getitem__(self, k)

    def __str__(self):
        return self.__repr__()
        # state = ["   %s=%r" % (attribute, value) for (attribute, value) in self.__dict__.items()]
        # return '\n'.join(state)


    def __repr__(self):
        return '<%s username:%s>' % (type(self).__name__, self.username)

    def get_thumbnail_link(self):
        """ URL to the thumbnail image """
        thumbnail_file = self.thumbnail
        if thumbnail_file is None:
            return self._portal.url + '/home/js/arcgisonline/css/images/no-user-thumb.jpg'
        else:
            thumbnail_url_path = self._portal.con.baseurl + '/community/users/' + self.username + '/info/' + thumbnail_file
            return thumbnail_url_path

    def _repr_html_(self):
        thumbnail = self.thumbnail
        if self.thumbnail is None or not self._portal.is_logged_in:
            thumbnail = self.get_thumbnail_link()
        else:
            b64 = base64.b64encode(self.get_thumbnail())
            thumbnail = "data:image/png;base64," + str(b64,"utf-8") + "' width='200' height='133"

        firstName = 'Not Provided'
        lastName = 'Not Provided'
        fullName = 'Not Provided'
        description = "This user has not provided any personal information."

        try:
            firstName = self.firstName
        except:
            firstName = 'Not Provided'

        try:
            lastName = self.lastName
        except:
            firstName = 'Not Provided'

        try:
            fullName = self.fullName
        except:
            fullName = 'Not Provided'

        try:
            description = self.description
        except:
            description = "This user has not provided any personal information."

        url = self._portal.url  + "/home/user.html?user=" + self.username

        return """<div class="9item_container" style="height: auto; overflow: hidden; border: 1px solid #cfcfcf; border-radius: 2px; background: #f6fafa; line-height: 1.21429em; padding: 10px;">
                    <div class="item_left" style="width: 210px; float: left;">
                       <a href='""" + str(url) + """' target='_blank'>
                        <img src='""" + str(thumbnail) + """' class="itemThumbnail">
                       </a>
                    </div>

                    <div class="item_right" style="float: none; width: auto; overflow: hidden;">
                        <a href='""" + str(url) + """' target='_blank'><b>""" + str(fullName) + """</b>
                        </a>
                        <br/><br/><b>Bio</b>: """ + str(description) + """
                        <br/><b>First Name</b>: """ + str(firstName) + """
                        <br/><b>Last Name</b>: """ + str(lastName)  + """
                        <br/><b>Username</b>: """ + str(self.username)  + """
                        <br/><b>Joined</b>: """ + str(datetime.datetime.fromtimestamp(self.created/1000).strftime("%B %d, %Y")) + """

                    </div>
                </div>
                """

    def reset(self, password, new_password=None, new_security_question=None, new_security_answer=None):
        """ Resets a user's password, security question, and/or security answer.

        .. note::
            This function does not apply to those using enterprise accounts
            that come from an enterprise such as ActiveDirectory, LDAP, or SAML.
            It only has an effect on built-in users.

            If a new security question is specified, a new security answer should
            be provided.

        =====================  =========================================================
        **Argument**           **Description**
        ---------------------  ---------------------------------------------------------
        password               required string, current password
        ---------------------  ---------------------------------------------------------
        new_password           optional string, new password if resetting password
        ---------------------  ---------------------------------------------------------
        new_security_question  optional int, new security question if desired
        ---------------------  ---------------------------------------------------------
        new_security_answer    optional string, new security question answer if desired
        =====================  =========================================================

        :return:
            a boolean, indicating success

        """
        return self._portal.reset_user(self.username, password, new_password,
                                       new_security_question, new_security_answer)

    def update(self, access=None, preferred_view=None, description=None, tags=None,
               thumbnail=None, fullname=None, email=None, culture=None, region=None):
        """ Updates this user's properties.

        .. note::
            Only pass in arguments for properties you want to update.
            All other properties will be left as they are.  If you
            want to update description, then only provide
            the description argument.

        ================  ==========================================================
        **Argument**      **Description**
        ----------------  ----------------------------------------------------------
        access            optional string, values: private, org, public
        ----------------  ----------------------------------------------------------
        preferred_view    optional string, values: Web, GIS, null
        ----------------  ----------------------------------------------------------
        description       optional string, a description of the user.
        ----------------  ----------------------------------------------------------
        tags              optional string (comma-separated tags) or list of tags
        ----------------  ----------------------------------------------------------
        thumbnail         optional string, path or url to a file.  can be PNG, GIF,
                          JPEG, max size 1 MB
        ----------------  ----------------------------------------------------------
        fullname          optional string, name of the user, only for built-in users
        ----------------  ----------------------------------------------------------
        email             optional string, email address, only for built-in users
        ----------------  ----------------------------------------------------------
        culture           optional string, two-letter language code, fr for example
        ----------------  ----------------------------------------------------------
        region            optional string, two-letter country code, FR for example
        ================  ==========================================================

        :return:
            a boolean indicating success

        """
        if tags is not None:
            if type(tags) is list:
                tags = ",".join(tags)

        ret = self._portal.update_user(self.username, access, preferred_view, description, tags, thumbnail, fullname, email, culture, region)
        if ret:
            self._hydrate()
        return ret
    #----------------------------------------------------------------------
    def disable(self):
        """
        The Disable operation (POST only) disables login access for the
        user. It is only available to the administrator of the organization
        """
        params = {"f" : "json"}
        url = "%s/sharing/rest/community/users/%s/disable" % (self._gis._url, self.username)
        res = self._gis._con.post(url, params)
        if 'status' in res:
            self._hydrate()
            return res['status'] == 'success'
        elif 'success' in res:
            self._hydrate()
            return res['success']
        return False
    #----------------------------------------------------------------------
    def enable(self):
        """
        The Disable operation (POST only) disables login access for the
        user. It is only available to the administrator of the organization
        """
        params = {"f" : "json"}
        url = "%s/sharing/rest/community/users/%s/enable" % (self._gis._url, self.username)
        res = self._gis._con.post(url, params)
        if 'status' in res:
            self._hydrate()
            return res['status'] == 'success'
        elif 'success' in res:
            self._hydrate()
            return res['success']
        return False
    #----------------------------------------------------------------------
    def update_role(self, role):
        """ Updates this user's role to org_user, org_publisher, org_admin or a custom role

        .. note::
            There are four types of roles in Portal - user, publisher, administrator and custom roles
            A user can share items, create maps, create groups, etc.  A publisher can
            do everything a user can do and create hosted services.  An administrator can
            do everything that is possible in Portal. A custom roles privileges can be customized

        ================  ========================================================
        **Argument**      **Description**
        ----------------  --------------------------------------------------------
        role              required string, one of these values org_user,
                          org_publisher, org_admin
                          OR
                          Role object (from gis.users.roles)
        ================  ========================================================

        :return:
            a boolean, that indicates success

        """
        if isinstance(role, Role):
            role = role.role_id
        passed = self._portal.update_user_role(self.username, role)
        if passed:
            self._hydrate()
            self.role = role
        return passed

    def delete(self, reassign_to=None):
        """ Deletes this user from the portal, optionally deleting or reassigning groups and items.

        .. note::
            You can not delete a user in Portal if that user owns groups or items.  If you
            specify someone in the reassign_to argument then items and groups will be
            transferred to that user.  If that argument is not set then the method
            will fail if the user has items or groups that need to be reassigned.

        ================  ========================================================
        **Argument**      **Description**
        ----------------  --------------------------------------------------------
        reassign_to       optional string, new owner of items and groups
        ================  ========================================================

        :return:
            a boolean indicating whether the operation succeeded or failed.

        """
        return self._portal.delete_user(self.username, reassign_to)

    def reassign_to(self, target_username):
        """ Reassigns all of this user's items and groups to another user.

        Items are transferred to the target user into a folder named
        <user>_<folder> where user corresponds to the user whose items were
        moved and folder corresponds to the folder that was moved.

        .. note::
            This method must be executed as an administrator.  This method also
            can not be undone.  The changes are immediately made and permanent.

        ================  ===========================================================
        **Argument**      **Description**
        ----------------  -----------------------------------------------------------
        target_username   required string, user who will own items/groups after this.
        ================  ===========================================================

        :return:
            a boolean indicating success

        """
        return self._portal.reassign_user(self.username, target_username)

    def get_thumbnail(self):
        """ Returns the bytes that make up the thumbnail for this user.

        Arguments
            None.

        Returns
            bytes that represent the image.

        Example

        .. code-block:: python

            response = user.get_thumbnail()
            f = open(filename, 'wb')
            f.write(response)

        """
        thumbnail_file = self.thumbnail
        if thumbnail_file:
            thumbnail_url_path = 'community/users/' + self.username + '/info/' + thumbnail_file
            if thumbnail_url_path:
                return self._portal.con.get(thumbnail_url_path, try_json=False, force_bytes=True)

    def download_thumbnail(self, save_folder=None):
        """ Downloads the item thumbnail for this user, returns file path. """
        thumbnail_file = self.thumbnail

        # Only proceed if a thumbnail exists
        if thumbnail_file:
            thumbnail_url_path = 'community/users/' + self.username + '/info/' + thumbnail_file
            if thumbnail_url_path:
                if not save_folder:
                    save_folder = self._workdir
                file_name = os.path.split(thumbnail_file)[1]
                if len(file_name) > 50: #If > 50 chars, truncate to last 30 chars
                    file_name = file_name[-30:]

                file_path = os.path.join(save_folder, file_name)
                return self._portal.con.get(path=thumbnail_url_path, try_json=False,
                                     out_folder=save_folder,
                                     file_name=file_name)
        else:
            return None

    @property
    def folders(self):
        """list of the user's folders"""
        return self._portal.user_folders(self.username)

    def items(self, folder=None, max_items=100):
        """Returns a list of items in the specified folder.

        For content in the root folder, use the default value of None for the folder.

        For other folders, pass in the folder name as a string, or a dict containing
        the folder 'id', such as the dict obtained from the folders property.
        """
        items = []
        folder_id = None
        if folder is not None:
            if isinstance(folder, str):
                folder_id = self._portal.get_folder_id(self.username, folder)
            elif isinstance(folder, dict):
                folder_id = folder['id']
            else:
                print("folder should be folder name as a string"
                      "or a dict containing the folder 'id'")

        resp = self._portal.user_items(self.username, folder_id, max_items)
        for item in resp:
            items.append(Item(self._gis, item['id'], item))

        return items
    #----------------------------------------------------------------------
    @property
    def notifications(self):
        """
        The list of notifications available for the given user.
        """
        from .._impl.notification import Notification
        result = []
        url = "%s/community/users/%s/notifications" % (self._portal.resturl, self.username)
        params = {"f" : "json"}
        ns = self._portal.con.get(url, params)
        if "notifications" in ns:
            for n in ns["notifications"]:
                result.append(Notification(url="%s/%s" % (url, n['id']),
                                           user=self,
                                           data=n,
                                           initialize=False)
                              )
                del n
            return result
        return result

class Item(dict):
    """
    An item (a unit of content) in the GIS. Each item has a unique identifier and a well
    known URL that is independent of the user owning the item.
    An item can have associated binary or textual data that's available via the item data resource.
    For example, an item of type Map Package returns the actual bits corresponding to the
    map package via the item data resource.

    Items that have layers (eg FeatureLayerCollection items and ImageryLayer items) and tables have
    the dynamic `layers` and `tables` properties to get to the individual layers/tables in this item.
    """

    def __init__(self, gis, itemid, itemdict=None):
        dict.__init__(self)
        self._portal = gis._portal
        self._gis = gis
        self.itemid = itemid
        self.thumbnail = None
        self._workdir = tempfile.gettempdir()
        self._hydrated = False
        self.resources = ResourceManager(self, self._gis)

        if itemdict:
            if 'size' in itemdict and itemdict['size'] == -1:
                del itemdict['size'] # remove nonsensical size
            self.__dict__.update(itemdict)
            super(Item, self).update(itemdict)
            if self._has_layers():
                self.layers = None
                self.tables = None
                self['layers'] = None
                self['tables'] = None

    def _has_layers(self):
        return self.type ==  'Feature Collection' or \
            self.type == 'Feature Service' or \
            self.type == 'Big Data File Share' or \
            self.type == 'Image Service' or \
            self.type == 'Map Service' or \
            self.type == 'Globe Service' or \
            self.type == 'Scene Service' or \
            self.type == 'Network Analysis Service' or \
            self.type == 'Vector Tile Service'

    def _populate_layers(self):
        from arcgis.features import FeatureLayer, FeatureCollection, FeatureLayerCollection, Table
        from arcgis.mapping import VectorTileLayer, MapImageLayer
        from arcgis.network import NetworkDataset
        from arcgis.raster import ImageryLayer

        if self._has_layers():
            layers = []
            tables = []

            params = {"f" : "json"}

            if self.type == 'Image Service': # service that is itself a layer
                layers.append(ImageryLayer(self.url, self._gis))

            elif self.type == 'Feature Collection':
                lyrs = self.get_data()['layers']
                for layer in lyrs:
                    layers.append(FeatureCollection(layer))

            elif self.type == 'Big Data File Share':
                serviceinfo = self._portal.con.post(self.url, params)
                for lyr in serviceinfo['children']:
                    lyrurl = self.url + '/' + lyr['name']
                    layers.append(Layer(lyrurl, self._gis))


            elif self.type == 'Vector Tile Service':
                layers.append(VectorTileLayer(self.url, self._gis))

            elif self.type == 'Network Analysis Service':
                svc = NetworkDataset.fromitem(self)

                # route laters, service area layers, closest facility layers
                for lyr in svc.route_layers:
                    layers.append(lyr)
                for lyr in svc.service_area_layers:
                    layers.append(lyr)
                for lyr in svc.closest_facility_layers:
                    layers.append(lyr)

            elif self.type == 'Feature Service':
                m = re.search(r'\d+$', self.url)
                if m is not None:  # ends in digit - it's a single layer from a Feature Service
                    layers.append(FeatureLayer(self.url, self._gis))
                else:
                    svc = FeatureLayerCollection.fromitem(self)
                    for lyr in svc.layers:
                        layers.append(lyr)
                    for tbl in svc.tables:
                        tables.append(tbl)

            elif self.type == 'Map Service':
                svc = MapImageLayer.fromitem(self)
                for lyr in svc.layers:
                    layers.append(lyr)
            else:
                m = re.search(r'\d+$', self.url)
                if m is not None: # ends in digit
                    layers.append(FeatureLayer(self.url, self._gis))
                else:
                    svc = _GISResource(self.url, self._gis)
                    for lyr in svc.properties.layers:
                        if self.type == 'Scene Service':
                            lyr_url = svc.url + '/layers/' + str(lyr.id)
                        else:
                            lyr_url = svc.url+'/'+str(lyr.id)
                        lyr = Layer(lyr_url, self._gis)
                        layers.append(lyr)
                    try:
                        for lyr in svc.properties.tables:
                            lyr = Table(svc.url+'/'+str(lyr.id), self._gis)
                            tables.append(lyr)
                    except:
                        pass

            self.layers = layers
            self.tables = tables
            self['layers'] = layers
            self['tables'] = tables

    def _hydrate(self):
        itemdict = self._portal.get_item(self.itemid)
        self._hydrated = True
        super(Item, self).update(itemdict)
        self.__dict__.update(itemdict)
        try:
            with _DisableLogger():
                self._populate_layers()
        except:
            pass

    def __getattribute__ (self, name):
        if name == 'layers':
            if self['layers'] == None or self['layers'] == []:
                try:
                    with _DisableLogger():
                        self._populate_layers()
                except:
                    pass
                return self['layers']
        elif name == 'tables':
            if self['tables'] == None or self['tables'] == []:
                try:
                    with _DisableLogger():
                        self._populate_layers()
                except:
                    pass
                return self['tables']
        return super(Item, self).__getattribute__(name)

    def __getattr__(self, name): # support item attributes
        if not self._hydrated and not name.startswith('_'):
            self._hydrate()
        try:
            return dict.__getitem__(self, name)
        except:
            raise AttributeError("'%s' object has no attribute '%s'" % (type(self).__name__, name))

    def __getitem__(self, k): # support item attributes as dictionary keys on this object
        try:
            return dict.__getitem__(self, k)
        except KeyError:
            if not self._hydrated and not k.startswith('_'):
                self._hydrate()
            return dict.__getitem__(self, k)

    def download(self, save_path=None):
        """
        Downloads the data to the specified folder or a temporary folder if a folder isn't provided
        :param save_path: Optional, location to download the file as a string
        :return: Returns download path if data was available else None.
        """
        data_path = 'content/items/' + self.itemid + '/data'
        if not save_path:
            save_path = self._workdir
        if data_path:
            download_path = self._portal.con.get(path=data_path, file_name=self.name or self.title,
                                        out_folder=save_path, try_json=False, force_bytes=False)
            if download_path == '':
                return None
            else:
                return download_path

    def export(self, title, export_format, parameters=None, wait=True):
        """
        Exports a service item to the specified output format.
        Available only to users with an organizational subscription.
        Invokable only by the service item owner or an administrator.

        Parameters:
         :export_format: The format to export the data to.
          Allowed types: 'Shapefile', 'CSV',
                   'File Geodatabase', 'Feature Collection',
                   'GeoJson', 'Scene Package', 'KML']
         :parameters: A JSON object describing the layers to be exported
          and the export parameters for each layer.
         :wait: boolean value that
        Output:
         Item or dictionary.  Item is returned when wait=True. A dictionary
         describing the status of the item is returned when wait=False.
         This means the user has to check if the item is exported
         successfully.  This is useful for long running exports that could
         hold up a script.
        """
        import time
        formats = ['Shapefile',
                   'CSV',
                   'File Geodatabase',
                   'Feature Collection',
                   'GeoJson',
                   'Scene Package',
                   'KML']
        data_path = 'content/users/%s/export' % self._gis.users.me.username
        params = {
            "f" : "json",
            "itemId" : self.itemid,
            "exportFormat" : export_format,
            "title" : title,
        }
        res = self._portal.con.post(data_path, params)
        export_item = Item(gis=self._gis, itemid=res['exportItemId'])
        if wait == True:
            status = "partial"
            while status != "completed":
                status = export_item.status(job_id=res['jobId'],
                                            job_type="export")
                if status['status'] == 'failed':
                    raise Exception("Could not export item: %s" % self.itemid)
                elif status['status'].lower() == "completed":
                    return export_item
                time.sleep(2)
        return res
    #----------------------------------------------------------------------
    def status(self, job_id=None, job_type=None):
        """
           Inquire about status when publishing an item, adding an item in
           async mode, or adding with a multipart upload. "Partial" is
           available for Add Item Multipart, when only a part is uploaded
           and the item is not committed.

           Input:
              job_type The type of asynchronous job for which the status has
                      to be checked. Default is none, which check the
                      item's status.  This parameter is optional unless
                      used with the operations listed below.
                      Values: publish, generateFeatures, export,
                              and createService
              job_id - The job ID returned during publish, generateFeatures,
                      export, and createService calls.
        """
        params = {
            "f" : "json"
        }
        data_path = 'content/users/%s/items/%s/status' % (self._gis.users.me.username, self.itemid)
        if job_type is not None:
            params['jobType'] = job_type
        if job_id is not None:
            params["jobId"] = job_id
        return self._portal.con.get(data_path,
                                    params)
    #----------------------------------------------------------------------
    def get_thumbnail(self):
        """ Returns the bytes that make up the thumbnail for this item.

        Arguments
            None.

        Returns
            bytes that represent the item.

        Example

        .. code-block:: python

            response = item.get_thumbnail()
            f = open(filename, 'wb')
            f.write(response)

        """
        thumbnail_file = self.thumbnail
        if thumbnail_file:
            thumbnail_url_path = 'content/items/' + self.itemid + '/info/' + thumbnail_file
            if thumbnail_url_path:
                return self._portal.con.get(thumbnail_url_path, try_json=False, force_bytes=True)

    def download_thumbnail(self, save_folder=None):
        """ Downloads the item thumbnail for this item, returns file path. """
        if self.thumbnail is None:
            self._hydrate()
        thumbnail_file = self.thumbnail

        # Only proceed if a thumbnail exists
        if thumbnail_file:
            thumbnail_url_path = 'content/items/' + self.itemid  + '/info/' + thumbnail_file
            if thumbnail_url_path:
                if not save_folder:
                    save_folder = self._workdir
                file_name = os.path.split(thumbnail_file)[1]
                if len(file_name) > 50: #If > 50 chars, truncate to last 30 chars
                    file_name = file_name[-30:]

                file_path = os.path.join(save_folder, file_name)
                self._portal.con.get(path=thumbnail_url_path, try_json=False,
                                     out_folder=save_folder,
                                     file_name=file_name)
                return file_path
        else:
            return None

    def get_thumbnail_link(self):
        """ URL to the thumbnail image """
        thumbnail_file = self.thumbnail
        if thumbnail_file is None:
            if self._gis.properties.portalName == 'ArcGIS Online':
                return 'http://static.arcgis.com/images/desktopapp.png'
            else:
                return self._portal.url + '/portalimages/desktopapp.png'
        else:
            thumbnail_url_path = self._portal.con.baseurl + '/content/items/' + self.itemid + '/info/' + thumbnail_file
            return thumbnail_url_path
    @property
    def metadata(self):
        """ Returns the item metadata for the specified item.
            Returns None if the item does not have metadata.
            Items with metadata have 'Metadata' in their typeKeywords
        """
        metadataurlpath = 'content/items/' + self.itemid  + '/info/metadata/metadata.xml'
        try:
            return self._portal.con.get(metadataurlpath, try_json=False)

        # If the get operation returns a 400 HTTP Error then the metadata simply
        # doesn't exist, let's just return None in this case
        except HTTPError as e:
            if e.code == 400 or e.code == 500:
                return None
            else:
                raise e

    #----------------------------------------------------------------------
    @metadata.setter
    def metadata(self, value):
        """
        For metadata enabled site, users can get/set metadata from a file
        or XML text.
        """
        import shutil
        from six import string_types
        xml_file = os.path.join(tempfile.gettempdir(), 'metadata.xml')
        if os.path.isfile(xml_file) == True:
            os.remove(xml_file)
        if os.path.isfile(value) == True and \
           str(value).lower().endswith('.xml'):
            if os.path.basename(value).lower() != 'metadata.xml':
                shutil.copy(value, xml_file)
            else:
                xml_file = value
        elif isinstance(value, string_types):
            with open(xml_file, mode='w') as writer:
                writer.write(value)
                writer.close()
        else:
            raise ValueError("Input must be XML path file or XML Text")
        return self.update(metadata=xml_file)

    def download_metadata(self, save_folder=None):
        """ Downloads the item metadata for the specified item id, returns file path.
            Returns None if the item does not have metadata.
            Items with metadata have 'Metadata' in their typeKeywords
        """
        metadataurlpath = 'content/items/' + self.itemid + '/info/metadata/metadata.xml'
        if not save_folder:
            save_folder = self._workdir
        try:
            file_name="metadata.xml"
            file_path = os.path.join(save_folder, file_name)
            self._portal.con.get(path=metadataurlpath,
                                     out_folder=save_folder,
                                     file_name=file_name, try_json=False)
            return file_path

        # If the get operation returns a 400 HTTP/IO Error then the metadata
        # simply doesn't exist, let's just return None in this case
        except HTTPError as e:
            if e.code == 400 or e.code == 500:
                return None
            else:
                raise e

    def _get_icon(self):
        icon = "layers16.png"
        if self.type.lower() == "web map":
            icon = "maps16.png"
        elif self.type.lower() == "web scene":
            icon = "websceneglobal16.png"
        elif self.type.lower() == "cityengine web scene":
            icon = "websceneglobal16.png"
        elif self.type.lower() == "pro map":
            icon = "mapsgray16.png"
        elif self.type.lower() == "feature service":
            icon = "featureshosted16.png"
        elif self.type.lower() == "map service":
            icon = "mapimages16.png"
        elif self.type.lower() == "image service":
            icon = "imagery16.png"
        elif self.type.lower() == "kml":
            icon = "features16.png"
        elif self.type.lower() == "wms":
            icon = "mapimages16.png"
        elif self.type.lower() == "feature collection":
            icon = "features16.png"
        elif self.type.lower() == "feature collection template":
            icon = "maps16.png"
        elif self.type.lower() == "geodata service":
            icon = "layers16.png"
        elif self.type.lower() == "globe service":
            icon = "layers16.png"
        elif self.type.lower() == "shapefile":
            icon = "datafiles16.png"
        elif self.type.lower() == "web map application":
            icon = "apps16.png"
        elif self.type.lower() == "map package":
            icon = "mapsgray16.png"
        elif self.type.lower() == "feature layer":
            icon = "featureshosted16.png"
        elif self.type.lower() == "map service":
            icon = "maptiles16.png"
        elif self.type.lower() == "map document":
            icon = "mapsgray16.png"
        else:
            icon = "layers16.png"

        icon = self._portal.url + '/home/js/jsapi/esri/css/images/item_type_icons/' + icon
        return icon

    def _ux_item_type(self):
        item_type= self.type
        if self.type == 'Geoprocessing Service':
            item_type = 'Geoprocessing Toolbox'
        elif self.type.lower() == 'feature service':
            item_type = 'Feature Layer Collection'
        elif self.type.lower() == 'map service':
            item_type = 'Map Image Layer'
        elif self.type.lower() == 'image service':
            item_type = 'Imagery Layer'
        elif self.type.lower().endswith('service'):
            item_type = self.type.replace('Service', 'Layer')
        return item_type

    def _repr_html_(self):
        thumbnail = self.thumbnail
        if self.thumbnail is None or not self._portal.is_logged_in:
            thumbnail = self.get_thumbnail_link()
        else:
            b64 = base64.b64encode(self.get_thumbnail())
            thumbnail = "data:image/png;base64," + str(b64,"utf-8") + "' width='200' height='133"

        snippet = self.snippet
        if snippet is None:
            snippet = ""

        portalurl = self._portal.url  + "/home/item.html?id=" + self.itemid

        locale.setlocale(locale.LC_ALL, '')
        numViews = locale.format("%d", self.numViews, grouping=True)
        return """<div class="item_container" style="height: auto; overflow: hidden; border: 1px solid #cfcfcf; border-radius: 2px; background: #f6fafa; line-height: 1.21429em; padding: 10px;">
                    <div class="item_left" style="width: 210px; float: left;">
                       <a href='""" + portalurl + """' target='_blank'>
                        <img src='""" + thumbnail + """' class="itemThumbnail">
                       </a>
                    </div>

                    <div class="item_right"     style="float: none; width: auto; overflow: hidden;">
                        <a href='""" + portalurl + """' target='_blank'><b>""" + self.title + """</b>
                        </a>
                        <br/>""" + snippet + """<img src='""" + self._get_icon() +"""' style="vertical-align:middle;">""" + self._ux_item_type() + """ by """ + self.owner + """
                        <br/>Last Modified: """ + datetime.datetime.fromtimestamp(self.modified/1000).strftime("%B %d, %Y") + """
                        <br/>""" + str(self.numComments) + """ comments, """ +  str(numViews) + """ views
                    </div>
                </div>
                """

    def __str__(self):
        return self.__repr__()
        # state = ["   %s=%r" % (attribute, value) for (attribute, value) in self.__dict__.items()]
        # return '\n'.join(state)

    def __repr__(self):
        return '<%s title:"%s" type:%s owner:%s>' % (type(self).__name__, self.title, self._ux_item_type(), self.owner)

    def reassign_to(self, target_owner, target_folder=None):
        """ Allows the administrator to reassign a single item from one user to another.

        .. note::
             	If you wish to move all of a user's items (and groups) to another user then use the
                user.reassign_to() method.  This method only moves one item at a time.

        ================  ========================================================
        **Argument**      **Description**
        ----------------  --------------------------------------------------------
        item_id           required string, unique identifier for the item
        ----------------  --------------------------------------------------------
        target_owner      required string, desired owner of the item
        ----------------  --------------------------------------------------------
        target_folder     optional string, folder to move the item to.
        ================  ========================================================

        :return:
            a boolean, indicating success

        """
        try:
            current_folder = self.ownerFolder
        except:
            current_folder = None
        resp = self._portal.reassign_item(self.itemid, self.owner, target_owner, current_folder, target_folder)
        if resp is True:
            self._hydrate() # refresh
            return resp

    def share(self, everyone=False, org=False, groups=None, allow_members_to_edit=False):
        """ Shares an item with the specified list of groups

        ================  ========================================================
        **Argument**      **Description**
        ----------------  --------------------------------------------------------
        everyone          optional boolean, share with everyone
        ----------------  --------------------------------------------------------
        org               optional boolean, share with the organization
        ----------------  --------------------------------------------------------
        groups            optional list of group names as strings, or, list of
                            arcgis.gis.Group objects
                          You can also pass a comma-separated list of group IDs
        ----------------  --------------------------------------------------------
        allow_members_to_edit  optional boolean to allow item to be shared with groups that allow shared update
        ================  ========================================================

        :return:
            dict with key "notSharedWith" containing array of groups with which the item could not be shared.

        """
        try:
            folder = self.ownerFolder
        except:
            folder = None

        #get list of group IDs
        group_ids = ''
        if isinstance(groups, list):
            for group in groups:
                if isinstance(group, Group):
                    group_ids = group_ids + "," + group.id

                elif isinstance(group, str):
                    #search for group using title
                    search_result = self._gis.groups.search(query='title:' + group, max_groups=1)
                    if len(search_result) >0:
                        group_ids = group_ids + "," + search_result[0].id
                    else:
                        raise Exception("Cannot find: " + group)
                else:
                    raise Exception("Invalid group(s)")

        elif isinstance(groups, str):
            #old API - groups sent as comma separated group ids
            group_ids = groups

        if self.access == 'public' and not everyone and not org:
            return self._portal.share_item_as_group_admin(self.itemid, group_ids, allow_members_to_edit)
        else:
            return self._portal.share_item(self.itemid, self.owner, folder, everyone, org, group_ids, allow_members_to_edit)

    def unshare(self, groups):
        """ Stops sharing the item with the specified list of groups

        ================  ========================================================
        **Argument**      **Description**
        ----------------  --------------------------------------------------------
        groups            optional list of group names as strings, or, list of
                            arcgis.gis.Group objects.
                          You can also pass a comma-separated list of group IDs
        ================  ========================================================

        :return:
            dict with key "notUnsharedFrom" containing array of groups from which the item could not be unshared.
        """
        try:
            folder = self.ownerFolder
        except:
            folder = None

        # get list of group IDs
        group_ids = ''
        if isinstance(groups, list):
            for group in groups:
                if isinstance(group, Group):
                    group_ids = group_ids + "," + group.id

                elif isinstance(group, str):
                    # search for group using title
                    search_result = self._gis.groups.search(query='title:' + group, max_groups=1)
                    if len(search_result) > 0:
                        group_ids = group_ids + "," + search_result[0].id
                    else:
                        raise Exception("Cannot find: " + group)
                else:
                    raise Exception("Invalid group(s)")

        elif isinstance(groups, str):
            # old API - groups sent as comma separated group ids
            group_ids = groups

        if self.access == 'public':
            return self._portal.unshare_item_as_group_admin(self.itemid, group_ids)
        else:
            return self._portal.unshare_item(self.itemid, self.owner, folder, group_ids)

    def delete(self):
        """ Deletes an item.

        :return:
            a boolean, indicating success

        """
        try:
            folder = self.ownerFolder
        except:
            folder = None
        return self._portal.delete_item(self.itemid, self.owner, folder)

    def update(self, item_properties=None, data=None, thumbnail=None, metadata=None):
        """ Updates an item in a Portal.


        .. note::
            That content can be a file (such as a layer package, geoprocessing package,
            map package) or it can be a URL (to an ArcGIS Server service, WMS service,
            or an application).

            If you are uploading a package or other file, provide a path or URL
            to the file in the data argument.

            Only pass in arguments for properties you want to update.
            All other properties will be left as they are.  If you
            want to update description, then only provide
            the description argument in item_properties.


        ============     ====================================================
        **Argument**     **Description**
        ------------     ----------------------------------------------------
        item_properties  optional dictionary, see below for the keys and values
        ------------     ----------------------------------------------------
        data             optional string, either a path or URL to the data
        ------------     ----------------------------------------------------
        thumbnail        optional string, either a path or URL to an image
        ------------     ----------------------------------------------------
        metadata         optional string, either a path or URL to metadata
        ============     ====================================================


        ================  ============================================================================
         **Key**           **Value**
        ----------------  ----------------------------------------------------------------------------
        type              optional string, indicates type of item.  See URL 1 below for valid values.
        ----------------  ----------------------------------------------------------------------------
        typeKeywords      optional string list.  Lists all sub-types.  See URL 1 for valid values.
        ----------------  ----------------------------------------------------------------------------
        description       optional string.  Description of the item.
        ----------------  ----------------------------------------------------------------------------
        title             optional string.  Name of the item.
        ----------------  ----------------------------------------------------------------------------
        url               optional string.  URL to item that are based on URLs.
        ----------------  ----------------------------------------------------------------------------
        tags              optional string of comma-separated values.  Used for searches on items.
        ----------------  ----------------------------------------------------------------------------
        snippet           optional string.  Provides a very short summary of the what the item is.
        ----------------  ----------------------------------------------------------------------------
        extent            optional string with comma separated values for min x, min y, max x, max y.
        ----------------  ----------------------------------------------------------------------------
        spatialReference  optional string.  Coordinate system that the item is in.
        ----------------  ----------------------------------------------------------------------------
        accessInformation optional string.  Information on the source of the content.
        ----------------  ----------------------------------------------------------------------------
        licenseInfo       optinal string, any license information or restrictions regarding the content.
        ----------------  ----------------------------------------------------------------------------
        culture           optional string.  Locale, country and language information.
        ----------------  ----------------------------------------------------------------------------
        access            optional string.  Valid values: private, shared, org, or public.
        ----------------  ----------------------------------------------------------------------------
        commentsEnabled   optional boolean.  Default is true.  Controls whether comments are allowed.
        ----------------  ----------------------------------------------------------------------------
        culture           optional string.  Language and country information.
        ================  ============================================================================


        URL 1: http://resources.arcgis.com/en/help/arcgis-rest-api/index.html#//02r3000000ms000000

        :return:
             a boolean, that indicates success.
        """
        try:
            folder = self.ownerFolder
        except:
            folder = None

        if item_properties is not None:
            if 'tags' in item_properties:
                if type(item_properties['tags']) is list:
                    item_properties['tags'] = ",".join(item_properties['tags'])

        ret = self._portal.update_item(self.itemid, item_properties, data, thumbnail, metadata, self.owner, folder)
        if ret:
            self._hydrate()
        return ret

    def get_data(self, try_json=True):
        """Returns the data for the item.
        Binary files are downloaded and the path to the downloaded file is returned.
        For JSON/text files, if try_json is True, the method tries to convert it to a Python dict and returns it, else
        returns the data as a string. Zero byte files will return None.
        To convert this dict to string use json.dumps(data).
        Else, returns the data as a byte array, that can be converted to string using data.decode('utf-8')"""
        item_data = self._portal.get_item_data(self.itemid, try_json)

        if item_data == '':
            return None
        elif type(item_data) == bytes:
            try:
                item_data_str = item_data.decode('utf-8')
                if item_data_str == '':
                    return None
                else:
                    return item_data
            except:
                return item_data
        else:
            return item_data

    def dependent_upon(self):
        """ Returns items and urls, etc that this items depends upon  """
        return self._portal.get_item_dependencies(self.itemid)

    def dependent_to(self):
        """ Returns items and urls, etc dependend upon this item. """
        return self._portal.get_item_dependents_to(self.itemid)

    _RELATIONSHIP_TYPES = frozenset(['Map2Service', 'WMA2Code',
                                     'Map2FeatureCollection', 'MobileApp2Code', 'Service2Data',
                                     'Service2Service'])

    _RELATIONSHIP_DIRECTIONS = frozenset(['forward', 'reverse'])

    def related_items(self, rel_type, direction="forward"):
        """ Returns items related to this item. Relationsships can be added and deleted using item.add_relationship() and item.delete_relationship() respectively.
        rel_type is one of ['Map2Service', 'WMA2Code', 'Map2FeatureCollection', 'MobileApp2Code', 'Service2Data', 'Service2Service']
        direction is one of ['forward', 'reverse'] """
        if not rel_type in self._RELATIONSHIP_TYPES:
            raise Error('Unsupported relationship type: ' + rel_type)
        if not direction in self._RELATIONSHIP_DIRECTIONS:
            raise Error('Unsupported direction: ' + direction)

        related_items = []

        postdata = { 'f' : 'json' }
        postdata['relationshipType'] = rel_type
        postdata['direction'] = direction
        resp = self._portal.con.post('content/items/' + self.itemid + '/relatedItems', postdata)
        for related_item in resp['relatedItems']:
            related_items.append(Item(self._gis, related_item['id'], related_item))
        return related_items

    def add_relationship(self, rel_item, rel_type):
        """ Adds a relationship from this item to rel_item.
        Relationships are not tied to an item. They are directional links from an origin item
        to a destination item and have a type. The type defines the valid origin and destination
        item types as well as some rules. See Relationship types in REST API help for more information.
        Users don't have to own the items they relate unless so defined by the rules of the
        relationship type.
        Users can only delete relationships they create.
        Relationships are deleted automatically if one of the two items is deleted.

        rel_item is the related item
        rel_type is one of ['Map2Service', 'WMA2Code', 'Map2FeatureCollection', 'MobileApp2Code', 'Service2Data', 'Service2Service']. See Relationship types in REST API help for more information on this parameter
        Returns True if the relationship was added
        """
        if not rel_type in self._RELATIONSHIP_TYPES:
            raise Error('Unsupported relationship type: ' + rel_type)

        postdata = { 'f' : 'json' }
        postdata['originItemId'] = self.itemid
        postdata['destinationItemId'] = rel_item.itemid
        postdata['relationshipType'] = rel_type
        path = 'content/users/' + self.owner

        path += '/addRelationship'

        resp = self._portal.con.post(path, postdata)
        if resp:
            return resp.get('success')

    def delete_relationship(self, rel_item, rel_type):
        """ Deletes a relationship between this item and the rel_item.
        rel_item is the related item
        rel_type is one of ['Map2Service', 'WMA2Code', 'Map2FeatureCollection', 'MobileApp2Code', 'Service2Data', 'Service2Service']
        Returns True if the relationship was deleted
        """
        if not rel_type in self._RELATIONSHIP_TYPES:
            raise Error('Unsupported relationship type: ' + rel_type)
        postdata = { 'f' : 'json' }
        postdata['originItemId'] =  self.itemid
        postdata['destinationItemId'] = rel_item.itemid
        postdata['relationshipType'] = rel_type
        path = 'content/users/' + self.owner


        path += '/deleteRelationship'
        resp = self._portal.con.post(path, postdata)
        if resp:
            return resp.get('success')

    def publish(self, publish_parameters=None, address_fields=None, output_type=None, overwrite=False,
                file_type=None):
        """
        Publishes a hosted service based on an existing source item (this item).
        Publishers can create feature, tiled map, vector tile and scene services.

        Feature services can be created using input files of type csv, shapefile, serviceDefinition, featureCollection, and fileGeodatabase.
        CSV files that contain location fields, (ie.address fields or X, Y fields) are spatially enabled during the process of publishing.
        Shapefiles and file geodatabases should be packaged as *.zip files.

        Tiled map services can be created from service definition (*.sd) files, tile packages, and existing feature services.

        Vector tile services can be created from vector tile package (*.vtpk) files.

        Scene services can be created from scene layer package (*.spk, *.slpk) files.

        Service definitions are authored in ArcGIS for Desktop and contain both the cartographic definition for a map
        as well as its packaged data together with the definition of the geo-service to be created.

        ================    ===============================================================
        **Argument**        **Description**
        ----------------    ---------------------------------------------------------------
        publish_parameters  dictionary containing publish instructions and customizations.
                            Cannot be combined with overwrite.
        ----------------    ---------------------------------------------------------------
        address_fields      dict containing mapping of df columns to address fields,
                            eg: { "CountryCode" : "Country"} or { "Address" : "Address" }
        ----------------    ---------------------------------------------------------------
        output_type         Only used when a feature service is published as a tile service.
                            eg: output_type='Tiles'
        ----------------    ---------------------------------------------------------------
        overwrite           If True, the hosted feature service is overwritten.
                            Only available in ArcGIS Online and Portal for ArcGIS 10.5 or later.
        ----------------    ---------------------------------------------------------------
        file_type           Some formats are not automatically detected, when this occurs, the
                            file_type can be specified: serviceDefinition,shapefile,csv,
                            tilePackage, featureService, featureCollection, fileGeodatabase,
                            geojson, scenepackage, vectortilepackage, imageCollection,
                            mapService, and sqliteGeodatabase are valid entries. This is an
                            optional parameter.
        ================    ===============================================================

        :return:
            an arcgis.gis.Item object corresponding to the published web layer

        .. note::
             	ArcGIS does not permit overwriting if you published multiple hosted feature layers from the same data item.
        """

        import time
        params = {
            "f" : "json"
        }
        buildInitialCache = False
        if file_type is None:
            if self['type'] == 'Service Definition':
                fileType = 'serviceDefinition'
            elif self['type'] == 'Feature Collection':
                fileType = 'featureCollection'
            elif self['type'] == 'CSV':
                fileType = 'CSV'
            elif self['type'] == 'Shapefile':
                fileType = 'shapefile'
            elif self['type'] == 'File Geodatabase':
                fileType = 'fileGeodatabase'
            elif self['type'] == 'Vector Tile Package':
                fileType = 'vectortilepackage'
            elif self['type'] == 'Scene Package':
                fileType = 'scenePackage'
            elif self['type'] == 'Tile Package':
                fileType = 'tilePackage'
            elif self['type'] == 'SQLite Geodatabase':
                fileType = 'sqliteGeodatabase'
            elif self['type'] == 'GeoJson':
                fileType = 'geojson'
            else:
                raise ValueError("A file_type must be provide, data format not recognized")
        else:
            fileType = file_type
        try:
            folder = self.ownerFolder
        except:
            folder = None

        if publish_parameters is None:
            if fileType == 'shapefile' and not overwrite:
                publish_parameters =  {"hasStaticData":True, "name":os.path.splitext(self['name'])[0],
                                       "maxRecordCount":2000, "layerInfo":{"capabilities":"Query"} }

            elif fileType == 'CSV' and not overwrite:
                path = "content/features/analyze"

                postdata = {
                    "f": "pjson",
                    "itemid" : self.itemid,
                    "filetype" : "csv",

                    "analyzeParameters" : {
                        "enableGlobalGeocoding": "true",
                        "sourceLocale":"en-us",
                        #"locationType":"address",
                        "sourceCountry":"",
                        "sourceCountryHint":""
                    }
                }

                if address_fields is not None:
                    postdata['analyzeParameters']['locationType'] = 'address'

                res = self._portal.con.post(path, postdata)
                publish_parameters =  res['publishParameters']
                if address_fields is not None:
                    publish_parameters.update({"addressFields":address_fields})

                # use csv title for service name, after replacing non-alphanumeric characters with _
                service_name = re.sub(r'[\W_]+', '_', self['title'])
                publish_parameters.update({"name": service_name})

            elif fileType in ['CSV', 'shapefile', 'fileGeodatabase'] and overwrite: #need to construct full publishParameters
                #find items with relationship 'Service2Data' in reverse direction - all feature services published using this data item
                related_items = self.related_items('Service2Data', 'reverse')

                return_item_list = []
                if len (related_items) == 1: #simple 1:1 relationship between data and service items
                    r_item = related_items[0]
                    #construct a FLC manager
                    from arcgis.features import FeatureLayerCollection
                    flc = FeatureLayerCollection.fromitem(r_item)
                    flc_mgr = flc.manager

                    #get the publish parameters from FLC manager
                    publish_parameters = flc_mgr._gen_overwrite_publishParameters(r_item)

                elif len(related_items) == 0:
                    # the CSV item was never published. Hence overwrite should work like first time publishing - analyze csv
                    path = "content/features/analyze"
                    postdata = {
                        "f": "pjson",
                        "itemid" : self.itemid,
                        "filetype" : "csv",

                        "analyzeParameters" : {
                            "enableGlobalGeocoding": "true",
                            "sourceLocale":"en-us",
                            #"locationType":"address",
                            "sourceCountry":"",
                            "sourceCountryHint":""
                        }
                    }

                    if address_fields is not None:
                        postdata['analyzeParameters']['locationType'] = 'address'

                    res = self._portal.con.post(path, postdata)
                    publish_parameters =  res['publishParameters']
                    if address_fields is not None:
                        publish_parameters.update({"addressFields":address_fields})

                    # use csv title for service name, after replacing non-alphanumeric characters with _
                    service_name = re.sub(r'[\W_]+', '_', self['title'])
                    publish_parameters.update({"name": service_name})

                elif len(related_items) > 1:
                    # length greater than 1, then 1:many relationship
                    raise RuntimeError("User cant overwrite this service, using this data, as this data is already referring to another service.")

            elif fileType == 'vectortilepackage':
                name = re.sub(r'[\W_]+', '_', self['title'])
                publish_parameters = {'name': name, 'maxRecordCount':2000}
                output_type = 'VectorTiles'
                buildInitialCache = True

            elif fileType == 'scenePackage':
                name = re.sub(r'[\W_]+', '_', self['title'])
                publish_parameters = {'name': name, 'maxRecordCount':2000}
                output_type = 'sceneService'

            elif fileType == 'tilePackage':
                name = re.sub(r'[\W_]+', '_', self['title'])
                publish_parameters = {'name': name, 'maxRecordCount':2000}
                buildInitialCache = True
            elif fileType == 'sqliteGeodatabase':
                name = re.sub(r'[\W_]+', '_', self['title'])
                publish_parameters = {"name":name,
                                      'maxRecordCount':2000,
                                      "capabilities":"Query, Sync"}
            else: #sd files
                name = re.sub(r'[\W_]+', '_', self['title'])
                publish_parameters =  {"hasStaticData":True, "name": name, "maxRecordCount":2000, "layerInfo":{"capabilities":"Query"} }

        elif fileType == 'CSV': # merge users passed-in publish parameters with analyze results
            publish_parameters_orig = publish_parameters
            path = "content/features/analyze"

            postdata = {
                "f": "pjson",
                "itemid" : self.itemid,
                "filetype" : "csv",

                "analyzeParameters" : {
                    "enableGlobalGeocoding": "true",
                    "sourceLocale":"en-us",
                    #"locationType":"address",
                    "sourceCountry":"",
                    "sourceCountryHint":""
                }
            }

            if address_fields is not None:
                postdata['analyzeParameters']['locationType'] = 'address'

            res = self._portal.con.post(path, postdata)
            publish_parameters =  res['publishParameters']
            publish_parameters.update(publish_parameters_orig)

        ret = self._portal.publish_item(self.itemid, None, None, fileType, publish_parameters, output_type, overwrite,
                                        self.owner, folder, buildInitialCache)

        #Check publishing job status
        serviceitem_id = self._check_publish_status(ret, folder)

        return Item(self._gis, serviceitem_id)

    def move(self, folder, owner=None):
        """ Move this item to the folder with the given name.

        ================  ===============================================================
        **Argument**      **Description**
        ----------------  ---------------------------------------------------------------
        folder            required string, the name of the folder to move the item to.
                          Use '/' for the root folder. For other folders, pass in the
                          folder name as a string, or a dict containing the folder 'id',
                          such as the dict obtained from the folders property.
        ================  ===============================================================

        :return:
            a json object like the following:
            {
               "success": true | false,
               "itemId": "<item id>",
               "owner": "<owner username>",
               "folder": "<folder id>"
            }


        """
        owner_name = self._portal.logged_in_user()['username']

        folder_id = None
        if folder is not None:
            if isinstance(folder, str):
                if folder == '/':
                    folder_id = '/'
                else:
                    folder_id = self._portal.get_folder_id(owner_name, folder)
            elif isinstance(folder, dict):
                folder_id = folder['id']
            else:
                print("folder should be folder name as a string, or dict with id")

        if folder_id is not None:
            ret = self._portal.move_item(self.itemid, owner_name, self.ownerFolder, folder_id)
            self._hydrate()
            return ret
        else:
            print('Folder not found for given owner')
            return None

    def protect(self, enable=True):
        """ Enable or disable delete protection on the item

        ================  ===============================================================
        **Argument**      **Description**
        ----------------  ---------------------------------------------------------------
        enable            optional boolean, True to enable delete protection, False to
                          to disable it
        ================  ===============================================================

        :return:
            a json object like the following:
            {
               "success": true | false
            }


        """
        try:
            folder = self.ownerFolder
        except:
            folder = None
        return self._portal.protect_item(self.itemid, self.owner, folder, enable)

    def _check_publish_status(self, ret, folder):
        """
        Internal method to check the status of a publishing job.
        :param ret: Dictionary representing the result of a publish REST call. This dict should contain the
                    `serviceItemId` and `jobId` of the publishing job
        :param folder: obtained from self.ownerFolder
        :return:
        """
        import time
        try:
            serviceitem_id = ret[0]['serviceItemId']
        except KeyError as ke:
            raise RuntimeError(ret[0]['error']['message'])

        if 'jobId' in ret[0]:
            job_id = ret[0]['jobId']
            path = 'content/users/' + self.owner
            if folder is not None:
                path = path + '/' + folder + '/'

            path = path + '/items/' + serviceitem_id + '/status'
            params = {
                "f" : "json",
                "jobid" : job_id
            }
            job_response = self._portal.con.post(path, params)

            # Query and report the Analysis job status.
            #
            num_messages = 0
            #print(str(job_response))
            if "status" in job_response:
                while not job_response.get("status") == "completed":
                    time.sleep(5)

                    job_response = self._portal.con.post(path, params)

                    #print(str(job_response))
                    if job_response.get("status") in ("esriJobFailed","failed"):
                        raise Exception("Job failed.")
                    elif job_response.get("status") == "esriJobCancelled":
                        raise Exception("Job cancelled.")
                    elif job_response.get("status") == "esriJobTimedOut":
                        raise Exception("Job timed out.")

            else:
                raise Exception("No job results.")
        else:
            raise Exception("No job id")

        return serviceitem_id
    #----------------------------------------------------------------------
    @property
    def comments(self):
        """
        returns a list of comments on a given item
        """
        from .._impl.comments import Comment
        cs = []
        start = 1
        num = 100
        nextStart = 0
        url = "%s/content/items/%s/comments" % (self._portal.url, self.id)
        while nextStart != -1:
            params = {
                "f" : "json",
                "start" : start,
                "num" : num
            }
            res = self._portal.con.post(url, params)
            for c in res['comments']:
                cs.append(Comment(url="%s/%s" % (url, c['id']),
                                  item=self, initialize=False))
            start += num
            nextStart = res['nextStart']
        return cs
    #----------------------------------------------------------------------
    def add_comment(self, comment):
        """
        Adds a comment to an item. Available only to authenticated users
        who have access to the item.

        Parameters:
         :comment: text comment to a specific item
        Output:
         comment ID is successful, None on failure
        """
        params = {
            "f" : "json",
            "comment" : comment
        }
        url = "%s/content/items/%s/addComment" % (self._portal.url, self.id)
        res = self._portal.con.post(url, params)
        if 'commentId' in res:
            return res['commentId']
        return None
    #----------------------------------------------------------------------
    @property
    def rating(self):
        """
        Returns the rating given by the current user to the item, if any.
        """
        url = "%s/content/items/%s/rating" % (self._portal.url, self.id)
        params = {"f" : "json"}
        res = self._portal.con.get(url, params)
        if 'rating' in res:
            return res['rating']
        return None
    #----------------------------------------------------------------------
    @rating.setter
    def rating(self, value):
        """
        Adds a rating to an item to which you have access. Only one rating
        can be given to an item per user. If this call is made on a
        currently rated item, the new rating will overwrite the existing
        rating. A user cannot rate their own item. Available only to
        authenticated users.

        Parameters:
         :value: Rating to set for the item. Rating must be a floating
          point number between 1.0 and 5.0.
        """
        url = "%s/content/items/%s/addRating" % (self._portal.url,
                                                 self.id)
        params = {"f" : "json",
                  'rating' : float(value)}
        res = self._portal.con.post(url, params)
    #----------------------------------------------------------------------
    def delete_rating(self):
        """
        Removes the rating the calling user added for the specified item
        """
        url = "%s/content/items/%s/deleteRating" % (self._portal.url,
                                                    self.id)
        params = {"f" : "json"}
        res = self._portal.con.post(url, params)
        if 'success' in res:
            return res['success']
        return res
    #----------------------------------------------------------------------
    @property
    def proxies(self):
        """
        All ArcGIS Online hosted proxy services set on a registered app
        item with the Registered App type keyword. This resource is only
        available to the item owner and the organization administrator.
        """
        url = "%s/content/users/%s/items/%s/proxies" % (self._portal.url,
                                                        self.owner,
                                                        self.id)
        params = {"f" : "json"}
        ps = []
        try:
            res = self._portal.con.get(url, params)
            if 'appProxies' in res:
                for p in res['appProxies']:
                    ps.append(p)
        except:
            return []
        return ps

def rot13(s):
    if s is None:
        return None
    result = ""

    # Loop over characters.
    for v in s:
        # Convert to number with ord.
        c = ord(v)

        # Shift number back or forward.
        if c >= ord('a') and c <= ord('z'):
            if c > ord('m'):
                c -= 13
            else:
                c += 13
        elif c >= ord('A') and c <= ord('Z'):
            if c > ord('M'):
                c -= 13
            else:
                c += 13

        # Append to result.
        result += chr(c)

    # Return transformation.
    return result


class _GISResource(object):
    """ a GIS service
    """
    def __init__(self, url, gis=None):
        from .._impl._server._common import ServerConnection
        from .._impl.connection import _ArcGISConnection
        self._hydrated = False
        self.url = url
        self._url = url

        if gis is None:
            gis = GIS(set_active=False)
            self._gis = gis
            self._con = gis._con
        #elif isinstance(gis, (ServerConnection, _ArcGISConnection)):
            #self._gis = GIS(set_active=False)
            #self._con = gis
        else:
            self._gis = gis
            if isinstance(gis, (ServerConnection, _ArcGISConnection)):
                self._con = gis
            else:
                self._con = gis._con

    @classmethod
    def fromitem(cls, item):
        if not item.type.lower().endswith('service'):
            raise TypeError("item must be a type of service, not " + item.type)
        return cls(item.url, item._gis)

    def _refresh(self):
        params = {"f": "json"}
        dictdata = self._con.post(self.url, params, token=self._lazy_token)
        self._lazy_properties = PropertyMap(dictdata)

    @property
    def properties(self):
        """The properties of this object"""
        if self._hydrated:
            return self._lazy_properties
        else:
            self._hydrate()
            return self._lazy_properties

    @properties.setter
    def properties(self, value):
        self._lazy_properties = value

    def _hydrate(self):
        """Fetches properties and deduces token while doing so"""
        self._lazy_token = None
        err = None

        with _DisableLogger():
            try:
                # try as a federated server
                if self._con._token is None:
                    self._lazy_token = None
                else:
                    if isinstance(self._con, arcgis._impl._ArcGISConnection):
                        self._lazy_token = self._con.generate_portal_server_token(self._url)
                    else:
                        self._lazy_token = self._con.token

                self._refresh()

            except HTTPError as httperror:  # service maybe down
                _log.error(httperror)
                err = httperror
            except RuntimeError as e:
                try:
                    # try as a public server
                    self._lazy_token = None
                    self._refresh()

                except HTTPError as httperror:
                    _log.error(httperror)
                    err = httperror
                except RuntimeError as e:
                    if 'Token Required' in e.args[0]:
                        # try token in the provided gis
                        self._lazy_token = self._con.token
                        self._refresh()

        if err is not None:
            raise RuntimeError('HTTPError: this service url encountered an HTTP Error: ' + self.url)

        self._hydrated = True

    @property
    def _token(self):
        if self._hydrated:
            return self._lazy_token
        else:
            self._hydrate()
            return self._lazy_token


    def __str__(self):
        return '<%s url:"%s">' % (type(self).__name__, self.url)

    def __repr__(self):
        return '<%s url:"%s">' % (type(self).__name__, self.url)

    def _invoke(self, method, **kwargs):
        """Invokes the specified method on this service passing in parameters from the kwargs name-value pairs"""
        url = self._url + "/" + method
        params = { "f" : "json"}
        if len(kwargs) > 0:
            for k,v in kwargs.items():
                params[k] = v
                del k,v
        return self._con.post(path=url, postdata=params, token=self._token)


class Layer(_GISResource):
    """
    The layer is a primary concept for working with data in a GIS.

    Users create, import, export, analyze, edit, and visualize layers.

    Layers can be added to and visualized using maps. They act as inputs to and outputs from analysis tools.

    Layers are created by publishing data to a GIS, and are exposed as a broader resource (Item) in the
    GIS. Layer objects can be obtained through the layers attribute on layer Items in the GIS.
    """

    def __init__(self, url, gis=None):
        super(Layer, self).__init__(url, gis)
        self.filter = None

    @classmethod
    def fromitem(cls, item, index=0):
        """
        returns the layer at the specified index from a layer item
        :param item: an item representing a layer
        :param index: optional, the index of the layer amongst the item's layers
        :return: the layer at the specified index
        """
        return item.layers[index]

    @property
    def _lyr_dict(self):
        url = self.url

        lyr_dict =  { 'type' : type(self).__name__, 'url' : url }
        if self._token is not None:
            lyr_dict['serviceToken'] = self._token

        if self.filter is not None:
            lyr_dict['filter'] = self.filter

        return lyr_dict

    @property
    def _lyr_json(self):
        url = self.url
        if self._token is not None:  # causing geoanalytics Invalid URL error
            url += '?token=' + self._token

        lyr_dict = {'type': type(self).__name__, 'url': url}

        return lyr_dict
