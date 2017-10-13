"""
Helper classes for managing feature layers and datasets.  These class are not created by users directly.
Instances of this class, are available as a properties of feature layers and make it easier to manage them.
"""

import collections
import json
import tempfile
import time

from arcgis._impl.common._mixins import PropertyMap
from arcgis.gis import _GISResource


# pylint: disable=protected-access

class AttachmentManager(object):
    """
    Manager class for manipulating feature layer attachments. This class is not created by users directly.
    An instance of this class, called 'attachments', is available as a property of the FeatureLayer object,
    if the layer supports attachments.
    Users call methods on this 'attachments' object to manipulate (create, get, list, delete) attachments.
    """

    def __init__(self, layer):
        self._layer = layer

    def get_list(self, oid):
        """ returns the list of attachements for a given OBJECT ID """
        return self._layer._list_attachments(oid)['attachmentInfos']

    def download(self, oid, attachment_id, save_path=None):
        """ downloads attachment and returns it's path on disk """
        att_path = '{}/{}/attachments/{}'.format(self._layer.url, oid, attachment_id)
        att_list = self.get_list(oid)

        #get attachment file name
        desired_att = [att for att in att_list if att['id']== attachment_id]
        if len(desired_att) == 0: #bad attachment id
            raise RuntimeError
        else:
            att_name = desired_att[0]['name']

        if not save_path:
            save_path = tempfile.gettempdir()

        return self._layer._con.get(path=att_path, try_json=False, out_folder=save_path,
                                    file_name=att_name, token=self._layer._token, force_bytes=False)

    def add(self, oid, file_path):
        """ Adds an attachment to a feature layer
            Input:
              oid - string - OBJECTID value to add attachment to
              file_path - string - path to file
            Output:
              JSON Repsonse
        """
        return self._layer._add_attachment(oid, file_path)

    def delete(self, oid, attachment_id):
        """ removes an attachment from a feature
            Input:
              oid - integer or string - id of feature
              attachment_id - integer - id of attachment to erase
            Output:
               JSON response
        """
        return self._layer._delete_attachment(oid, attachment_id)

    def update(self, oid, attachment_id, file_path):
        """ updates an existing attachment with a new file
            Inputs:
               oid - string/integer - Unique record ID
               attachment_id - integer - Unique attachment identifier
               file_path - string - path to new attachment
            Output:
               JSON response
        """
        return self._layer._update_attachment(oid, attachment_id, file_path)


class SyncManager(object):
    """
    Manager class for manipulating replicas for syncing disconnected editing of feature layers.
    This class is not created by users directly.
    An instance of this class, called 'replicas', is available as a property of the FeatureLayerCollection object,
    if the layer is sync enabled / supports disconnected editing.
    Users call methods on this 'replicas' object to manipulate (create, synchronize, unregister) replicas.
    """

    # http://services.arcgis.com/help/fsDisconnectedEditing.html
    def __init__(self, featsvc):
        self._fs = featsvc

    def get_list(self):
        """ returns all the replicas for the feature layer collection """
        return self._fs._replicas

    # ----------------------------------------------------------------------
    def unregister(self, replica_id):
        """
           unregisters a replica from a feature layer collection
           Inputs:
             replica_id - The replicaID returned by the feature service
                          when the replica was created.
        """
        return self._fs._unregister_replica(replica_id)

    # ----------------------------------------------------------------------
    def get(self, replica_id):
        """
           returns replica metadata for a specific replica.
           Inputs:
              replica_id - The replicaID returned by the feature service
                           when the replica was created.
        """
        return self._fs._replica_info(replica_id)

    # ----------------------------------------------------------------------
    def create(self,
               replica_name,
               layers,
               layer_queries=None,
               geometry_filter=None,
               replica_sr=None,
               transport_type="esriTransportTypeUrl",
               return_attachments=False,
               return_attachments_databy_url=False,
               asynchronous=False,
               attachments_sync_direction="none",
               sync_model="none",
               data_format="json",
               replica_options=None,
               wait=False,
               out_path=None):
        """
        The create operation is performed on a feature layer collection
        resource. This operation creates the replica between the feature
        dataset and a client based on a client-supplied replica definition.
        It requires the Sync capability. See Sync overview for more
        information on sync. The response for create includes
        replicaID, replica generation number, and data similar to the
        response from the feature layer collection query operation.
        The create operation returns a response of type
        esriReplicaResponseTypeData, as the response has data for the
        layers in the replica. If the operation is called to register
        existing data by using replicaOptions, the response type will be
        esriReplicaResponseTypeInfo, and the response will not contain data
        for the layers in the replica.

        Inputs:
           replica_name - name of the replica
           layers - layers to export
           layer_queries - In addition to the layers and geometry parameters, the layer_queries
            parameter can be used to further define what is replicated. This
            parameter allows you to set properties on a per layer or per table
            basis. Only the properties for the layers and tables that you want
            changed from the default are required.
            Example:
             layer_queries = {"0":{"queryOption": "useFilter", "useGeometry": true,
             "where": "requires_inspection = Yes"}}
           geometry_filter - spatial filter from arcgis.geometry.filters module to filter results by a
                             spatial relationship with another geometry
           replica_sr - the spatial reference of the replica geometry.
           transport_type -  The transport_type represents the response format. If the
            transport_type is esriTransportTypeUrl, the JSON response is contained in a file,
            and the URL link to the file is returned. Otherwise, the JSON object is returned
            directly. The default is esriTransportTypeUrl.
            If async is true, the results will always be returned as if transport_type is
            esriTransportTypeUrl. If dataFormat is sqlite, the transportFormat will always be
            esriTransportTypeUrl regardless of how the parameter is set.
            Values: esriTransportTypeUrl | esriTransportTypeEmbedded
           return_attachments - If true, attachments are added to the replica and returned in
            the response. Otherwise, attachments are not included. The default is false. This
            parameter is only applicable if the feature service has attachments.
           return_attachments_databy_url -  If true, a reference to a URL will be provided for
            each attachment returned from create method. Otherwise, attachments are embedded
            in the response. The default is true. This parameter is only applicable if the
            feature service has attachments and if return_attachments is true.
           asynchronous - If true, the request is processed as an asynchronous job, and a URL is
            returned that a client can visit to check the status of the job. See the topic on
            asynchronous usage for more information. The default is false.
           attachments_sync_direction - Client can specify the attachmentsSyncDirection when
            creating a replica. AttachmentsSyncDirection is currently a createReplica property
            and cannot be overridden during sync.
            Values: none, upload, bidirectional
           sync_model - this parameter is used to indicate that the replica is being created for
            per-layer sync or per-replica sync. To determine which model types are supported by a
            service, query the supportsPerReplicaSync, supportsPerLayerSync, and supportsSyncModelNone
            properties of the Feature Service. By default, a replica is created for per-replica sync.
            If syncModel is perReplica, the syncDirection specified during sync applies to all layers
            in the replica. If the syncModel is perLayer, the syncDirection is defined on a layer-by-layer
            basis.

            If syncModel is perReplica, the response will have replicaServerGen. A perReplica syncModel
            requires the replicaServerGen on sync. The replicaServerGen tells the server the point
            in time from which to send back changes. If syncModel is perLayer, the response will include
            an array of server generation numbers for the layers in layerServerGens. A perLayer sync
            model requires the layerServerGens on sync. The layerServerGens tell the server the point
            in time from which to send back changes for a specific layer. sync_model=none can be used
            to export the data without creating a replica. Query the supportsSyncModelNone property
            of the feature service to see if this model type is supported.

            See the RollbackOnFailure and Sync Models topic for more details.
            Values: perReplica | perLayer | none
            Example: syncModel=perLayer
           data_format - The format of the replica geodatabase returned in the response. The
            default is json.
            Values: filegdb, json, sqlite, shapefile
           replica_options - This parameter instructs the create operation to create a
            new replica based on an existing replica definition (refReplicaId). It can be used
            to specify parameters for registration of existing data for sync. The operation
            will create a replica but will not return data. The responseType returned in the
            create response will be esriReplicaResponseTypeInfo.
           wait - if async, wait to pause the process until the async operation is completed.
           out_path - folder path to save the file
        """
        return self._fs._create_replica(replica_name,
                                        layers,
                                        layer_queries,
                                        geometry_filter,
                                        replica_sr,
                                        transport_type,
                                        return_attachments,
                                        return_attachments_databy_url,
                                        asynchronous,
                                        attachments_sync_direction,
                                        sync_model,
                                        data_format,
                                        replica_options,
                                        wait,
                                        out_path)

    # ----------------------------------------------------------------------
    def synchronize(self,
                    replica_id,
                    transport_type="esriTransportTypeUrl",
                    replica_server_gen=None,
                    return_ids_for_adds=False,
                    edits=None,
                    return_attachment_databy_url=False,
                    asynchronous=False,
                    sync_direction="snapshot",
                    sync_layers="perReplica",
                    edits_upload_id=None,
                    edits_upload_format=None,
                    data_format="json",
                    rollback_on_failure=True):
        """
        synchronizes replica with feature layer collection
        http://resources.arcgis.com/en/help/arcgis-rest-api/index.html#//02r3000000vv000000
        """
        # TODO:
        return self._fs._synchronize_replica(replica_id,
                                             transport_type,
                                             replica_server_gen,
                                             return_ids_for_adds,
                                             edits,
                                             return_attachment_databy_url,
                                             asynchronous,
                                             sync_direction,
                                             sync_layers,
                                             edits_upload_id,
                                             edits_upload_format,
                                             data_format,
                                             rollback_on_failure)
    def create_replica_item(self,
                            replica_name,
                            item,
                            destination_gis,
                            layers=None,
                            extent=None):
        """creates a replicated service from a parent to another GIS"""
        import tempfile
        import os
        from ..gis import Item
        fs = item.layers[0].container
        if layers is None:
            ls = fs.properties['layers']
            ts = fs.properties['tables']
            layers = ""
            for i in ls + ts:
                layers += str(i['id'])
        if extent is None:
            extent = fs.properties['fullExtent']
            if 'spatialReference' in extent:
                del extent['spatialReference']
        out_path = tempfile.gettempdir()
        from . import FeatureLayerCollection
        isinstance(fs, FeatureLayerCollection)
        db = fs._create_replica(replica_name=replica_name,
                            layers=layers,
                            geometry_filter=extent,
                            attachments_sync_direction=None,
                            transport_type="esriTransportTypeUrl",
                            return_attachments=True,
                            return_attachments_data_by_url=True,
                            asynchronous=True,
                            sync_model="perLayer",
                            target_type="server",
                            data_format="sqlite",
                            #target_type="server",
                            out_path=out_path,
                            wait=True)
        if os.path.isfile(db) == False:
            raise Exception("Could not create the replica")
        destination_content = destination_gis.content
        item = destination_content.add(item_properties= {"type" : "SQLite Geodatabase",
                                                    "tags" : "replication",
                                                    "title" : replica_name},
                                  data=db)
        published = item.publish()
        return published

    def sync_replicated_items(self, parent, child, replica_name):
        """
        synchronizes two replicated items between portals

        Paramters:
         :parent: arcgis.gis.Item class that points to a feature service
          who is the parent (source) dataset.
         :child: arcgis.gis.Item class that points to the child replica
         :replica_name: name of the replica to synchronize
        Output:
         boolean value. True means service is up to date/synchronized,
         False means the synchronization failed.


        """
        from ..gis import Item
        if isinstance(parent, Item) == False:
            raise ValueError("parent must be an Item")
        if isinstance(child, Item) == False:
            raise ValueError("child must be an Item")
        child_fs = child.layers[0].container
        parent_fs = parent.layers[0].container
        child_replicas = child_fs.replicas
        parent_replicas = parent_fs.replicas
        if child_replicas and \
           parent_replicas:
            child_replica_id = None
            parent_replica_id = None
            child_replica = None
            parent_replica = None
            for replica in child_replicas.get_list():
                if replica['replicaName'].lower() == replica_name.lower():
                    child_replica_id = replica['replicaID']
                    break
            for replica in parent_replicas.get_list():
                if replica['replicaName'].lower() == replica_name.lower():
                    parent_replica_id = replica['replicaID']
                    break
            if child_replica_id and \
               parent_replica_id:
                import tempfile, os
                child_replica = child_replicas.get(replica_id=child_replica_id)
                parent_replica = parent_replicas.get(replica_id=parent_replica_id)
                delta = parent_fs._synchronize_replica(replica_id=parent_replica_id,
                                                       transport_type="esriTransportTypeUrl",
                                                       close_replica=False,
                                                       return_ids_for_adds=False,
                                                       return_attachment_databy_url=True,
                                                       asynchronous=False,
                                                       sync_direction="download",
                                                       sync_layers=parent_replica['layerServerGens'],
                                                       edits_upload_format="sqlite",
                                                       data_format="sqlite",
                                                       rollback_on_failure=False,
                                                       out_path=tempfile.gettempdir())
                if os.path.isfile(delta) == False:
                    return True
                work, message = child_fs.upload(path=delta)
                if isinstance(message, dict) and \
                   'item' in message and \
                   'itemID' in message['item']:
                    syncLayers_child = child_replica['layerServerGens']
                    syncLayers_parent = parent_replica['layerServerGens']
                    for i in range(len(syncLayers_parent)):
                        syncLayers_child[i]['serverSibGen'] = syncLayers_parent[i]['serverGen']
                    child_fs._synchronize_replica(
                        replica_id=child_replica_id,
                        sync_layers=syncLayers_child,
                        sync_direction=None,
                        edits_upload_id=message['item']['itemID'],
                        return_ids_for_adds=False,
                        data_format="sqlite",
                        asynchronous=False,
                        edits_upload_format="sqlite")
                    return True
                else:
                    return False
            else:
                raise ValueError("Could not find replica name %s in both services" % replica_name)
        else:
            return False
        return False

class FeatureLayerCollectionManager(_GISResource):
    """
    Allows updating the definition (if access permits) of a feature layer collection.
    This class is not created by users directly.
    An instance of this class, called 'manager', is available as a property of the FeatureLayerCollection object.

    Users call methods on this 'manager' object to manage the feature layer collection.
    """

    def __init__(self, url, gis=None, fs=None):
        super(FeatureLayerCollectionManager, self).__init__(url, gis)
        self._fs = fs
        self._populate_layers()

    def _populate_layers(self):
        """
        populates layers and tables in the managed feature service
        """
        layers = []
        tables = []

        try:
            for layer in self.properties.layers:
                layers.append(FeatureLayerManager(self.url + '/' + str(layer['id']), self._gis))
        except:
            pass

        try:
            for table in self.properties.tables:
                tables.append(FeatureLayerManager(self.url + '/' + str(table['id']), self._gis))
        except:
            pass

        self.layers = layers
        self.tables = tables
    # ----------------------------------------------------------------------
    def refresh(self):
        """ refreshes a feature layer collection """
        params = {"f": "json"}
        refresh_url = self._url + "/refresh"
        res = self._con.post(refresh_url, params)

        super(FeatureLayerCollectionManager, self)._refresh()
        self._populate_layers()

        self._fs._refresh()
        self._fs._populate_layers()

        return res
    # ----------------------------------------------------------------------
    def create_view(self,
                    name,
                    spatial_reference=None,
                    extent=None,
                    allow_schema_changes=True,
                    updateable=True,
                    capabilities="Query",
                    view_layers=None):
        """
        Creates a View of an Existing Feature Service.

        Parameters:
         :name: Name of the new view item
         :spatial_reference:
         :extent: initial extent of the object
         :allow_schema_changes: boolean that determines if a view can alter a
          service's schema.
         :updateable: boolean value that says if a view can update values
         :capabilities: determines what operations a user can do on a given
          view
         :view_layers: optional dictionary used to define the layers that
          are referenced inside the view.  The default is all layers.
        :Returns:
         Item for  the view
        """
        import os
        from . import FeatureLayerCollection
        gis = self._gis
        content = gis.content
        if 'serviceItemId' not in self.properties:
            raise Exception("A registered hosted feature service is required to use create_view")
        item_id = self.properties['serviceItemId']
        item = content.get(itemid=item_id)
        url = item.url
        fs = FeatureLayerCollection(url=url, gis=gis)
        if gis._url.lower().find("sharing/rest") < 0:
            url = gis._url + "/sharing/rest"
        else:
            url = gis._url
        url = "%s/content/users/%s/createService" % (url, gis.users.me.username)
        params = {
            "f" : "json",
            "isView" : True,
            "createParameters" :json.dumps({"name": name,
                                            "isView":True,
                                            "sourceSchemaChangesAllowed": allow_schema_changes,
                                            "isUpdatableView": updateable,
                                            "spatialReference":spatial_reference or fs.properties['spatialReference'],
                                            "initialExtent": extent or fs.properties['initialExtent'],
                                            "capabilities":capabilities or fs.properties['capabilties']}),
            "outputType" : "featureService"
        }
        res = gis._con.post(path=url, postdata=params)
        view = content.get(res['itemId'])
        fs_view = FeatureLayerCollection(url=view.url, gis=gis)
        add_def = {
            "layers" : []
        }
        if view_layers is None:
            for lyr in fs.layers:
                add_def['layers'].append(
                    {
                        "adminLayerInfo" : {
                            "viewLayerDefinition" :
                        {
                            "sourceServiceName" : os.path.basename(os.path.dirname(fs.url)),
                            "sourceLayerId" : lyr.manager.properties['id'],
                            "sourceLayerFields" :  "*"
                        }
                        },
                        "name" : lyr.manager.properties['name']
                    })
        else:
            add_def = view_layers
        fs_view.manager.add_to_definition(add_def)
        return content.get(res['itemId'])
    # ----------------------------------------------------------------------
    def add_to_definition(self, json_dict):
        """
           The add_to_definition operation supports adding a definition
           property to a hosted feature layer collection service. The result of this
           operation is a response indicating success or failure with error
           code and description.

           This function will allow users to change or add additional values
           to an already published service.

           Input:
              json_dict - part to add to host service.  The part format can
                          be derived from the properties property.  For
                          layer level modifications, run updates on each
                          individual feature service layer object.
           Output:
              JSON message as dictionary
        """
        if isinstance(json_dict, PropertyMap):
            json_dict = dict(json_dict)

        params = {
            "f": "json",
            "addToDefinition": json.dumps(json_dict),
            "async": json.dumps(False)
        }
        adddefn_url = self._url + "/addToDefinition"
        old_ref = self._con._referer
        self._con._referer = "http"
        res = self._con.post(adddefn_url, params)
        self.refresh()
        self._con._referer = old_ref
        return res

    # ----------------------------------------------------------------------
    def update_definition(self, json_dict):
        """
           The update_definition operation supports updating a definition
           property in a hosted feature layer collection service. The result of this
           operation is a response indicating success or failure with error
           code and description.

           Input:
              json_dict - part to add to host service.  The part format can
                          be derived from the properties property.  For
                          layer level modifications, run updates on each
                          individual feature service layer object.
           Output:
              JSON Message as dictionary
        """
        definition = None
        if json_dict is not None:

            if isinstance(json_dict, PropertyMap):
                definition = dict(json_dict)
            if isinstance(json_dict, collections.OrderedDict):
                definition = json_dict
            else:

                definition = collections.OrderedDict()
                if 'hasStaticData' in json_dict:
                    definition['hasStaticData'] = json_dict['hasStaticData']
                if 'allowGeometryUpdates' in json_dict:
                    definition['allowGeometryUpdates'] = json_dict['allowGeometryUpdates']
                if 'capabilities' in json_dict:
                    definition['capabilities'] = json_dict['capabilities']
                if 'editorTrackingInfo' in json_dict:
                    definition['editorTrackingInfo'] = collections.OrderedDict()
                    if 'enableEditorTracking' in json_dict['editorTrackingInfo']:
                        definition['editorTrackingInfo']['enableEditorTracking'] = json_dict['editorTrackingInfo'][
                            'enableEditorTracking']

                    if 'enableOwnershipAccessControl' in json_dict['editorTrackingInfo']:
                        definition['editorTrackingInfo']['enableOwnershipAccessControl'] = \
                            json_dict['editorTrackingInfo']['enableOwnershipAccessControl']

                    if 'allowOthersToUpdate' in json_dict['editorTrackingInfo']:
                        definition['editorTrackingInfo']['allowOthersToUpdate'] = json_dict['editorTrackingInfo'][
                            'allowOthersToUpdate']

                    if 'allowOthersToDelete' in json_dict['editorTrackingInfo']:
                        definition['editorTrackingInfo']['allowOthersToDelete'] = json_dict['editorTrackingInfo'][
                            'allowOthersToDelete']

                    if 'allowOthersToQuery' in json_dict['editorTrackingInfo']:
                        definition['editorTrackingInfo']['allowOthersToQuery'] = json_dict['editorTrackingInfo'][
                            'allowOthersToQuery']
                    if isinstance(json_dict['editorTrackingInfo'], dict):
                        for key, val in json_dict['editorTrackingInfo'].items():
                            if key not in definition['editorTrackingInfo']:
                                definition['editorTrackingInfo'][key] = val
                if isinstance(json_dict, dict):
                    for key, val in json_dict.items():
                        if key not in definition:
                            definition[key] = val

        params = {
            "f": "json",
            "updateDefinition": json.dumps(obj=definition, separators=(',', ':')),
            "async": False
        }
        u_url = self._url + "/updateDefinition"
        old_ref = self._con._referer
        self._con._referer = "http"
        res = self._con.post(u_url, params)
        self._con._referer = old_ref
        self.refresh()
        return res

    # ----------------------------------------------------------------------
    def delete_from_definition(self, json_dict):
        """
        The delete_from_definition operation supports deleting a
        definition property from a hosted feature layer collection service. The result of
        this operation is a response indicating success or failure with
        error code and description.
        See http://resources.arcgis.com/en/help/arcgis-rest-api/index.html#/Delete_From_Definition_Feature_Service/02r30000021w000000/ # noqa
        for additional information on this function.
        Input:
          json_dict - part to add to host service.  The part format can
                      be derived from the properties property.  For
                      layer level modifications, run updates on each
                      individual feature service layer object.  Only
                      include the items you want to remove from the
                      FeatureService or layer.

        Output:
          JSON Message as dictionary

        """
        params = {
            "f": "json",
            "deleteFromDefinition": json.dumps(json_dict),
            "async": False
        }
        u_url = self._url + "/deleteFromDefinition"

        res = self._con.post(u_url, params)
        self.refresh()
        return res

    # ----------------------------------------------------------------------
    def overwrite(self, data_file):
        """
        Overwrite all the features and layers in a hosted feature layer collection service. This operation removes
        all features but retains the properties (such as symbology, itemID) and capabilities configured on the service.
        There are some limits to using this operation:
            1. Only hosted feature layer collection services can be overwritten
            2. The original data used to publish this layer should be available on the portal
            3. The data file used to overwrite should be of the same format and filename as the original that was used to
            publish the layer
            4. The schema (column names, column data types) of the data_file should be the same as original. You can have
            additional or fewer rows (features).

        In addition to overwriting the features, this operation also updates the data of the item used to published this
        layer.

        :param data: path to data_file used to overwrite the hosted feature layer collection
        :return: JSON message as dictionary such as {'success':True} or {'error':'error message'}
        """
        # region Get Item associated with the service
        if 'serviceItemId' in self.properties.keys():
            feature_layer_item = self._gis.content.get(self.properties['serviceItemId'])
        else:
            return {'error': 'Can only overwrite a hosted feature layer collection'}
        # endregion

        # region find data item related to this hosted feature layer
        related_data_items = feature_layer_item.related_items('Service2Data', 'forward')
        if len(related_data_items) > 0:
            related_data_item = related_data_items[0]
        else:
            return {'error': 'Cannot find related data item used to publish this feature layer'}

        # endregion

        # region construct publishParameters dictionary
        if related_data_item.type in ['CSV', 'Shapefile', 'File Geodatabase']:
            # construct a full publishParameters that is a combination of existing Feature Layer definition
            # and original publishParameters.json used for publishing the service the first time

            # get old publishParameters.json
            path = "content/items/" + feature_layer_item.itemid + "/info/publishParameters.json"
            postdata = {'f': 'json'}

            old_publish_parameters = self._gis._con.post(path, postdata)

            # get FeatureServer definition
            feature_service_def = dict(self.properties)

            # Get definition of each layer and table, remove fields in the dict
            layers_dict = []
            tables_dict = []
            for layer in self.layers:
                layer_def = dict(layer.properties)
                if 'fields' in layer_def.keys():
                    dump = layer_def.pop("fields")
                layers_dict.append(layer_def)

            for table in self.tables:
                table_def = dict(table.properties)
                if 'fields' in table_def.keys():
                    dump = table_def.pop('fields')
                tables_dict.append(table_def)

            # Splice the detailed table and layer def with FeatuerServer def
            feature_service_def['layers'] = layers_dict
            feature_service_def['tables'] = tables_dict
            from pathlib import Path
            service_name = Path(self.url).parts[-2]  # get service name from url
            feature_service_def['name'] = service_name

            # combine both old publish params and full feature service definition
            publish_parameters = feature_service_def
            publish_parameters.update(old_publish_parameters)

        else:
            # overwriting a SD case - no need for detailed publish parameters
            publish_parameters = None
        # endregion

        #region Perform overwriting
        if related_data_item.update(data=data_file):
            published_item = related_data_item.publish(publish_parameters, overwrite=True)
            if published_item is not None:
                return {'success': True}
            else:
                return {'error': 'Unable to overwrite the hosted feature layer collection'}
        else:
            return {'error': 'Unable to update related data item with new data'}
        #end region

        # ----------------------------------------------------------------------

    def _gen_overwrite_publishParameters(self, flc_item):
        """
        This internal method generates publishParameters for overwriting a hosted feature layer collection. This is used
        by Item.publish() method when user wants to originate the overwrite process from the data item instead of
        the hosted feature layer.

        :param flc_item: The Feature Layer Collection Item object that is being overwritten
        :return: JSON message as dictionary with to be used as publishParameters payload in the publish REST call.
        """

        # region construct publishParameters dictionary
        # construct a full publishParameters that is a combination of existing Feature Layer definition
        # and original publishParameters.json used for publishing the service the first time

        # get old publishParameters.json
        path = "content/items/" + flc_item.itemid + "/info/publishParameters.json"
        postdata = {'f': 'json'}

        old_publish_parameters = self._gis._con.post(path, postdata)

        # get FeatureServer definition
        feature_service_def = dict(self.properties)

        # Get definition of each layer and table, remove fields in the dict
        layers_dict = []
        tables_dict = []
        for layer in self.layers:
            layer_def = dict(layer.properties)
            if 'fields' in layer_def.keys():
                dump = layer_def.pop("fields")
            layers_dict.append(layer_def)

        for table in self.tables:
            table_def = dict(table.properties)
            if 'fields' in table_def.keys():
                dump = table_def.pop('fields')
            tables_dict.append(table_def)

        # Splice the detailed table and layer def with FeatuerServer def
        feature_service_def['layers'] = layers_dict
        feature_service_def['tables'] = tables_dict
        from pathlib import Path
        service_name = Path(self.url).parts[-2]  # get service name from url
        feature_service_def['name'] = service_name

        # combine both old publish params and full feature service definition
        publish_parameters = feature_service_def
        publish_parameters.update(old_publish_parameters)

        # endregion

        return publish_parameters


class FeatureLayerManager(_GISResource):
    """
    Allows updating the definition (if access permits) of a feature layer. This class is not created by users
    directly.
    An instance of this class, called 'manager', is available as a property of the FeatureLayer object,
    if the layer can be managed by the user.
    Users call methods on this 'manager' object to manage the feature layer.
    """

    def __init__(self, url, gis=None):
        super(FeatureLayerManager, self).__init__(url, gis)
        self._hydrate()

    # ----------------------------------------------------------------------
    @classmethod
    def fromitem(cls, item, layer_id=0):
        """
        Creates a FeatureLayerManager object from a GIS Item.
        The type of item should be a 'Feature Service' that represents a FeatureLayerCollection.
        The layer_id is the id of the layer in feature layer collection (feature service).
        """
        if item.type != "Feature Service":
            raise TypeError("item must be a of type Feature Service, not " + item.type)
        from arcgis.features import FeatureLayer
        return FeatureLayer.fromitem(item, layer_id).manager

    # ----------------------------------------------------------------------
    def refresh(self):
        """ refreshes a service """
        params = {"f": "json"}
        u_url = self._url + "/refresh"
        res = self._con.post(u_url, params)

        super(FeatureLayerManager, self)._refresh()

        return res

    # ----------------------------------------------------------------------
    def add_to_definition(self, json_dict):
        """
           The addToDefinition operation supports adding a definition
           property to a hosted feature layer. The result of this
           operation is a response indicating success or failure with error
           code and description.

           This function will allow users to change add additional values
           to an already published service.

           Input:
              json_dict - part to add to host service.  The part format can
                          be derived from the asDictionary property.  For
                          layer level modifications, run updates on each
                          individual feature service layer object.
           Output:
              JSON message as dictionary
        """

        if isinstance(json_dict, PropertyMap):
            json_dict = dict(json_dict)

        params = {
            "f": "json",
            "addToDefinition": json.dumps(json_dict),
            # "async" : False
        }
        u_url = self._url + "/addToDefinition"

        res = self._con.post(u_url, params)
        self.refresh()
        return res

    # ----------------------------------------------------------------------
    def update_definition(self, json_dict):
        """
           The updateDefinition operation supports updating a definition
           property in a hosted feature layer. The result of this
           operation is a response indicating success or failure with error
           code and description.

           Input:
              json_dict - part to add to host service.  The part format can
                          be derived from the asDictionary property.  For
                          layer level modifications, run updates on each
                          individual feature service layer object.
           Output:
              JSON Message as dictionary
        """

        if isinstance(json_dict, PropertyMap):
            json_dict = dict(json_dict)

        params = {
            "f": "json",
            "updateDefinition": json.dumps(json_dict),
            "async": False
        }

        u_url = self._url + "/updateDefinition"

        res = self._con.post(u_url, params)
        self.refresh()
        return res

    # ----------------------------------------------------------------------
    def delete_from_definition(self, json_dict):
        """
           The deleteFromDefinition operation supports deleting a
           definition property from a hosted feature layer. The result of
           this operation is a response indicating success or failure with
           error code and description.
           See: http://resources.arcgis.com/en/help/arcgis-rest-api/index.html#/Delete_From_Definition_Feature_Service/02r30000021w000000/ # noqa
           for additional information on this function.
           Input:
              json_dict - part to add to host service.  The part format can
                          be derived from the asDictionary property.  For
                          layer level modifications, run updates on each
                          individual feature service layer object.  Only
                          include the items you want to remove from the
                          FeatureService or layer.

           Output:
              JSON Message as dictionary

        """

        if isinstance(json_dict, PropertyMap):
            json_dict = dict(json_dict)

        params = {
            "f": "json",
            "deleteFromDefinition": json.dumps(json_dict)
        }
        u_url = self._url + "/deleteFromDefinition"

        res = self._con.post(u_url, params)
        self.refresh()
        return res

    # ----------------------------------------------------------------------
    def truncate(self,
                 attachment_only=False,
                 asynchronous=False,
                 wait=True):
        """
           The truncate operation supports deleting all features or attachments
           in a hosted feature service layer. The result of this operation is a
           response indicating success or failure with error code and description.
           See: http://resources.arcgis.com/en/help/arcgis-rest-api/#/Truncate_Feature_Layer/02r3000002v0000000/ # noqa
           for additional information on this function.
           Input:
              attachment_only - Deletes all the attachments for this layer.
                                None of the layer features will be deleted
                                when attachmentOnly=true.
              asynchronous - Supports options for asynchronous processing. The
                      default format is false. It is recommended to set
                      async=true for larger datasets.
              wait - if async, wait to pause the process until the async
                     operation is completed.

           Output:
              JSON Message as dictionary

        """
        params = {
            "f": "json",
            "attachmentOnly": attachment_only,
            "async": asynchronous
        }
        u_url = self._url + "/truncate"

        if asynchronous:
            if wait:
                job = self._con.post(u_url, params)
                status = self._get_status(url=job['statusURL'])
                while status['status'] not in ("Completed", "CompletedWithErrors", "Failed"):
                    # wait before checking again
                    time.sleep(2)
                    status = self._get_status(url=job['statusURL'])

                res = status
                self.refresh()
            else:
                res = self._con.post(u_url, params)
                # Leave calling refresh to user since wait is false
        else:
            res = self._con.post(u_url, params)
            self.refresh()
        return res

    # ----------------------------------------------------------------------
    def _get_status(self, url):
        """gets the status when exported async set to True"""
        params = {"f": "json"}
        url += "/status"
        return self._con.get(url, params)
