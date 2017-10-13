"""
Represents messages left by users on a given Item in the GIS
"""
from __future__ import absolute_import
import json
from .connection import _ArcGISConnection
from ..gis import GIS, User
########################################################################
class Notification(dict):
    """
    Represents messages left by users on a given Item in the GIS
    """
    _gis = None
    _portal = None
    _item = None
    _con = None
    _json_dict = None
    _json = None
    _hydrated = None
    def __init__(self, url, user, data=None, initialize=True, **kwargs):
        """
        class initializer

        Parameters:
         :url: web address to the resource
         :item: arcgis.gis.Item class where the comment originate from
         :data: allows the object to be pre-populated with information from
          a dictionary
         :initialize: if True, on creation, the object will hydrate itself.
        """
        super(Notification, self).__init__()
        self._url = url
        self._gis = item._gis
        self._portal = self._gis._portal
        isinstance(user, User)

        if isinstance(user._gis, _ArcGISConnection):
            self._con = user._gis
        elif isinstance(user._gis, GIS):
            self._gis = user._gis
            self._con = user._gis._con
        else:
            raise ValueError(
                "connection must be of type GIS or _ArcGISConnection")
        if data and \
           isinstance(data, dict):
            for k,v in data.items():
                self[k] = v
            self.__dict__.update(data)
        if initialize:
            self._init(connection=self._con)
            self._hydrated = True
        else:
            self._hydrated = False
    #----------------------------------------------------------------------
    def _init(self, connection=None):
        """loads the properties into the class"""
        if connection is None:
            connection = self._con
        attributes = [attr for attr in dir(self)
                      if not attr.startswith('__') and \
                      not attr.startswith('_')]
        params = {"f":"json"}
        result = connection.get(path=self._url,
                                params=params)
        self._json_dict = result
        for k,v in result.items():
            if k in attributes:
                setattr(self, "_"+ k, v)
                self[k] = v
            else:
                self[k] = v
        self.__dict__.update(result)
    #----------------------------------------------------------------------
    def __getattr__(self, name):
        if not self._hydrated and not name.startswith('_'):
            self._init()
        try:
            return self.__dict__[name]
        except:
            raise AttributeError("'%s' object has no attribute '%s'" % (type(self).__name__, name))
    #----------------------------------------------------------------------
    def __getitem__(self, k):
        try:
            return self.__dict__[k]
        except KeyError:
            if not self._hydrated and not k.startswith('_'):
                self._init()
            return self.__dict__[k]
    #----------------------------------------------------------------------
    def delete(self):
        """
        removes a given notification
        """
        url = "%s/delete" % self._url
        params = {"f" : "json"}
        res = self._con.post(path=url,
                             postdata=params)
        if 'success' in res:
            return res['success']
        return res

