""" The portalpy module for working with the ArcGIS Online and Portal APIs."""


from __future__ import absolute_import
import copy
import json
import imghdr
import logging
import os
import tempfile
from .connection import _ArcGISConnection, _normalize_url
from .connection import _is_http_url
from .connection import _parse_hostname, _unpack
from .common._utils import _to_utf8
from six.moves.urllib import request
from six.moves.urllib_parse import urlparse

__version__ = '1.0'

_log = logging.getLogger(__name__)

class Portal(object):
    """ An object representing a connection to a single portal (via URL).

    .. note:: To instantiate a Portal object execute code like this:

            PortalPy.Portal(portalUrl, user, password)

        There are a few things you should know as you use the methods below.

        Group IDs - Many of the group functions require a group id.  This id is
        different than the group's name or title.  To determine
        a group id, use the search_groups function using the title
        to get the group id.

        Time - Many of the methods return a time field.  All time is
        returned as millseconds since 1 January 1970.  Python
        expects time in seconds since 1 January 1970 so make sure
        to divide times from PortalPy by 1000.  See the example
        a few lines down to see how to convert from PortalPy time
        to Python time.

    Example - converting time

    .. code-block:: python

        import time
        .
        .
        .
        group = portalAdmin.get_group('67e1761068b7453693a0c68c92a62e2e')
        pythontime = time.ctime(group['created']/1000)

    Example - list users in group

    .. code-block:: python

        portal = PortalPy.Portal(portalUrl, user, password)
        resp = portal.get_group_members('67e1761068b7453693a0c68c92a62e2e')
        for user in resp['users']:
            print user

    Example - create a group

    .. code-block:: python

        portal= PortalPy.Portal(portalUrl, user, password)
        group_id = portalAdmin.create_group('my group', 'test tag', 'a group to share travel maps')

    Example - delete a user named amy and assign her content to bob

    .. code-block:: python

        portal = PortalPy.Portal(portalUrl, user, password)
        portal.delete_user('amy.user', True, 'bob.user')

    """
    _is_arcpy = False
    def __init__(self, url, username=None, password=None, key_file=None,
                 cert_file=None, expiration=60, referer=None, proxy_host=None,
                 proxy_port=None, connection=None, workdir=tempfile.gettempdir(),
                 tokenurl=None, verify_cert=True, client_id=None):
        """ The Portal constructor. Requires URL and optionally username/password."""
        url = url.strip()            # be permissive in accepting home app urls
        homepos = url.find('/home')
        if homepos != -1:
            url = url[:homepos]

        self._is_arcpy = url.lower() == "pro"
        if self._is_arcpy:
            try:
                import arcpy
                url = arcpy.GetActivePortalURL()
                self.url = url
            except ImportError:
                raise ImportError("Could not import arcpy")
            except:
                raise ValueError("Could not use Pro authentication.")
        else:
            self.url = url

        if url:
            normalized_url = self.url
            '''_normalize_url(self.url)'''
            if not normalized_url[-1] == '/':
                normalized_url += '/'
            if normalized_url.lower().find("www.arcgis.com") > -1:
                urlscheme = urlparse(normalized_url).scheme
                self.resturl = "{scheme}://www.arcgis.com/sharing/rest/".format(scheme=urlscheme)
            elif normalized_url.lower().endswith("sharing/"):
                self.resturl = normalized_url + 'rest/'
            elif normalized_url.lower().endswith("sharing/rest/"):
                self.resturl = normalized_url
            else:
                self.resturl = normalized_url + 'sharing/rest/'
            self.hostname = _parse_hostname(url)
        self.workdir = workdir

        # Setup the instance members
        self._basepostdata = { 'f': 'json' }
        self._version = None
        self._properties = None
        self._resources = None
        self._languages = None
        self._regions = None
        self._is_pre_162 = False
        self._is_pre_21 = False

        # If a connection was passed in, use it, otherwise setup the
        # connection (use all SSL until portal informs us otherwise)
        if connection:
            _log.debug('Using existing connection to: ' + \
                       _parse_hostname(connection.baseurl))
            self.con = connection
        if not connection:
            _log.debug('Connecting to portal: ' + self.hostname)
            if self._is_arcpy:
                self.con = _ArcGISConnection(baseurl="pro",
                                             tokenurl=tokenurl,
                                             username=username,
                                             password=password,
                                             key_file=key_file,
                                             cert_file=cert_file,
                                             expiration=expiration,
                                             all_ssl=True,
                                             referer=referer,
                                             proxy_host=proxy_host,
                                             proxy_port=proxy_port,
                                             verify_cert=verify_cert)
            else:
                self.con = _ArcGISConnection(baseurl=self.resturl,
                                             tokenurl=tokenurl,
                                             username=username,
                                             password=password,
                                             key_file=key_file,
                                             cert_file=cert_file,
                                             expiration=expiration,
                                             all_ssl=True,
                                             referer=referer,
                                             proxy_host=proxy_host,
                                             proxy_port=proxy_port,
                                             verify_cert=verify_cert,
                                             client_id=client_id)
        #self.get_version(True)
        self.get_properties(True)



    def add_group_users(self, user_names, group_id):
        """ Adds users to the group specified.

        .. note::
            This method will only work if the user for the
            Portal object is either an administrator for the entire
            Portal or the owner of the group.

        ============  ======================================
        **Argument**  **Description**
        ------------  --------------------------------------
        user_names    list of usernames
        ------------  --------------------------------------
        group_id      required string, specifying group id
        ============  ======================================

        :return:
             A dictionary with a key of "not_added" which contains the users that were not
             added to the group.
        """


        if self._is_pre_21:
            _log.warning('The auto_accept option is not supported in ' \
                         + 'pre-2.0 portals')
            return

        #user_names = _unpack(user_names, 'username')

        postdata = self._postdata()
        postdata['users'] = ','.join(user_names)
        resp = self.con.post('community/groups/' + group_id + '/addUsers',
                             postdata)
        return resp

    def add_item(self, item_properties, data=None, thumbnail=None, metadata=None, owner=None, folder=None):
        """ Adds content to a Portal.


        .. note::
            That content can be a file (such as a layer package, geoprocessing package,
            map package) or it can be a URL (to an ArcGIS Server service, WMS service,
            or an application).

            If you are uploading a package or other file, provide a path or URL
            to the file in the data argument.

            From a technical perspective, none of the item properties below are required.  However,
            it is strongly recommended that title, type, typeKeywords, tags, snippet, and description
            be provided.


        ============     ====================================================
        **Argument**     **Description**
        ------------     ----------------------------------------------------
        item_properties  required dictionary, see below for the keys and values
        ------------     ----------------------------------------------------
        data             optional string, either a path or URL to the data
        ------------     ----------------------------------------------------
        thumbnail        optional string, either a path or URL to an image
        ------------     ----------------------------------------------------
        metadata         optional string, either a path or URL to metadata.
        ------------     ----------------------------------------------------
        owner            optional string, defaults to logged in user.
        ------------     ----------------------------------------------------
        folder           optional string, content folder where placing item
        ============     ====================================================


        ================  ============================================================================
         **Key**           **Value**
        ----------------  ----------------------------------------------------------------------------
        type              optional string, indicates type of item.  See URL 1 below for valid values.
        ----------------  ----------------------------------------------------------------------------
        typeKeywords      optinal string list.  Lists all sub-types.  See URL 1 for valid values.
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
             The item id of the uploaded item if successful, None if unsuccessful.
        """


        # Postdata is a dictionary object whose keys and values will be sent via an HTTP Post.
        postdata = self._postdata()
        postdata.update(_to_utf8(item_properties))

        # Build the files list (tuples)
        files = []
        if data:
            if _is_http_url(data):
                data = request.urlretrieve(data)[0]
            else:
                if not os.path.isfile(os.path.abspath(data)):
                    raise RuntimeError("File("+data+") not found.")
            files.append(('file', data, os.path.basename(data)))
        if metadata:
            if _is_http_url(metadata):
                metadata = request.urlretrieve(metadata)[0]
            files.append(('metadata', metadata, 'metadata.xml'))
        if thumbnail:
            if _is_http_url(thumbnail):
                thumbnail = request.urlretrieve(thumbnail)[0]
                file_ext = os.path.splitext(thumbnail)[1]
                if not file_ext:
                    file_ext = imghdr.what(thumbnail)
                    if file_ext in ('gif', 'png', 'jpeg'):
                        new_thumbnail = thumbnail + '.' + file_ext
                        os.rename(thumbnail, new_thumbnail)
                        thumbnail = new_thumbnail
            files.append(('thumbnail', thumbnail, os.path.basename(thumbnail)))

        # If owner isn't specified, use the logged in user
        if not owner:
            owner = self.logged_in_user()['username']

        # Setup the item path, including the folder, and post to it
        path = 'content/users/' + owner
        if folder and folder != '/':
            folder_id = self.get_folder_id(owner, folder)
            path += '/' + folder_id

        path += '/addItem'
        resp = self.con.post(path, postdata, files)
        if resp and resp.get('success'):
            return resp['id']

    def publish_item(self, itemid, data=None, text=None, fileType="serviceDefinition", publishParameters=None,
                     outputType=None, overwrite=False, owner=None, folder=None, buildInitialCache=False):
        """
        Publishes a hosted service based on an existing source item.
        Publishers can create feature services as well as tiled map services.
        Feature services can be created using input files of type csv, shapefile, serviceDefinition, featureCollection, and fileGeodatabase.
        CSV files that contain location fields, (ie.address fields or X, Y fields) are spatially enabled during the process of publishing.
        Shapefiles and file geodatabases should be packaged as *.zip files.
        Tiled map services can be created from service definition (*.sd) files, tile packages, and existing feature services.
        Service definitions are authored in ArcGIS for Desktop and contain both the cartographic definition for a map as well as its packaged data together with the definition of the geo-service to be created.
        Use the Analyze operation to generate the default publishing parameters for CSVs.
        See http://resources.arcgis.com/en/help/arcgis-rest-api/index.html#/Publish_Item/02r300000080000000/
        """
        # Postdata is a dictionary object whose keys and values will be sent via an HTTP Post.
        postdata = self._postdata()

        postdata['itemid'] = itemid
        if text is not None:
            postdata['test'] = text

        postdata['fileType'] = fileType

        if publishParameters is not None and isinstance(publishParameters, dict):
            postdata['publishParameters'] = json.dumps(publishParameters)

        if outputType is not None:
            postdata['outputType'] = outputType

        postdata['overwrite'] = overwrite

        postdata['buildInitialCache'] = buildInitialCache

        # Build the files list (tuples)
        files = []
        if data:
            if _is_http_url(data):
                data = request.urlretrieve(data)[0]
            files.append(('file', data, os.path.basename(data)))

        # If owner isn't specified, use the logged in user
        if not owner:
            owner = self.logged_in_user()['username']

        # Setup the item path, including the folder, and post to it
        path = 'content/users/' + owner
        if folder:
            path += '/' + folder
        path += '/publish'
        resp = self.con.post(path, postdata, files)
        if resp:
            return resp['services']

    def create_service(self,
                       name,
                       service_description="",
                       has_static_data=False,
                       max_record_count = 1000,
                       supported_query_formats = "JSON",
                       capabilities = None,
                       description = "",
                       copyright_text = "",
                       wkid=102100,
                       service_type="imageService",
                       create_params=None,
                       owner=None, folder=None, common_params=None):
        """ Creates service.
         #"Create,Delete,Query,Update,Editing",
        :return:
             The item id of the created service item if successful, None if unsuccessful.
        """


        # Postdata is a dictionary object whose keys and values will be sent via an HTTP Post.
        postdata = self._postdata()

        # If owner isn't specified, use the logged in user
        if not owner:
            owner = self.logged_in_user()['username']

        # Setup the item path, including the folder, and post to it
        path = 'content/users/' + owner
        if folder and folder != '/':
            folder_id = self.get_folder_id(owner, folder)
            path += '/' + folder_id
        path += '/createService'


        createParameters = {
            "name" : name,
            "serviceDescription" : service_description,
            "hasStaticData" : has_static_data,
            "maxRecordCount" : max_record_count,
            "supportedQueryFormats" : supported_query_formats,
            "capabilities" :capabilities,
            "description" : description,
            "copyrightText" : copyright_text,
            "spatialReference" : {
                "wkid" : wkid
                },
            "initialExtent" : {
                "xmin" : -20037507.0671618,
                "ymin" : -30240971.9583862,
                "xmax" : 20037507.0671618,
                "ymax" : 18398924.324645,
                "spatialReference" : {
                    "wkid" : 102100,
                    "latestWkid" : 3857
                }
                },
            "allowGeometryUpdates" : True,
            "units" : "esriMeters",
            "xssPreventionInfo" : {
                "xssPreventionEnabled" : True,
                "xssPreventionRule" : "InputOnly",
                "xssInputRule" : "rejectInvalid"
            }
        }

        if create_params is not None:
            postdata['createParameters'] = json.dumps(create_params)
        else:
            postdata['createParameters'] = json.dumps(createParameters)

        postdata['outputType'] = service_type

        # If common_params dictionary provided, add each key/value pair to postdata.
        if common_params is not None:
            for key in common_params:
                if key not in postdata:
                    postdata[key] = common_params[key]

        resp = self.con.post(path, postdata)
        if resp and resp.get('success'):
            return resp['itemId']


    def create_group_from_dict(self, group, thumbnail=None):

        """ Creates a group and returns a group id if successful.

        .. note::
           Use create_group in most cases.  This method is useful for taking a group
           dict returned from another PortalPy call and copying it.

        ============  ======================================
        **Argument**  **Description**
        ------------  --------------------------------------
        group         dict object
        ------------  --------------------------------------
        thumbnail     url to image
        ============  ======================================

        Example

        .. code-block:: python

             create_group({'title': 'Test', 'access':'public'})
        """

        postdata = self._postdata()
        postdata.update(_to_utf8(group))

        # Build the files list (tuples)
        files = []
        if thumbnail:
            if _is_http_url(thumbnail):
                thumbnail = request.urlretrieve(thumbnail)[0]
                file_ext = os.path.splitext(thumbnail)[1]
                if not file_ext:
                    file_ext = imghdr.what(thumbnail)
                    if file_ext in ('gif', 'png', 'jpeg'):
                        new_thumbnail = thumbnail + '.' + file_ext
                        os.rename(thumbnail, new_thumbnail)
                        thumbnail = new_thumbnail
            files.append(('thumbnail', thumbnail, os.path.basename(thumbnail)))

        # Send the POST request, and return the id from the response
        resp = self.con.post('community/createGroup', postdata, files)
        if resp and resp.get('success'):
            return resp['group']

    def create_group(self, title, tags, description=None,
                     snippet=None, access='public', thumbnail=None,
                     is_invitation_only=False, sort_field='avgRating',
                     sort_order='desc', is_view_only=False, ):
        """ Creates a group and returns a group id if successful.

        ================  ========================================================
        **Argument**      **Description**
        ----------------  --------------------------------------------------------
        title             required string, name of the group
        ----------------  --------------------------------------------------------
        tags              required string, comma-delimited list of tags
        ----------------  --------------------------------------------------------
        description       optional string, describes group in detail
        ----------------  --------------------------------------------------------
        snippet           optional string, <250 characters summarizes group
        ----------------  --------------------------------------------------------
        access            optional string, can be private, public, or org
        ----------------  --------------------------------------------------------
        thumbnail         optional string, URL to group image
        ----------------  --------------------------------------------------------
        isInvitationOnly  optional boolean, defines whether users can join by request.
        ----------------  --------------------------------------------------------
        sort_field        optional string, specifies how shared items with the group are sorted.
        ----------------  --------------------------------------------------------
        sort_order        optional string, asc or desc for ascending or descending.
        ----------------  --------------------------------------------------------
        is_view_only      optional boolean, defines whether the group is searchable
        ================  ========================================================

        :return:
            a dict containing group properties
        """

        return self.create_group_from_dict({'title' : title, 'tags' : tags,
                                            'snippet' : snippet, 'access' : access,
                                            'sortField' : sort_field, 'sortOrder' : sort_order,
                                            'isViewOnly' : is_view_only,
                                            'isinvitationOnly' : is_invitation_only}, thumbnail)





    def delete_group(self, group_id):
        """ Deletes a group.

        ================  ========================================================
        **Argument**      **Description**
        ----------------  --------------------------------------------------------
        group_id          string containing the id for the group to be deleted.
        ================  ========================================================

        Returns
            a boolean indicating whether it was successful.

        """
        resp = self.con.post('community/groups/' + group_id + '/delete',
                             self._postdata())
        if resp:
            return resp.get('success')


    def delete_item(self, item_id, owner, folder=None):
        """ Deletes an item.

        ================  ========================================================
        **Argument**      **Description**
        ----------------  --------------------------------------------------------
        item_id           required string, unique identifier for the item
        ----------------  --------------------------------------------------------
        owner             required string, owner of the item currently
        ----------------  --------------------------------------------------------
        folder            optional string, folder containing the item.  Defaults to the root folder.
        ================  ========================================================

        :return:
            a boolean, indicating success

        """
        path = 'content/users/' + owner
        if folder :
            path += '/' + folder
        path += '/items/' + item_id + '/delete'
        #print(path)
        resp = self.con.post(path, self._postdata())

        if resp:
            return resp.get('success')

    def protect_item(self, item_id, owner, folder=None, enable=True):
        """ Enable or disable delete protection on the item

        ================  ========================================================
        **Argument**      **Description**
        ----------------  --------------------------------------------------------
        item_id           required string, unique identifier for the item
        ----------------  --------------------------------------------------------
        owner             required string, owner of the item currently
        ----------------  --------------------------------------------------------
        folder            optional string, folder containing the item.  Defaults to the root folder.
        ----------------  --------------------------------------------------------
        enable            optional boolean, True to enable delete protection, False to
                          to disable it
        ================  ========================================================

        :return:
            dict with key "success" containing boolean whether process completed or not


        """
        path = 'content/users/' + owner
        if folder :
            path += '/' + folder
        if enable == True:
            path += '/items/' + item_id + '/protect'
        else:
            path += '/items/' + item_id + '/unprotect'
        postdata = self._postdata()
        resp = self.con.post(path, postdata)
        if resp:
            return resp

    def share_item_as_group_admin(self, item_id, groups="", allow_members_to_edit=False):
        """ Shares public item with the specified list of groups belonging to caller

        ================  ========================================================
        **Argument**      **Description**
        ----------------  --------------------------------------------------------
        item_id           required string, unique identifier for the item
        ----------------  --------------------------------------------------------
        groups            optional string,
                          comma-separated list of group IDs with which the item will be shared.
        ----------------  --------------------------------------------------------
        allow_members_to_edit  optional boolean to allow item to be shared with groups that allow shared update
        ================  ========================================================

        :return:
            dict with key "notSharedWith" containing array of groups with which the item could not be shared.



        """
        path = 'content/items/' + item_id + '/share'
        postdata = self._postdata()
        postdata['groups'] = groups
        resp = self.con.post(path, postdata)
        if allow_members_to_edit:
            postdata['confirmItemControl'] = True
        if resp:
            return resp

    def unshare_item_as_group_admin(self, item_id, groups=""):
        """ Stops sharing public item with the specified list of groups belonging to caller

        ================  ========================================================
        **Argument**      **Description**
        ----------------  --------------------------------------------------------
        item_id           required string, unique identifier for the item
        ----------------  --------------------------------------------------------
        groups            optional string,
                          comma-separated list of group IDs with which the item will be unshared.
        ================  ========================================================

        :return:
            dict with key "notUnsharedFrom" containing array of groups from which the item could not be unshared.



        """
        path = 'content/items/' + item_id + '/unshare'
        postdata = self._postdata()
        postdata['groups'] = groups
        resp = self.con.post(path, postdata)
        if resp:
            return resp

    def share_item(self, item_id, owner, folder=None, everyone=False, org=False, groups="", allow_members_to_edit=False):
        """ Shares an item with the specified list of groups

        ================  ========================================================
        **Argument**      **Description**
        ----------------  --------------------------------------------------------
        item_id           required string, unique identifier for the item
        ----------------  --------------------------------------------------------
        owner             required string, owner of the item currently
        ----------------  --------------------------------------------------------
        folder            optional string, folder containing the item.  Defaults to the root folder.
        ----------------  --------------------------------------------------------
        everyone          optional boolean, share with everyone
        ----------------  --------------------------------------------------------
        org               optional boolean, share with the organization
        ----------------  --------------------------------------------------------
        groups            optional string,
                          comma-separated list of group IDs with which the item will be shared.
        ----------------  --------------------------------------------------------
        allow_members_to_edit  optional boolean to allow item to be shared with groups that allow shared update
        ================  ========================================================

        :return:
            dict with key "notSharedWith" containing array of groups with which the item could not be shared.



        """
        path = 'content/users/' + owner
        if folder :
            path += '/' + folder
        path += '/items/' + item_id + '/share'
        #print(path)
        postdata = self._postdata()
        postdata['everyone'] = everyone
        postdata['org'] = org
        postdata['groups'] = groups
        if allow_members_to_edit:
            postdata['confirmItemControl'] = True
        resp = self.con.post(path, postdata)

        if resp:
            return resp

    def unshare_item(self, item_id, owner, folder=None, groups=""):
        """ Stops sharing the item with the specified list of groups

        ================  ========================================================
        **Argument**      **Description**
        ----------------  --------------------------------------------------------
        item_id           required string, unique identifier for the item
        ----------------  --------------------------------------------------------
        owner             required string, owner of the item currently
        ----------------  --------------------------------------------------------
        folder            optional string, folder containing the item.  Defaults to the root folder.
        ----------------  --------------------------------------------------------
        groups            optional string,
                          comma-separated list of group IDs with which the item will be unshared.
        ================  ========================================================

        :return:
            dict with key "notUnsharedFrom" containing array of groups from which the item could not be unshared.



        """
        path = 'content/users/' + owner
        if folder :
            path += '/' + folder
        path += '/items/' + item_id + '/unshare'

        postdata = self._postdata()
        postdata['groups'] = groups
        resp = self.con.post(path, postdata)

        if resp:
            return resp

    def delete_user(self, username, reassign_to=None):
        """ Deletes a user from the portal, optionally deleting or reassigning groups and items.

        .. note::
            You can not delete a user in Portal if that user owns groups or items.  If you
            specify someone in the reassign_to argument then items and groups will be
            transferred to that user.  If that argument is not set then the method
            will fail if the user has items or groups that need to be reassigned.


        ================  ========================================================
        **Argument**      **Description**
        ----------------  --------------------------------------------------------
        username          required string, the name of the user
        ----------------  --------------------------------------------------------
        reassign_to       optional string, new owner of items and groups
        ================  ========================================================

        :return:
            a boolean indicating whether the operation succeeded or failed.

        """


        if reassign_to :
            self.reassign_user(username, reassign_to)
        resp = self.con.post('community/users/' + username + '/delete',self._postdata())
        if resp:
            return resp.get('success')
        else:
            return False

    def generate_token(self, username, password, expiration=60):
        """ Generates and returns a new token, but doesn't re-login.

        .. note::
            This method is not needed when using the Portal class
            to make calls into Portal.  It's provided for the benefit
            of making calls into Portal outside of the Portal class.

            Portal uses a token-based authentication mechanism where
            a user provides their credentials and a short-term token
            is used for calls.  Most calls made to the Portal REST API
            require a token and this can be appended to those requests.

        ================  ========================================================
        **Argument**      **Description**
        ----------------  --------------------------------------------------------
        username          required string, name of the user
        ----------------  --------------------------------------------------------
        password          required password, name of the user
        ----------------  --------------------------------------------------------
        expiration        optional integer, number of minutes until the token expires
        ================  ========================================================

        :return:
            a string with the token

        """

        return self.con.generate_token(username, password, expiration)


    def get_group(self, group_id):
        """ Returns group information for the specified group group_id.

        Arguments
            group_id : required string, indicating group.

        :return:
            a dictionary object with the group's information.  The keys in
            the dictionary object will often include:

            ================  ========================================================
            **Key**           **Value**
            ----------------  --------------------------------------------------------
            title:            the name of the group
            ----------------  --------------------------------------------------------
            isInvitationOnly  if set to true, users can't apply to join the group.
            ----------------  --------------------------------------------------------
            owner:            the owner username of the group
            ----------------  --------------------------------------------------------
            description:      explains the group
            ----------------  --------------------------------------------------------
            snippet:          a short summary of the group
            ----------------  --------------------------------------------------------
            tags:             user-defined tags that describe the group
            ----------------  --------------------------------------------------------
            phone:            contact information for group.
            ----------------  --------------------------------------------------------
            thumbnail:        File name relative to http://<community-url>/groups/<groupId>/info
            ----------------  --------------------------------------------------------
            created:          When group created, ms since 1 Jan 1970
            ----------------  --------------------------------------------------------
            modified:         When group last modified. ms since 1 Jan 1970
            ----------------  --------------------------------------------------------
            access:           Can be private, org, or public.
            ----------------  --------------------------------------------------------
            userMembership:   A dict with keys username and memberType.
            ----------------  --------------------------------------------------------
            memberType:       provides the calling user's access (owner, admin, member, none).
            ================  ========================================================

        """
        return self.con.post('community/groups/' + group_id, self._postdata())



    def get_group_thumbnail(self, group_id):
        """ Returns the bytes that make up the thumbnail for the specified group group_id.

        Arguments
            group_id:     required string, specifies the group's thumbnail

        Returns
            bytes that representt he image.

        Example

        .. code-block:: python

            response = portal.get_group_thumbnail("67e1761068b7453693a0c68c92a62e2e")
            f = open(filename, 'wb')
            f.write(response)

        """
        thumbnail_file = self.get_group(group_id).get('thumbnail')
        if thumbnail_file:
            thumbnail_url_path = 'community/groups/' + group_id + '/info/' + thumbnail_file
            if thumbnail_url_path:
                return self.con.get(thumbnail_url_path, try_json=False, force_bytes=True)


    def get_group_members(self, group_id):
        """ Returns members of the specified group.

        Arguments
            group_id:    required string, specifies the group

        Returns
            a dictionary with keys: owner, admins, and users.

            ================  ========================================================
            **Key**           **Value**
            ----------------  --------------------------------------------------------
            owner             string value, the group's owner
            ----------------  --------------------------------------------------------
            admins            list of strings, typically this is the same as the owner.
            ----------------  --------------------------------------------------------
            users             list of strings, the members of the group
            ================  ========================================================

        Example (to print users in a group)

        .. code-block:: python

            response = portal.get_group_members("67e1761068b7453693a0c68c92a62e2e")
            for user in response['users'] :
                print user

        """

        return self.con.post('community/groups/' + group_id + '/users',
                             self._postdata())

    def get_org_roles(self, max_roles=1000):
        """ Returns all roles within the portal organization.

        Arguments
            max_roles : optional int, the maximum number of users to return.

        :return:
            a list of dicts.  Each dict has the following keys:
        """

        # Execute the search and get back the results
        count = 0
        resp = self._roles_page(1, min(max_roles, 100))
        resp_roles = resp.get('roles')
        results = resp_roles
        count += int(resp['num'])
        nextstart = int(resp['nextStart'])
        while count < max_roles and nextstart > 0:
            resp = self._roles_page(nextstart, min(max_roles - count, 100))
            resp_roles = resp.get('roles')
            results.extend(resp_roles)
            count += int(resp['num'])
            nextstart = int(resp['nextStart'])

        return results

    def get_org_users(self, max_users=1000):
        """ Returns all users within the portal organization.

        Arguments
            max_users : optional int, the maximum number of users to return.

        :return:
            a list of dicts.  Each dict has the following keys:

            ================  ========================================================
            **Key**           **Value**
            ----------------  --------------------------------------------------------
            username :        string
            ----------------  --------------------------------------------------------
            storageUsage:     int
            ----------------  --------------------------------------------------------
            storageQuota:     int
            ----------------  --------------------------------------------------------
            description:      string
            ----------------  --------------------------------------------------------
            tags:             list of strings
            ----------------  --------------------------------------------------------
            region:            string
            ----------------  --------------------------------------------------------
            created:          int, when account created, ms since 1 Jan 1970
            ----------------  --------------------------------------------------------
            modified:         int, when account last modified, ms since 1 Jan 1970
            ----------------  --------------------------------------------------------
            email:            string
            ----------------  --------------------------------------------------------
            culture:          string
            ----------------  --------------------------------------------------------
            orgId:            string
            ----------------  --------------------------------------------------------
            preferredView:    string
            ----------------  --------------------------------------------------------
            groups:           list of strings
            ----------------  --------------------------------------------------------
            role:             string (org_user, org_publisher, org_admin)
            ----------------  --------------------------------------------------------
            fullName:         string
            ----------------  --------------------------------------------------------
            thumbnail:        string
            ----------------  --------------------------------------------------------
            idpUsername:      string
            ================  ========================================================

        Example (print all usernames in portal):

        .. code-block:: python

           resp = portalAdmin.get_org_users()
           for user in resp:
               print user['username']

        """

        # Execute the search and get back the results
        count = 0
        resp = self._org_users_page(1, min(max_users, 100))
        resp_users = resp.get('users')
        results = resp_users
        count += int(resp['num'])
        nextstart = int(resp['nextStart'])
        while count < max_users and nextstart > 0:
            resp = self._org_users_page(nextstart, min(max_users - count, 100))
            resp_users = resp.get('users')
            results.extend(resp_users)
            count += int(resp['num'])
            nextstart = int(resp['nextStart'])

        return results



    def get_properties(self, force=False):
        """ Returns the portal properties (using cache unless force=True). """

        # If we've never retrieved the properties before, or the caller is
        # forcing a check of the server, then check the server
        if not self._properties or force:
            path = 'accounts/self' if self._is_pre_162 else 'portals/self'
            resp = self.con.post(path, self._postdata(), ssl=True)
            if resp:
                self._properties = resp
                self.con.all_ssl = self.is_all_ssl

        # Return a defensive copy
        return copy.deepcopy(self._properties)

    def get_user(self, username):
        """ Returns the user information for the specified username.

        Arguments
            username        required string, the username whose information you want.

        :return:
            None if the user is not found and returns a dictionary object if the user is found
            the dictionary has the following keys:

            ================  ========================================================
            **Key**           **Value**
            ----------------  --------------------------------------------------------
            access            string
            ----------------  --------------------------------------------------------
            created           time (int)
            ----------------  --------------------------------------------------------
            culture           string, two-letter language code ('en')
            ----------------  --------------------------------------------------------
            description       string
            ----------------  --------------------------------------------------------
            email             string
            ----------------  --------------------------------------------------------
            fullName          string
            ----------------  --------------------------------------------------------
            idpUsername       string, name of the user in the enterprise system
            ----------------  --------------------------------------------------------
            groups            list of dictionaries.  For dictionary keys, see get_group doc.
            ----------------  --------------------------------------------------------
            modified          time (int)
            ----------------  --------------------------------------------------------
            orgId             string, the organization id
            ----------------  --------------------------------------------------------
            preferredView     string, value is either Web, GIS, or null
            ----------------  --------------------------------------------------------
            region            string, None or two letter country code
            ----------------  --------------------------------------------------------
            role              string, value is either org_user, org_publisher, org_admin
            ----------------  --------------------------------------------------------
            storageUsage      int
            ----------------  --------------------------------------------------------
            storageQuota      int
            ----------------  --------------------------------------------------------
            tags              list of strings
            ----------------  --------------------------------------------------------
            thumbnail         string, name of file
            ----------------  --------------------------------------------------------
            username          string, name of user
            ================  ========================================================
        """
        return self.con.post('community/users/' + username, self._postdata())


    def get_item(self, itemid):
        """ Returns the item information for the specified item.

        Arguments
            itemid            required string, the item-id whose information you want.

        :return:
            None if the item is not found and returns a dictionary object if the item is found
            the dictionary has the following keys:

            ================  ========================================================
            **Key**           **Value**
            ----------------  --------------------------------------------------------
            id                string, the unique ID for this item.
            ----------------  --------------------------------------------------------
            owner             string, the username of the user who owns this item.
            ----------------  --------------------------------------------------------
            created           time (int) the date the item was created. Shown in UNIX time in milliseconds.
            ----------------  --------------------------------------------------------
            modified          time (int) the date the item was last modified. Shown in UNIX time in milliseconds.
            ----------------  --------------------------------------------------------
            name              string, the file name of the item for file types. Read-only.
            ----------------  --------------------------------------------------------
            title             string, the title of the item. This is the name that's displayed to users
            ----------------  --------------------------------------------------------
            url               string, the URL for the resource represented by the item. Applies only to items that represent web-accessible resources such as map services.
            ----------------  --------------------------------------------------------
            type              string, the GIS content type of this item. Example types include Web Map, Map Service, Shapefile, and Web Mapping Application.
            ----------------  --------------------------------------------------------
            typeKeywords      string, a set of keywords that further describes the type of this item. Each item is tagged with a set of type keywords that are derived based on its primary type.
            ----------------  --------------------------------------------------------
            description       string, item description.
            ----------------  --------------------------------------------------------
            tags              string, user defined tags that describe the item.
            ----------------  --------------------------------------------------------
            snippet           string, a short summary description of the item.
            ----------------  --------------------------------------------------------
            thumbnail         string, the URL to the thumbnail used for the item.
            ----------------  --------------------------------------------------------
            extent            string, the bounding rectangle of the item. Should always be in WGS84.
            ----------------  --------------------------------------------------------
            spatialReference  string, the coordinate system of the item.
            ----------------  --------------------------------------------------------
            accessInformation string, information on the source of the item.
            ----------------  --------------------------------------------------------
            licenseInfo       string, any license information or restrictions.
            ----------------  --------------------------------------------------------
            culture           string, the item locale information (language and country).
            ----------------  --------------------------------------------------------
            access            string, ndicates the level of access to this item: private, shared, org, or public.
            ----------------  --------------------------------------------------------
            size              string, the size of the item.
            ----------------  --------------------------------------------------------
            commentsEnabled   indicates if comments are allowed on the item.
            ----------------  --------------------------------------------------------
            numComments       number of comments on the item.
            ----------------  --------------------------------------------------------
            numRatings        number of ratings on the item.
            ----------------  --------------------------------------------------------
            avgRating         average rating. Uses a weighted average called "Bayesian average."
            ----------------  --------------------------------------------------------
            numViews          number of views of the item.
            ================  ========================================================
        """
        return self.con.post('content/items/' + itemid, self._postdata())

    def get_item_data(self, itemid, try_json=True):
        #print('content/items/' + itemid + '/data')
        return self.con.get('content/items/' + itemid + '/data', try_json=try_json)
        #return self.con.post('content/items/' + itemid + '/data', self._postdata(), use_ordered_dict=try_json)
        #return self.con.post('content/items/' + itemid + '/data', self._postdata(), use_ordered_dict=True)

    def usage(self, startTime, endTime, period, vars, etype, stype, groupby, appId=None):
        postdata = self._postdata()
        postdata['startTime'] = startTime * 1000
        postdata['endTime'] = endTime * 1000
        postdata['period'] = period
        postdata['vars'] = vars
        postdata['etype'] = etype
        postdata['stype'] = stype
        postdata['groupby'] = groupby
        if appId is not None:
            postdata['appId'] = appId


        return self.con.post('portals/self/usage', postdata, use_ordered_dict=True)

        # https://dev04875.esri.com/arcgis/sharing/rest/portals/0123456789ABCDEF/usage?f=json&startTime=1436984519000&endTime=1439576519000&period=1d&vars=num&etype=geocodecnt&stype=geocode&groupby=username%2Cstype%2Cetype

    def get_item_dependencies(self, itemid):
        return self.con.post('content/items/' + itemid + '/dependencies', self._postdata())

    def get_item_dependents_to(self, itemid):
        return self.con.post('content/items/' + itemid + '/dependencies/listDependentsTo', self._postdata())


    def invite_group_users(self, user_names, group_id,
                           role='group_member', expiration=10080):
        """ Invites users to a group.

        .. note::
            A user who is invited to a group will see a list of invitations
            in the "Groups" tab of portal listing invitations.  The user
            can either accept or reject the invitation.

        Requires
            The user executing the command must be group owner

        ================  ========================================================
        **Argument**      **Description**
        ----------------  --------------------------------------------------------
        user_names:       a required string list of users to invite
        ----------------  --------------------------------------------------------
        group_id :        required string, specifies the group you are inviting users to.
        ----------------  --------------------------------------------------------
        role:             an optional string, either group_member or group_admin
        ----------------  --------------------------------------------------------
        expiration:       an optional int, specifies how long the invitation is valid for in minutes.
        ================  ========================================================

        :return:
            a boolean that indicates whether the call succeeded.

        """

        user_names = _unpack(user_names, 'username')

        # Send out the invitations
        postdata = self._postdata()
        postdata['users'] = ','.join(user_names)
        postdata['role'] = role
        postdata['expiration'] = expiration
        resp = self.con.post('community/groups/' + group_id + '/invite',
                             postdata)

        if resp:
            return resp.get('success')

    @property
    def is_logged_in(self):
        """ Returns true if logged into the portal. """
        return self.con.is_logged_in
    @property
    def is_all_ssl(self):
        """ Returns true if this portal requires SSL. """

        # If properties aren't set yet, return true (assume SSL until the
        # properties tell us otherwise)
        if not self._properties:
            return True

        # If access property doesnt exist, will correctly return false
        return self._properties.get('allSSL')
    @property
    def is_multitenant(self):
        """ Returns true if this portal is multitenant. """
        return self._properties['portalMode'] == 'multitenant'
    @property
    def is_arcgisonline(self):
        """ Returns true if this portal is ArcGIS Online. """
        return self._properties['portalName'] == 'ArcGIS Online' \
               and self.is_multitenant
    @property
    def is_subscription(self):
        """ Returns true if this portal is an ArcGIS Online subscription. """
        return bool(self._properties.get('urlKey'))
    @property
    def is_org(self):
        """ Returns true if this portal is an organization. """
        return bool(self._properties.get('id'))


    def leave_group(self, group_id):
        """ Removes the logged in user from the specified group.

        Requires:
            User must be logged in.

        Arguments:
             group_id:   required string, specifies the group id

        :return:
             a boolean indicating whether the operation was successful.
        """
        resp = self.con.post('community/groups/' + group_id + '/leave',
                             self._postdata())
        if resp:
            return resp.get('success')

    def login(self, username, password, expiration=60):
        """ Logs into the portal using username/password.

        .. note::
             You can log into a portal when you construct a portal
             object or you can login later.  This function is
             for the situation when you need to log in later.

        ================  ========================================================
        **Argument**      **Description**
        ----------------  --------------------------------------------------------
        username          required string
        ----------------  --------------------------------------------------------
        password          required string
        ----------------  --------------------------------------------------------
        expiration        optional int, how long the token generated should last.
        ================  ========================================================

        :return:
            a string, the token

        """

        newtoken = self.con.login(username, password, expiration)
        return newtoken

    def logout(self):
        """ Logs out of the portal.

        .. note::
             The portal will forget any existing tokens it was using, all
             subsequent portal calls will be anonymous until another login
             call occurs.

        :return:
             No return value.

        """

        self.con.logout()


    def logged_in_user(self):
        """ Returns information about the logged in user.

        :return:
            a dict with the following keys:

            ================  ========================================================
            **Key**           **Value**
            ----------------  --------------------------------------------------------
            username          string
            ----------------  --------------------------------------------------------
            storageUsage      int
            ----------------  --------------------------------------------------------
            description       string
            ----------------  --------------------------------------------------------
            tags              comma-separated string
            ----------------  --------------------------------------------------------
            created           int, when group created (ms since 1 Jan 1970)
            ----------------  --------------------------------------------------------
            modified          int, when group last modified (ms since 1 Jan 1970)
            ----------------  --------------------------------------------------------
            fullName          string
            ----------------  --------------------------------------------------------
            email             string
            ----------------  --------------------------------------------------------
            idpUsername       string, name of the user in their identity provider
            ================  ========================================================

         """
        try :
            username = self._properties['user']['username']
            return self.get_user(username)
        except:
            return None


    def reassign_user(self, username, target_username):
        """ Reassigns all of a user's items and groups to another user.

        Items are transferred to the target user into a folder named
        <user>_<folder> where user corresponds to the user whose items were
        moved and folder corresponds to the folder that was moved.

        .. note::
            This method must be executed as an administrator.  This method also
            can not be undone.  The changes are immediately made and permanent.

        ================  ========================================================
        **Argument**      **Description**
        ----------------  --------------------------------------------------------
        username          required string, user who will have items/groups transferred
        ----------------  --------------------------------------------------------
        target_username   required string, user who will own items/groups after this.
        ================  ========================================================

        :return:
            a boolean indicating success

        """

        postdata = self._postdata()
        postdata['targetUsername'] = target_username
        resp = self.con.post('community/users/' + username + '/reassign', postdata)
        if resp:
            return resp.get('success')



    def reassign_group(self, group_id, target_owner):
        """ Reassigns a group to another owner.



        ================  ========================================================
        **Argument**      **Description**
        ----------------  --------------------------------------------------------
        group_id          required string, unique identifier for the group
        ----------------  --------------------------------------------------------
        target_owner      required string, username of new group owner
        ================  ========================================================

        :return:
            a boolean, indicating success

        """
        postdata = self._postdata()
        postdata['targetUsername'] = target_owner
        resp = self.con.post('community/groups/' + group_id + '/reassign', postdata)
        if resp:
            return resp.get('success')


    def reassign_item(self, item_id, current_owner, target_owner, current_folder=None, target_folder=None):
        """ Allows the administrator to reassign a single item from one user to another.

        .. note::
             	If you wish to move all of a user's items (and groups) to another user then use the
                reassign_user method.  This method only moves one item at a time.

        ================  ========================================================
        **Argument**      **Description**
        ----------------  --------------------------------------------------------
        item_id           required string, unique identifier for the item
        ----------------  --------------------------------------------------------
        current_owner     required string, owner of the item currently
        ----------------  --------------------------------------------------------
        current_folder    optional string, folder containing the item.  Defaults to the root folder.
        ----------------  --------------------------------------------------------
        target_owner      required string, desired owner of the item
        ----------------  --------------------------------------------------------
        target_folder     optional string, folder to move the item to.
        ================  ========================================================

        :return:
            a boolean, indicating success

        """
        path = 'content/users/' + current_owner
        if current_folder :
            path += '/' + current_folder
        path += '/items/' + item_id + '/reassign'

        postdata = self._postdata()
        postdata['targetUsername'] = target_owner
        postdata['targetFolderName'] = target_folder if target_folder else '/'
        resp = self.con.post(path, postdata)
        if resp:
            return resp.get('success')

    def reset_user(self, username, password, new_password=None,
                   new_security_question=None, new_security_answer=None):
        """ Resets a user's password, security question, and/or security answer.

        .. note::
            This function does not apply to those using enterprise accounts
            that come from an enterprise such as ActiveDirectory, LDAP, or SAML.
            It only has an effect on built-in users.

            If a new security question is specified, a new security answer should
            be provided.

        =====================  ========================================================
        **Argument**           **Description**
        ---------------------   --------------------------------------------------------
        username               required string, account being reset
        ---------------------   --------------------------------------------------------
        password               required string, current password
        ---------------------   --------------------------------------------------------
        new_password           optional string, new password if resetting password
        ---------------------   --------------------------------------------------------
        new_security_question  optional int, new security question if desired
        ---------------------   --------------------------------------------------------
        new_security_answer    optional string, new security question answer if desired
        =====================  ========================================================

        :return:
            a boolean, indicating success

        """
        postdata = self._postdata()
        postdata['password'] = password
        if new_password:
            postdata['newPassword'] = new_password
        if new_security_question:
            postdata['newSecurityQuestionIdx'] = new_security_question
        if new_security_answer:
            postdata['newSecurityAnswer'] = new_security_answer
        resp = self.con.post('community/users/' + username + '/reset',
                             postdata, ssl=True)
        if resp:
            return resp.get('success')



    def remove_group_users(self, user_names, group_id):
        """ Remove users from a group.

        ================  ========================================================
        **Argument**      **Description**
        ----------------  --------------------------------------------------------
        user_names        required string, comma-separated list of users
        ----------------  --------------------------------------------------------
        group_id          required string, the id for a group.
        ================  ========================================================

        :return:
            a dictionary with a key notRemoved that is a list of users not removed.

        """

        user_names = _unpack(user_names, 'username')

        # Remove the users from the group
        postdata = self._postdata()
        postdata['users'] = ','.join(user_names)
        resp = self.con.post('community/groups/' + group_id + '/removeUsers',
                             postdata)
        return resp

    def user_folders(self, owner):
        resp = self._contents_page(owner, None, 1, 10)
        results = resp.get('folders')
        return results

    def user_items(self, owner, folder, max_results=100):
        count = 0
        resp = self._contents_page(owner, folder, 1, min(max_results, 100))
        results = resp.get('items')
        count += int(resp['num'])
        nextstart = int(resp['nextStart'])
        while count < max_results and nextstart > 0:
            resp = self._contents_page(owner, folder, nextstart, min(max_results - count, 100))
            results.extend(resp['items'])
            count += int(resp['num'])
            nextstart = int(resp['nextStart'])
        return results

    def search(self, q, bbox=None, sort_field='title', sort_order='asc',
               max_results=1000, outside_org=False):


        if not outside_org:
            accountid = self._properties.get('id')
            if accountid and q:
                q += ' accountid:' + accountid
            elif accountid:
                q = 'accountid:' + accountid

        count = 0
        resp = self._search_page(q, bbox, 1, min(max_results, 100), sort_field, sort_order)
        results = resp.get('results')
        count += int(resp['num'])
        nextstart = int(resp['nextStart'])
        while count < max_results and nextstart > 0:
            resp = self._search_page(q, bbox, nextstart, min(max_results - count, 100),
                                     sort_field, sort_order)
            results.extend(resp['results'])
            count += int(resp['num'])
            nextstart = int(resp['nextStart'])

        return results


    def search_groups(self, q, sort_field='title',sort_order='asc',
                      max_groups=1000, outside_org=False):
        """ Searches for portal groups.

        .. note::
            A few things that will be helpful to know.

            1. The query syntax has quite a few features that can't
               be adequately described here.  The query syntax is
               available in ArcGIS help.  A short version of that URL
               is http://bitly.com/1fJ8q31.

            2. Most of the time when searching groups you want to
               search within your organization in ArcGIS Online
               or within your Portal.  As a convenience, the method
               automatically appends your organization id to the query by
               default.  If you don't want the API to append to your query
               set outside_org to True.

        ================  ========================================================
        **Argument**      **Description**
        ----------------  --------------------------------------------------------
        q                 required string, query string.  See notes.
        ----------------  --------------------------------------------------------
        sort_field        optional string, valid values can be title, owner, created
        ----------------  --------------------------------------------------------
        sort_order        optional string, valid values are asc or desc
        ----------------  --------------------------------------------------------
        max_groups        optional int, maximum number of groups returned
        ----------------  --------------------------------------------------------
        outside_org       optional boolean, controls whether to search outside your org
        ================  ========================================================

        :return:
            A list of dictionaries.  Each dictionary has the following keys.

            ================  ========================================================
            **Key**           **Value**
            ----------------  --------------------------------------------------------
            access            string, values=private, org, public
            ----------------  --------------------------------------------------------
            created           int, ms since 1 Jan 1970
            ----------------  --------------------------------------------------------
            description       string
            ----------------  --------------------------------------------------------
            id                string, unique id for group
            ----------------  --------------------------------------------------------
            isInvitationOnly  boolean
            ----------------  --------------------------------------------------------
            isViewOnly        boolean
            ----------------  --------------------------------------------------------
            modified          int, ms since 1 Jan 1970
            ----------------  --------------------------------------------------------
            owner             string, user name of owner
            ----------------  --------------------------------------------------------
            phone             string
            ----------------  --------------------------------------------------------
            snippet           string, short summary of group
            ----------------  --------------------------------------------------------
            sortField         string, how shared items are sorted
            ----------------  --------------------------------------------------------
            sortOrder         string, asc or desc
            ----------------  --------------------------------------------------------
            tags              string list, user supplied tags for searching
            ----------------  --------------------------------------------------------
            thumbnail         string, name of file.  Append to http://<community url>/groups/<group id>/info/
            ----------------  --------------------------------------------------------
            title             string, name of group as shown to users
            ================  ========================================================
        """

        if not outside_org:
            accountid = self._properties.get('id')
            if accountid and q:
                q += ' accountid:' + accountid
            elif accountid:
                q = 'accountid:' + accountid

        # Execute the search and get back the results
        count = 0
        resp = self._groups_page(q, 1, min(max_groups,100), sort_field, sort_order)
        results = resp.get('results')
        count += int(resp['num'])
        nextstart = int(resp['nextStart'])
        while count < max_groups and nextstart > 0:
            resp = self._groups_page(q, nextstart, min(max_groups - count,100),
                                     sort_field, sort_order)
            resp_users = resp.get('results')
            results.extend(resp_users)
            count += int(resp['num'])
            nextstart = int(resp['nextStart'])

        return results



    def search_users(self, q, sort_field='username',
                     sort_order='asc', max_users=1000, outside_org=False):
        """ Searches portal users.

        This gives you a list of users and some basic information
        about those users.  To get more detailed information (such as role), you
        may need to call get_user on each user.

        .. note::
            A few things that will be helpful to know.

            1. The query syntax has quite a few features that can't
               be adequately described here.  The query syntax is
               available in ArcGIS help.  A short version of that URL
               is http://bitly.com/1fJ8q31.

            2. Most of the time when searching groups you want to
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
        q                 required string, query string.  See notes.
        ----------------  --------------------------------------------------------
        sort_field        optional string, valid values can be username or created
        ----------------  --------------------------------------------------------
        sort_order        optional string, valid values are asc or desc
        ----------------  --------------------------------------------------------
        max_users         optional int, maximum number of users returned
        ----------------  --------------------------------------------------------
        outside_org       optional boolean, controls whether to search outside
                          your org
        ================  ========================================================

        :return:
            A a list of dictionary objects with the following keys:

            ================  ========================================================
            **Key**           **Value**
            ----------------  --------------------------------------------------------
            created           time (int), when user created
            ----------------  --------------------------------------------------------
            culture           string, two-letter language code
            ----------------  --------------------------------------------------------
            description       string, user supplied description
            ----------------  --------------------------------------------------------
            fullName          string, name of the user
            ----------------  --------------------------------------------------------
            modified          time (int), when user last modified
            ----------------  --------------------------------------------------------
            region            string, may be None
            ----------------  --------------------------------------------------------
            tags              string list, of user tags
            ----------------  --------------------------------------------------------
            thumbnail         string, name of file
            ----------------  --------------------------------------------------------
            username          string, name of the user
            ================  ========================================================
        """

        if not outside_org:
            accountid = self._properties.get('id')
            if accountid and q:
                q += ' accountid:' + accountid
            elif accountid:
                q = 'accountid:' + accountid

        # Execute the search and get back the results
        count = 0
        resp = self._users_page(q, 1, min(max_users, 100), sort_field, sort_order)
        results = resp.get('results')
        count += int(resp['num'])
        nextstart = int(resp['nextStart'])
        while count < max_users and nextstart > 0:
            resp = self._users_page(q, nextstart, min(max_users - count, 100),
                                    sort_field, sort_order)
            resp_users = resp.get('results')
            results.extend(resp_users)
            count += int(resp['num'])
            nextstart = int(resp['nextStart'])

        return results



    # Used to signup a new user to an on-premises portal.
    def signup(self, username, password, fullname, email):
        """ Signs up users to an instance of Portal for ArcGIS.

        .. note::
            This method only applies to Portal and not ArcGIS
            Online.  This method can be called anonymously, but
            keep in mind that self-signup can also be disabled
            in a Portal.  It also only creates built-in
            accounts, it does not work with enterprise
            accounts coming from ActiveDirectory or your
            LDAP.

            There is another method called createUser that
            requires administrator access that can always
            be used against 10.2.1 portals or later that
            can create users whether they are builtin or
            enterprise accounts.

        ================  ========================================================
        **Argument**      **Description**
        ----------------  --------------------------------------------------------
        username          required string, must be unique in the Portal, >4 characters
        ----------------  --------------------------------------------------------
        password          required string, must be >= 8 characters.
        ----------------  --------------------------------------------------------
        fullname          required string, name of the user
        ----------------  --------------------------------------------------------
        email             required string, must be an email address
        ================  ========================================================

        :return:
            a boolean indicating success

        """
        if self.is_arcgisonline:
            raise ValueError('Signup is not supported on ArcGIS Online')

        postdata = self._postdata()
        postdata['username'] = username
        postdata['password'] = password
        postdata['fullname'] = fullname
        postdata['email'] = email
        resp = self.con.post('community/signUp', postdata, ssl=True)
        if resp:
            return resp.get('success')

        # TODO: Also check https://portalpy.esri.com/arcgis/portaladmin/security/users/createUser

    def update_user(self, username, access=None, preferred_view=None,
                    description=None, tags=None, thumbnail=None,
                    fullname=None, email=None, culture=None,
                    region=None):
        """ Updates a user's properties.

        .. note::
            Only pass in arguments for properties you want to update.
            All other properties will be left as they are.  If you
            want to update description, then only provide
            the description argument.

        ================  ========================================================
        **Argument**      **Description**
        ----------------  --------------------------------------------------------
        username          required string, name of the user to be updated.
        ----------------  --------------------------------------------------------
        access            optional string, values: private, org, public
        ----------------  --------------------------------------------------------
        preferred_view    optional string, values: Web, GIS, null
        ----------------  --------------------------------------------------------
        description       optional string, a description of the user.
        ----------------  --------------------------------------------------------
        tags              optional string, comma-separated tags for searching
        ----------------  --------------------------------------------------------
        thumbnail         optional string, path or url to a file.  can be PNG, GIF,
                                  JPEG, max size 1 MB
        ----------------  --------------------------------------------------------
        fullname          optional string, name of the user, only for built-in users
        ----------------  --------------------------------------------------------
        email             optional string, email address, only for built-in users
        ----------------  --------------------------------------------------------
        culture           optional string, two-letter language code, fr for example
        ----------------  --------------------------------------------------------
        region            optional string, two-letter country code, FR for example
        ================  ========================================================

        :return:
            a boolean indicating success

        """
        properties = dict()
        postdata = self._postdata()
        if access:
            properties['access'] = access
        if preferred_view:
            properties['preferredView'] = preferred_view
        if description:
            properties['description'] = description
        if tags:
            properties['tags'] = tags
        if fullname:
            properties['fullname'] = fullname
        if email:
            properties['email'] = email
        if culture:
            properties['culture'] = culture
        if region:
            properties['region'] = region

        files = []
        if thumbnail:
            if _is_http_url(thumbnail):
                thumbnail = request.urlretrieve(thumbnail)[0]
                file_ext = os.path.splitext(thumbnail)[1]
                if not file_ext:
                    file_ext = imghdr.what(thumbnail)
                    if file_ext in ('gif', 'png', 'jpeg'):
                        new_thumbnail = thumbnail + '.' + file_ext
                        os.rename(thumbnail, new_thumbnail)
                        thumbnail = new_thumbnail
            files.append(('thumbnail', thumbnail, os.path.basename(thumbnail)))
        postdata.update(properties)


        # Send the POST request, and return the id from the response
        resp = self.con.post('community/users/' + username + '/update', postdata, files, ssl=True)


        if resp:
            return resp.get('success')



    def update_user_role(self, username, role):
        """ Updates a user's role.

        .. note::
            There are three types of roles in Portal - user, publisher, and administrator.
            A user can share items, create maps, create groups, etc.  A publisher can
            do everything a user can do and create hosted services.  An administrator can
            do everything that is possible in Portal.

        ================  ========================================================
        **Argument**      **Description**
        ----------------  --------------------------------------------------------
        username          required string, the name of the user whose role will change
        ----------------  --------------------------------------------------------
        role              required string, one of these values org_user, org_publisher, org_admin
        ================  ========================================================

        :return:
            a boolean, that indicates success

        """
        postdata = self._postdata()
        postdata.update({'user': username, 'role': role})
        resp = self.con.post('portals/self/updateuserrole', postdata, ssl=True)
        if resp:
            return resp.get('success')


    def update_group(self, group_id, title=None, tags=None, description=None,
                     snippet=None, access=None, is_invitation_only=None,
                     sort_field=None, sort_order=None, is_view_only=None,
                     thumbnail=None):
        """ Updates a group.

        .. note::
            Only provide the values for the arguments you wish to update.

        ==================  ========================================================
        **Argument**        **Description**
        ------------------  --------------------------------------------------------
        group_id              required string, the group to modify
        ------------------  --------------------------------------------------------
        title                 optional string, name of the group
        ------------------  --------------------------------------------------------
        tags                  optional string, comma-delimited list of tags
        ------------------  --------------------------------------------------------
        description           optional string, describes group in detail
        ------------------  --------------------------------------------------------
        snippet               optional string, <250 characters summarizes group
        ------------------  --------------------------------------------------------
        access                optional string, can be private, public, or org
        ------------------  --------------------------------------------------------
        thumbnail             optional string, URL or file location to group image
        ------------------  --------------------------------------------------------
        is_invitation_only    optional boolean, defines whether users can join by request.
        ------------------  --------------------------------------------------------
        sort_field            optional string, specifies how shared items with the group are sorted.
        ------------------  --------------------------------------------------------
        sort_order            optional string, asc or desc for ascending or descending.
        ------------------  --------------------------------------------------------
        is_view_only          optional boolean, defines whether the group is searchable
        ==================  ========================================================

        :return:
            a boolean indicating success
        """



        properties = dict()
        postdata = self._postdata()
        if title:
            properties['title'] = title
        if tags:
            properties['tags'] = tags
        if description:
            properties['description'] = description
        if snippet:
            properties['snippet'] = snippet
        if access:
            properties['access'] = access
        if is_invitation_only:
            properties['isinvitationOnly'] = is_invitation_only
        if sort_field:
            properties['sortField'] = sort_field
        if sort_order:
            properties['sortOrder'] = sort_order
        if is_view_only:
            properties['isViewOnly'] = is_view_only

        postdata.update(properties)

        files = []
        if thumbnail:
            if _is_http_url(thumbnail):
                thumbnail = request.urlretrieve(thumbnail)[0]
                file_ext = os.path.splitext(thumbnail)[1]
                if not file_ext:
                    file_ext = imghdr.what(thumbnail)
                    if file_ext in ('gif', 'png', 'jpeg'):
                        new_thumbnail = thumbnail + '.' + file_ext
                        os.rename(thumbnail, new_thumbnail)
                        thumbnail = new_thumbnail
            files.append(('thumbnail', thumbnail, os.path.basename(thumbnail)))

        resp = self.con.post('community/groups/' + group_id + '/update', postdata, files)
        if resp:
            return resp.get('success')


    def update_item(self, itemid, item_properties=None, data=None, thumbnail=None, metadata=None, owner=None, folder=None):
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
        metadata         optional string, either a path or URL to metadata.
        ------------     ----------------------------------------------------
        owner            optional string, defaults to logged in user.
        ------------     ----------------------------------------------------
        folder           optional string, content folder where placing item
        ============     ====================================================


        ================  ============================================================================
         **Key**           **Value**
        ----------------  ----------------------------------------------------------------------------
        type              optional string, indicates type of item.  See URL 1 below for valid values.
        ----------------  ----------------------------------------------------------------------------
        typeKeywords      optinal string list.  Lists all sub-types.  See URL 1 for valid values.
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

        postdata = self._postdata()
        # Postdata is a dictionary object whose keys and values will be sent via an HTTP Post.
        if item_properties is not None:
            postdata.update(_to_utf8(item_properties))

        # Build the files list (tuples)
        files = []
        if data:
            if _is_http_url(data):
                data = request.urlretrieve(data)[0]
            elif os.path.isfile(data):
                files.append(('file', data, os.path.basename(data)))
            elif isinstance(data, dict):
                postdata['text'] = json.dumps(data)
            else:
                postdata['text'] = data
        if metadata:
            if _is_http_url(metadata):
                metadata = request.urlretrieve(metadata)[0]
            files.append(('metadata', metadata, 'metadata.xml'))
        if thumbnail:
            if _is_http_url(thumbnail):
                thumbnail = request.urlretrieve(thumbnail)[0]
                file_ext = os.path.splitext(thumbnail)[1]
                if not file_ext:
                    file_ext = imghdr.what(thumbnail)
                    if file_ext in ('gif', 'png', 'jpeg'):
                        new_thumbnail = thumbnail + '.' + file_ext
                        os.rename(thumbnail, new_thumbnail)
                        thumbnail = new_thumbnail
            files.append(('thumbnail', thumbnail, os.path.basename(thumbnail)))

        # If owner isn't specified, use the logged in user
        if not owner:
            owner = self.logged_in_user()['username']

        # Setup the item path, including the folder, and post to it
        path = 'content/users/' + owner
        if folder:
            path += '/' + folder
        path += '/items/' + itemid + '/update'
        resp = self.con.post(path, postdata, files)
        if resp:
            return resp.get('success')

    def get_version(self, force=False):
        """ Returns the portal version (using cache unless force=True).

        .. note::
            The version information is retrieved when you create the
            Portal object and then cached for future requests.  If you
            want to make a request to the Portal and not rely on the
            cache then you can set the force argument to True.

        Arguments:
            force        boolean, true=make a request, false=use cache

        :return:
            a string with the version.  The version is an internal number
            that may not match the version of the product purchased.  So
            2.3 is returned from Portal 10.2.1 for instance.


        """

        # If we've never retrieved the version before, or the caller is
        # forcing a check of the server, then check the server
        if not self._version or force:
            resp = self.con.post('', self._postdata())
            if not resp:
                old_resturl = _normalize_url(self.url) + 'sharing/'
                resp = self.con.post(old_resturl, self._postdata(), ssl=True)
                if resp:
                    _log.warning('Portal is pre-1.6.2; some things may not work')
                    self._is_pre_162 = True
                    self._is_pre_21 = True
                    self.resturl = old_resturl
                    self.con.baseurl = old_resturl
            else:
                version = resp.get('currentVersion')
                if version == '1.6.2' or version == '2.0':
                    _log.warning('Portal is pre-2.1; some features not supported')
                    self._is_pre_21 = True
            if resp:
                self._version = resp.get('currentVersion')

        return self._version


    def create_role(self, name, description):
        """ Creates a custom role with specified name and description

        :return:
            role_id if role is created, else None
        """
        postdata = self._postdata()
        postdata['name'] = name
        postdata['description'] = description

        resp = self.con.post('portals/self/createRole', postdata)
        if resp and resp.get('success'):
            return resp['id']

    def create_folder(self, owner, title):
        """ Creates a folder for the given user with the given title.

        ================  ========================================================
        **Argument**      **Description**
        ----------------  --------------------------------------------------------
        owner             required string, the name of the user
        ----------------  --------------------------------------------------------
        title             required string, the name of the folder to create for the owner
        ================  ========================================================

        :return:
            a json object like the following:
            {"username" : "portaladmin","id" : "bff13218991c4485a62c81db3512396f","title" : "testcreate"}
        """
        postdata = self._postdata()
        postdata['title'] = title
        resp = self.con.post('content/users/' + owner + '/createFolder', postdata)
        if resp and resp.get('success'):
            return resp['folder']



    def delete_folder(self, owner, folder):
        """ Deletes folder owned by owner with the given folder name.

        ================  ========================================================
        **Argument**      **Description**
        ----------------  --------------------------------------------------------
        owner             required string, the name of the user
        ----------------  --------------------------------------------------------
        folder            required string, the folder name
        ================  ========================================================

        :return:
            a boolean if succeeded.
        """
        postdata = self._postdata()
        folder_id = self.get_folder_id(owner, folder)
        if folder_id is None:
            print("Folder doesn't exist.")
            return False
        else:
            resp = self.con.post('content/users/' + owner + '/' + folder_id + '/delete', postdata)
            if resp:
                return resp.get('success')

    def move_item(self, itemid, owner, current_folder, folder_id):
        """ Moves the item to given folder """

        path = 'content/users/' + owner
        if current_folder :
            path += '/' + current_folder
        path += '/items/' + itemid + '/move'

        postdata = self._postdata()
        postdata['folder'] = folder_id
        resp = self.con.post(path, postdata)
        return resp

    def get_folder_id(self, owner, folder_name):
        """ Finds the folder for a particular owner and returns its id.

        ================  ========================================================
        **Argument**      **Description**
        ----------------  --------------------------------------------------------
        owner             required string, the name of the user
        ----------------  --------------------------------------------------------
        folder_name       required string, the name of the folder to search for
        ================  ========================================================

        :return:
            a boolean if succeeded.
        """
        resp = self.con.post('content/users/' + owner, self._postdata())
        if resp and 'folders' in resp:
            # Loop through each folder JSON object
            for fldr in resp['folders']:
                if fldr['title'].upper() == folder_name.upper():  # Force both strings to upper case for comparison
                    return fldr['id']
        return None # no such folder found for this owner

    def _is_searching_public(self, scope):
        if scope == 'public':
            return True
        elif scope == 'org':
            return False
        elif scope == 'default' or scope is None:
            # By default orgs won't search public
            return False if self.is_org else True
        else:
            raise ValueError('Unknown scope "' + scope + '". Supported ' \
                             + 'values are "public", "org", and "default"')


    def _invitations_page(self, start, num):
        postdata = self._postdata()
        postdata.update({ 'start': start, 'num': num })
        return self.con.post('portals/self/invitations', postdata)



    def _postdata(self):
        if self._basepostdata:
            # Return a defensive copy
            return copy.deepcopy(self._basepostdata)
        return None

    def _contents_page(self, owner, folderid=None, start=1, num=100):
        _log.info("getting user folders and items")
        postdata = self._postdata()
        postdata.update({"num":num, "start":start})
        path = "content/users/{}".format(owner)
        if folderid:
            path = "{}/{}".format(path, folderid)
        return self.con.post(path, postdata)

    def _search_page(self, q=None, bbox=None, start=1, num=10, sortfield='', sortorder='asc'):
        _log.info('Searching items (q=' + str(q) + ', bbox=' + str(bbox) \
                  + ', start=' + str(start) + ', num=' + str(num) + ')')
        postdata = self._postdata()
        postdata.update({ 'q': q or '', 'bbox': bbox or '', 'start': start, 'num': num,
                          'sortField': sortfield, 'sortOrder': sortorder })
        return self.con.post('search', postdata)


    def _groups_page(self, q=None, start=1, num=10, sortfield='',
                     sortorder='asc'):
        _log.info('Searching groups (q=' + str(q) + ', start=' + str(start) \
                  + ', num=' + str(num) + ')')
        postdata = self._postdata()
        postdata.update({ 'q': q, 'start': start, 'num': num,
                          'sortField': sortfield, 'sortOrder': sortorder })
        return self.con.post('community/groups', postdata)


    def _org_users_page(self, start=1, num=10):
        _log.info('Retrieving org users (start=' + str(start) \
                  + ', num=' + str(num) + ')')
        postdata = self._postdata()
        postdata['start'] = start
        postdata['num'] = num
        return self.con.post('portals/self/users', postdata)

    def _roles_page(self, start=1, num=10):
        _log.info('Retrieving roles(start=' + str(start) \
                  + ', num=' + str(num) + ')')
        postdata = self._postdata()
        postdata['start'] = start
        postdata['num'] = num
        return self.con.post('portals/self/roles', postdata)


    def _users_page(self, q=None, start=1, num=10, sortfield='', sortorder='asc'):
        _log.info('Searching users (q=' + str(q) + ', start=' + str(start) \
                  + ', num=' + str(num) + ')')
        postdata = self._postdata()
        postdata.update({ 'q': q, 'start': start, 'num': num,
                          'sortField': sortfield, 'sortOrder': sortorder })
        return self.con.post('community/users', postdata)




    def _extract(self, results, props=None):
        if not props or len(props) == 0:
            return results
        newresults = []
        for result in results:
            newresult = dict((p, result[p]) for p in props if p in result)
            newresults.append(newresult)
        return newresults
