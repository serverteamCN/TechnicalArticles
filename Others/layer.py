"""
Feature Layers and Tables provide the primary interface for working with features in a GIS.

Users create, import, export, analyze, edit, and visualize features, i.e. entities in space as feature layers.

A FeatureLayerCollection is a collection of feature layers and tables, with the associated relationships among the entities.
"""
import json
import os
from re import search
import time

import six
from arcgis._impl.common import _utils
from arcgis._impl.common._filters import StatisticFilter, TimeFilter, GeometryFilter
from arcgis._impl.common._mixins import PropertyMap
from arcgis._impl.common._utils import _date_handler, chunks

from .managers import AttachmentManager, SyncManager, FeatureLayerCollectionManager, FeatureLayerManager
from .feature import Feature, FeatureSet
from arcgis.geometry import SpatialReference
from arcgis.gis import Layer, _GISResource


class FeatureLayer(Layer):
    """
    The feature layer is the primary concept for working with features in a GIS.

    Users create, import, export, analyze, edit, and visualize features, i.e. entities in space as feature layers.

    Feature layers can be added to and visualized using maps. They act as inputs to and outputs from feature analysis
    tools.

    Feature layers are created by publishing feature data to a GIS, and are exposed as a broader resource (Item) in the
    GIS. Feature layer objects can be obtained through the layers attribute on feature layer Items in the GIS.
    """
    def __init__(self, url, gis=None, container=None):
        """
        Constructs a feature layer given a feature layer URL
        :param url: feature layer url
        :param gis: optional, the GIS that this layer belongs to. Required for secure feature layers.
        :param container: optional, the feature layer collection to which this layer belongs
        """
        super(FeatureLayer, self).__init__(url, gis)
        self._storage = container
        self.attachments = AttachmentManager(self)


    @classmethod
    def fromitem(cls, item, layer_id=0):
        """
        Creates a feature layer from a GIS Item.
        The type of item should be a 'Feature Service' that represents a FeatureLayerCollection.
        The layer_id is the id of the layer in feature layer collection (feature service).
        """
        return FeatureLayerCollection.fromitem(item).layers[layer_id]

    @property
    def manager(self):
        """
        Helper object to manage the feature layer, update it's definition, etc
        """
        url = self._url
        res = search("/rest/", url).span()
        add_text = "admin/"
        part1 = url[:res[1]]
        part2 = url[res[1]:]
        admin_url = "%s%s%s" % (part1, add_text, part2)

        res = FeatureLayerManager(admin_url, self._gis)
        return res

    @property
    def container(self):
        """
        The feature layer collection to which this layer belongs.
        """
        return self._storage

    @container.setter
    def container(self, value):
        """
        The feature layer collection to which this layer belongs.
        """
        self._storage = value

    def _add_attachment(self, oid, file_path):
        """ Adds an attachment to a feature service
            Input:
              oid - string - OBJECTID value to add attachment to
              file_path - string - path to file
            Output:
              JSON Repsonse
        """
        attach_url = self._url + "/%s/addAttachment" % oid
        params = {'f': 'json'}

        files = {'attachment': file_path}
        res = self._con.post(path=attach_url,
                             postdata=params,
                             files=files, token=self._token)
        return res

    # ----------------------------------------------------------------------
    def _delete_attachment(self, oid, attachment_id):
        """ removes an attachment from a feature service feature
            Input:
              oid - integer or string - id of feature
              attachment_id - integer - id of attachment to erase
            Output:
               JSON response
        """
        url = self._url + "/%s/deleteAttachments" % oid
        params = {
            "f": "json",
            "attachmentIds": "%s" % attachment_id
        }
        return self._con.post(url, params, token=self._token)

    # ----------------------------------------------------------------------
    def _update_attachment(self, oid, attachment_id, file_path):
        """ updates an existing attachment with a new file
            Inputs:
               oid - string/integer - Unique record ID
               attachment_id - integer - Unique attachment identifier
               file_path - string - path to new attachment
            Output:
               JSON response
        """
        url = self._url + "/%s/updateAttachment" % oid
        params = {
            "f": "json",
            "attachmentId": "%s" % attachment_id
        }
        files = {'attachment': file_path}
        res = self._con.post(path=url,
                             postdata=params,
                             files=files, token=self._token)
        return res

    # ----------------------------------------------------------------------
    def _list_attachments(self, oid):
        """ list attachements for a given OBJECT ID """
        url = self._url + "/%s/attachments" % oid
        params = {
            "f": "json"
        }
        return self._con.get(path=url, params=params, token=self._token)

    # ----------------------------------------------------------------------
    def query(self,
              where="1=1",
              out_fields="*",
              time_filter=None,
              geometry_filter=None,
              return_geometry=True,
              return_count_only=False,
              return_ids_only=False,
              return_distinct_values=False,
              return_extent_only=False,
              group_by_fields_for_statistics=None,
              statistic_filter=None,
              result_offset=None,
              result_record_count=None,
              object_ids=None,
              distance=None,
              units=None,
              max_allowable_offset=None,
              out_sr=None,
              geometry_precision=None,
              gdb_version=None,
              order_by_fields=None,
              out_statistics=None,
              return_z=False,
              return_m=False,
              multipatch_option=None,
              quanitization_parameters=None,
              return_centroid=False,
              return_all_records=True,
              **kwargs):
        """ queries a feature layer based on a sql statement
            Inputs:
                where - the selection sql statement
                out_fields - the attribute fields to return
                object_ids -  The object IDs of this layer or table to be
                            queried.
                distance - The buffer distance for the input geometries.
                          The distance unit is specified by units. For
                          example, if the distance is 100, the query
                          geometry is a point, units is set to meters, and
                          all points within 100 meters of the point are
                          returned.
                units - The unit for calculating the buffer distance. If
                        unit is not specified, the unit is derived from the
                        geometry spatial reference. If the geometry spatial
                        reference is not specified, the unit is derived
                        from the feature service data spatial reference.
                        This parameter only applies if
                        supportsQueryWithDistance is true.
                        Values: esriSRUnit_Meter | esriSRUnit_StatuteMile |
                        esriSRUnit_Foot | esriSRUnit_Kilometer |
                        esriSRUnit_NauticalMile | esriSRUnit_USNauticalMile
                time_filter - a TimeFilter object where either the start time
                            or start and end time are defined to limit the
                            search results for a given time.  The values in
                            the timeFilter should be as UTC timestampes in
                            milliseconds.  No checking occurs to see if they
                            are in the right format.
                geometry_filter - spatial filter from arcgis.geometry.filters module to filter results by a
                                spatial relationship with another geometry
                maxAllowableOffset - This option can be used to specify the
                                     maxAllowableOffset to be used for
                                     generalizing geometries returned by
                                     the query operation.
                                     The maxAllowableOffset is in the units
                                     of outSR. If outSR is not specified,
                                     maxAllowableOffset is assumed to be in
                                     the unit of the spatial reference of
                                     the map.
                outSR - The spatial reference of the returned geometry.
                geometryPrecision -  This option can be used to specify the
                                     number of decimal places in the
                                     response geometries returned by the
                                     Query operation.
                gdbVersion - Geodatabase version to query
                returnDistinctValues -  If true, it returns distinct values
                                        based on the fields specified in
                                        outFields. This parameter applies
                                        only if the
                                        supportsAdvancedQueries property of
                                        the layer is true.
                returnIdsOnly -  If true, the response only includes an
                                 array of object IDs. Otherwise, the
                                 response is a feature set. The default is
                                 false.
                returnCountOnly -  If true, the response only includes the
                                   count (number of features/records) that
                                   would be returned by a query. Otherwise,
                                   the response is a feature set. The
                                   default is false. This option supersedes
                                   the returnIdsOnly parameter. If
                                   returnCountOnly = true, the response will
                                   return both the count and the extent.
                returnExtentOnly -  If true, the response only includes the
                                    extent of the features that would be
                                    returned by the query. If
                                    returnCountOnly=true, the response will
                                    return both the count and the extent.
                                    The default is false. This parameter
                                    applies only if the
                                    supportsReturningQueryExtent property
                                    of the layer is true.
                orderByFields - One or more field names on which the
                                features/records need to be ordered. Use
                                ASC or DESC for ascending or descending,
                                respectively, following every field to
                                control the ordering.
                groupByFieldsForStatistics - One or more field names on
                                             which the values need to be
                                             grouped for calculating the
                                             statistics.
                outStatistics - The definitions for one or more field-based
                                statistics to be calculated.
                returnZ -  If true, Z values are included in the results if
                           the features have Z values. Otherwise, Z values
                           are not returned. The default is false.
                returnM - If true, M values are included in the results if
                          the features have M values. Otherwise, M values
                          are not returned. The default is false.
                multipatchOption - This option dictates how the geometry of
                                   a multipatch feature will be returned.
                resultOffset -  This option can be used for fetching query
                                results by skipping the specified number of
                                records and starting from the next record
                                (that is, resultOffset + 1th).
                resultRecordCount - This option can be used for fetching
                                    query results up to the
                                    resultRecordCount specified. When
                                    resultOffset is specified but this
                                    parameter is not, the map service
                                    defaults it to maxRecordCount. The
                                    maximum value for this parameter is the
                                    value of the layer's maxRecordCount
                                    property.
                quanitizationParameters - Used to project the geometry onto
                                          a virtual grid, likely
                                          representing pixels on the screen.
                returnCentroid - Used to return the geometry centroid
                                 associated with each feature returned. If
                                 true, the result includes the geometry
                                 centroid. The default is false.
                return_all_records - When True, the query operation will call
                                    the service until all records that satisfy
                                    the where_clause are returned. Note: result_offset
                                    and result_record_count will be ignored
                                    if return_all_records is True. Also, if
                                    return_count_only, return_ids_only, or
                                    return_extent_only are True, this parameter
                                    will be ignored.
               kwargs - optional parameters that can be passed to the Query
                 function.  This will allow users to pass additional
                 parameters not explicitly implemented on the function. A
                 complete list of functions available is documented on the
                 Query REST API.
            Output:
               A FeatureSet containing the features matching the query
               unless another return type is specified, such as count
         """
        url = self._url + "/query"
        params = {"f": "json"}
        params['where'] = where
        params['outFields'] = out_fields
        params['returnGeometry'] = return_geometry
        params['returnDistinctValues'] = return_distinct_values
        params['returnCentroid'] = return_centroid
        params['returnCountOnly'] = return_count_only
        params['returnExtentOnly'] = return_extent_only
        params['returnIdsOnly'] = return_ids_only
        params['returnZ'] = return_z
        params['returnM'] = return_m
        if return_count_only or return_extent_only or return_ids_only:
            return_all_records = False
        if result_record_count and not return_all_records:
            params['resultRecordCount'] = result_record_count
        if result_offset and not return_all_records:
            params['resultOffset'] = result_offset
        if quanitization_parameters:
            params['quanitizationParameters'] = quanitization_parameters
        if multipatch_option:
            params['multipatchOption'] = multipatch_option
        if order_by_fields:
            params['orderByFields'] = order_by_fields
        if group_by_fields_for_statistics:
            params['groupByFieldsForStatistics'] = group_by_fields_for_statistics
        if statistic_filter and \
                isinstance(statistic_filter, StatisticFilter):
            params['outStatistics'] = statistic_filter.filter
        if out_statistics:
            params['outStatistics'] = out_statistics
        if out_sr:
            params['outSR'] = out_sr
        if max_allowable_offset:
            params['maxAllowableOffset'] = max_allowable_offset
        if gdb_version:
            params['gdbVersion'] = gdb_version
        if geometry_precision:
            params['geometryPrecision'] = geometry_precision
        if object_ids:
            params['objectIds'] = object_ids
        if distance:
            params['distance'] = distance
        if units:
            params['units'] = units
        if time_filter and \
                isinstance(time_filter, TimeFilter):
            for key, val in time_filter.filter:
                params[key] = val
        elif isinstance(time_filter, dict):
            for key, val in time_filter.items():
                params[key] = val
        if geometry_filter and \
                isinstance(geometry_filter, GeometryFilter):
            for key, val in geometry_filter.filter:
                params[key] = val
        elif geometry_filter and \
                isinstance(geometry_filter, dict):
            for key, val in geometry_filter.items():
                params[key] = val
        if len(kwargs) > 0:
            for key, val in kwargs.items():
                params[key] = val
                del key, val

        if not return_all_records:
            return self._query(url, params)

        params['returnCountOnly'] = True
        record_count = self._query(url, params)
        if 'maxRecordCount' in self.properties:
            max_records = self.properties['maxRecordCount']
        else:
            max_records = 1000

        params['returnCountOnly'] = False
        if record_count <= max_records:
            return self._query(url, params)

        result = None
        if 'advancedQueryCapabilities' not in self.properties or \
                'supportsPagination' not in self.properties['advancedQueryCapabilities'] or \
                not self.properties['advancedQueryCapabilities']['supportsPagination']:
            params['returnIdsOnly'] = True
            oid_info = self._query(url, params)
            params['returnIdsOnly'] = False
            for ids in chunks(oid_info['objectIds'], max_records):
                ids = [str(i) for i in ids]
                sql = "%s in (%s)" % (oid_info['objectIdFieldName'], ",".join(ids))
                params['where'] = sql
                records = self._query(url, params)
                if result:
                    result.features.extend(records.features)
                else:
                    result = records
        else:
            i = 0
            params['resultRecordCount'] = max_records

            while True:
                params['resultOffset'] = max_records * i
                records = self._query(url, params)

                if result:
                    result.features.extend(records.features)
                else:
                    result = records

                if len(records.features) < max_records:
                    break
                i += 1

        return result
    # ----------------------------------------------------------------------
    def validate_sql(self, sql, sql_type="where"):
        """
        The validate_sql operation validates an SQL-92 expression or WHERE
        clause.
        The validate_sql operation ensures that an SQL-92 expression, such
        as one written by a user through a user interface, is correct
        before performing another operation that uses the expression. For
        example, validateSQL can be used to validate information that is
        subsequently passed in as part of the where parameter of the
        calculate operation.
        validate_sql also prevents SQL injection. In addition, all table
        and field names used in the SQL expression or WHERE clause are
        validated to ensure they are valid tables and fields.

        :Parameters:
         :sql: the SQL expression of WHERE clause to validate
           Example: "Population > 300000"
         :sql_type:  Three SQL types are supported in validate_sql
          - where (default) - Represents the custom WHERE clause the user
            can compose when querying a layer or using calculate.
          - expression - Represents an SQL-92 expression. Currently,
            expression is used as a default value expression when adding a
            new field or using the calculate API.
          - statement - Represents the full SQL-92 statement that can be
            passed directly to the database. No current ArcGIS REST API
            resource or operation supports using the full SQL-92 SELECT
            statement directly. It has been added to the validateSQL for
            completeness.
            Values: where | expression | statement
        """
        params = {
            "f" : "json"
        }
        if not isinstance(sql, six.string_types):
            raise ValueError("sql must be a string")
        else:
            params['sql'] = sql
        if sql_type.lower() not in ['where', 'expression', 'statement']:
            raise ValueError("sql_type must have value of: where, expression or statement")
        else:
            params['sqlType'] = sql_type
        sql_type = sql_type.lower()
        url = self._url + "/validateSQL"
        return self._con.post(path=url,
                              postdata=params,
                              token=self._token)
    # ----------------------------------------------------------------------
    def query_related_records(self,
                              object_ids,
                              relationship_id,
                              out_fields="*",
                              definition_expression=None,
                              return_geometry=True,
                              max_allowable_offset=None,
                              geometry_precision=None,
                              out_wkid=None,
                              gdb_version=None,
                              return_z=False,
                              return_m=False):
        """
           The Query operation is performed on a feature service layer
           resource. The result of this operation are feature sets grouped
           by source layer/table object IDs. Each feature set contains
           Feature objects including the values for the fields requested by
           the user. For related layers, if you request geometry
           information, the geometry of each feature is also returned in
           the feature set. For related tables, the feature set does not
           include geometries.
           Inputs:
              objectIds - the object IDs of the table/layer to be queried
              relationshipId - The ID of the relationship to be queried.
              outFields - the list of fields from the related table/layer
                          to be included in the returned feature set. This
                          list is a comma delimited list of field names. If
                          you specify the shape field in the list of return
                          fields, it is ignored. To request geometry, set
                          returnGeometry to true.
                          You can also specify the wildcard "*" as the
                          value of this parameter. In this case, the result
                          s will include all the field values.
              definitionExpression - The definition expression to be
                                     applied to the related table/layer.
                                     From the list of objectIds, only those
                                     records that conform to this
                                     expression are queried for related
                                     records.
              returnGeometry - If true, the feature set includes the
                               geometry associated with each feature. The
                               default is true.
              maxAllowableOffset - This option can be used to specify the
                                   maxAllowableOffset to be used for
                                   generalizing geometries returned by the
                                   query operation. The maxAllowableOffset
                                   is in the units of the outSR. If outSR
                                   is not specified, then
                                   maxAllowableOffset is assumed to be in
                                   the unit of the spatial reference of the
                                   map.
              geometryPrecision - This option can be used to specify the
                                  number of decimal places in the response
                                  geometries.
              outWKID - The spatial reference of the returned geometry.
              gdbVersion - The geodatabase version to query. This parameter
                           applies only if the isDataVersioned property of
                           the layer queried is true.
              returnZ - If true, Z values are included in the results if
                        the features have Z values. Otherwise, Z values are
                        not returned. The default is false.
              returnM - If true, M values are included in the results if
                        the features have M values. Otherwise, M values are
                        not returned. The default is false.
        """
        params = {
            "f": "json",
            "objectIds": object_ids,
            "relationshipId": relationship_id,
            "outFields": out_fields,
            "returnGeometry": return_geometry,
            "returnM": return_m,
            "returnZ": return_z
        }
        if gdb_version is not None:
            params['gdbVersion'] = gdb_version
        if definition_expression is not None:
            params['definitionExpression'] = definition_expression
        if out_wkid is not None and \
                isinstance(out_wkid, SpatialReference):
            params['outSR'] = out_wkid
        elif out_wkid is not None and \
                isinstance(out_wkid, dict):
            params['outSR'] = out_wkid
        if max_allowable_offset is not None:
            params['maxAllowableOffset'] = max_allowable_offset
        if geometry_precision is not None:
            params['geometryPrecision'] = geometry_precision
        qrr_url = self._url + "/queryRelatedRecords"
        return self._con.get(path=qrr_url, params=params, token=self._token)

    # ----------------------------------------------------------------------
    def get_html_popup(self, oid):
        """
           The htmlPopup resource provides details about the HTML pop-up
           authored by the user using ArcGIS for Desktop.
           Input:
              oid - object id of the feature where the HTML pop-up
           Output:

        """
        if self.properties.htmlPopupType != "esriServerHTMLPopupTypeNone":
            pop_url = self._url + "/%s/htmlPopup" % oid
            params = {
                'f': "json"
            }

            return self._con.get(path=pop_url, params=params, token=self._token)
        return ""

    # ----------------------------------------------------------------------
    def delete_features(self,
                        deletes=None,
                        where=None,
                        geometry_filter=None,
                        gdb_version=None,
                        rollback_on_failure=True):
        """
           This operation deletes features in a feature layer or table
           Inputs:
              deletes - string of OIDs to remove from service
              where -  A where clause for the query filter.
                       Any legal SQL where clause operating on the fields in
                       the layer is allowed. Features conforming to the specified
                       where clause will be deleted.
              geometry_filter - spatial filter from arcgis.geometry.filters module to filter results by a
                                spatial relationship with another geometry
              gdb_version - Geodatabase version to apply the edits.
              rollback_on_failure - Optional parameter to specify if the
                                  edits should be applied only if all
                                  submitted edits succeed. If false, the
                                  server will apply the edits that succeed
                                  even if some of the submitted edits fail.
                                  If true, the server will apply the edits
                                  only if all edits succeed. The default
                                  value is true.
           Output:
              dictionary of messages
        """
        delete_url = self._url + "/deleteFeatures"
        params = {
            "f": "json",
            "rollbackOnFailure": rollback_on_failure
        }
        if gdb_version is not None:
            params['gdbVersion'] = gdb_version

        if deletes is not None and \
                isinstance(deletes, str):
            params['objectIds'] = deletes
        elif deletes is not None and \
                isinstance(deletes, PropertyMap):
            print('pass in delete, unable to convert PropertyMap to string list of OIDs')

        elif deletes is not None and \
                isinstance(deletes, FeatureSet):
            params['objectIds'] = ",".join(
                [str(feat.get_value(field_name=deletes.object_id_field_name)) for feat in deletes.features])

        if where is not None:
            params['where'] = where

        if geometry_filter is not None and \
                isinstance(geometry_filter, GeometryFilter):
            for key, val in geometry_filter.filter:
                params[key] = val
        elif geometry_filter is not None and \
                isinstance(geometry_filter, dict):
            for key, val in geometry_filter.items():
                params[key] = val

        if 'objectIds' not in params and 'where' not in params and 'geometry' not in params:
            print("Parameters not valid for delete_features")
            return None
        return self._con.post(path=delete_url, postdata=params, token=self._token)

    # ----------------------------------------------------------------------
    def edit_features(self,
                      adds=None,
                      updates=None,
                      deletes=None,
                      gdb_version=None,
                      use_global_ids=False,
                      rollback_on_failure=True):
        """
           This operation adds, updates, and deletes features to the
           associated feature layer or table in a single call.
           Inputs:
              adds - The array of features to be added.
              updates - The array of features to be updateded.
              deletes - string of OIDs to remove from service
              gdbVersion - Geodatabase version to apply the edits.
              useGlobalIds - instead of referencing the default Object ID
                              field, the service will look at a GUID field
                              to track changes.  This means the GUIDs will
                              be passed instead of OIDs for delete,
                              update or add features.
              rollbackOnFailure - Optional parameter to specify if the
                                  edits should be applied only if all
                                  submitted edits succeed. If false, the
                                  server will apply the edits that succeed
                                  even if some of the submitted edits fail.
                                  If true, the server will apply the edits
                                  only if all edits succeed. The default
                                  value is true.
           Output:
              dictionary of messages
        """
        if adds is None:
            adds = []
        if updates is None:
            updates = []
        edit_url = self._url + "/applyEdits"
        params = {
            "f": "json",
            "useGlobalIds": use_global_ids,
            "rollbackOnFailure": rollback_on_failure
        }
        if gdb_version is not None:
            params['gdbVersion'] = gdb_version
        if isinstance(adds, FeatureSet):
            params['adds'] = json.dumps([f.as_dict for f in adds.features],
                                        default=_date_handler)
        elif len(adds) > 0:
            if isinstance(adds[0], dict):
                params['adds'] = json.dumps([f for f in adds],
                                            default=_date_handler)
            elif isinstance(adds[0], PropertyMap):
                params['adds'] = json.dumps([dict(f) for f in adds],
                                            default=_date_handler)
            elif isinstance(adds[0], Feature):
                params['adds'] = json.dumps([f.as_dict for f in adds],
                                               default=_date_handler)
            else:
                print('pass in features as list of Features, dicts or PropertyMap')
        if isinstance(updates, FeatureSet):
            params['updates'] = json.dumps([f.as_dict for f in updates.features],
                                           default=_date_handler)
        elif len(updates) > 0:
            if isinstance(updates[0], dict):
                params['updates'] = json.dumps([f for f in updates],
                                               default=_date_handler)
            elif isinstance(updates[0], PropertyMap):
                params['updates'] = json.dumps([dict(f) for f in updates],
                                               default=_date_handler)
            elif isinstance(updates[0], Feature):
                params['updates'] = json.dumps([f.as_dict for f in updates],
                                               default=_date_handler)
            else:
                print('pass in features as list of Features, dicts or PropertyMap')
        if deletes is not None and \
                isinstance(deletes, str):
            params['deletes'] = deletes
        elif deletes is not None and \
                isinstance(deletes, PropertyMap):
            print('pass in delete, unable to convert PropertyMap to string list of OIDs')

        elif deletes is not None and \
                isinstance(deletes, FeatureSet):
            params['deletes'] = ",".join(
                [str(feat.get_value(field_name=deletes.object_id_field_name)) for feat in deletes.features])

        if 'deletes' not in params and 'updates' not in params and 'adds' not in params:
            print("Parameters not valid for edit_features")
            return None
        return self._con.post(path=edit_url, postdata=params, token=self._token)

    # ----------------------------------------------------------------------
    def calculate(self, where, calc_expression, sql_format="standard"):
        """
        The calculate operation is performed on a feature layer
        resource. It updates the values of one or more fields in an
        existing feature service layer based on SQL expressions or scalar
        values. The calculate operation can only be used if the
        supportsCalculate property of the layer is true.
        Neither the Shape field nor system fields can be updated using
        calculate. System fields include ObjectId and GlobalId.
        See Calculate a field for more information on supported expressions

        Inputs:
           where - A where clause can be used to limit the updated records.
                   Any legal SQL where clause operating on the fields in
                   the layer is allowed.
           calcExpression - The array of field/value info objects that
                            contain the field or fields to update and their
                            scalar values or SQL expression.  Allowed types
                            are dictionary and list.  List must be a list
                            of dictionary objects.
                            Calculation Format is as follows:
                               {"field" : "<field name>",
                               "value" : "<value>"}
           sqlFormat - The SQL format for the calcExpression. It can be
                       either standard SQL92 (standard) or native SQL
                       (native). The default is standard.
                       Values: standard, native
        Output:
           JSON as string
        Usage:
        >>>print(fl.calculate(where="OBJECTID < 2",
                              calcExpression={"field": "ZONE",
                                              "value" : "R1"}))
        {'updatedFeatureCount': 1, 'success': True}
        """
        url = self._url + "/calculate"
        params = {
            "f": "json",
            "where": where,

        }
        if isinstance(calc_expression, dict):
            params["calcExpression"] = json.dumps([calc_expression],
                                                  default=_date_handler)
        elif isinstance(calc_expression, list):
            params["calcExpression"] = json.dumps(calc_expression,
                                                  default=_date_handler)
        if sql_format.lower() in ['native', 'standard']:
            params['sqlFormat'] = sql_format.lower()
        else:
            params['sqlFormat'] = "standard"
        return self._con.post(path=url,
                              postdata=params, token=self._token)

    # ----------------------------------------------------------------------
    def _query(self, url, params):
        """ returns results of query """
        result = self._con.post(path=url,
                                postdata=params, token=self._token)
        if 'error' in result:
            raise ValueError(result)

        if  params['returnCountOnly']:
            return result['count']
        elif params['returnIdsOnly']:
            return result
        else:
            return FeatureSet.from_dict(result)


class Table(FeatureLayer):
    """
    Tables represent entity classes with uniform properties. In addition to working with "entities with location" as
    features, the GIS can also work with non-spatial entities as rows in tables.

    Working with tables is similar to working with feature layers, except that the rows (Features) in a table do not
    have a geometry, and tables ignore any geometry related operation.
    """
    pass


class FeatureLayerCollection(_GISResource):
    """
    A FeatureLayerCollection is a collection of feature layers and tables, with the associated relationships among the entities.

    In a web GIS, a feature layer collection is exposed as a feature service with multiple feature layers.

    Instances of FeatureDatasets can be obtained from feature service Items in the GIS using
    `FeatureLayerCollection.fromitem(item)`, from feature service endpoints using the constructor, or by accessing the `dataset`
    attribute of feature layer objects.

    FeatureDatasets can be configured and managed using their `manager` helper object.

    If the dataset supports the sync operation, the `replicas` helper object allows management and synchronization of
    replicas for disconnected editing of the feature layer collection.

    Note: You can use the `layers` and `tables` property to get to the individual layers and tables in this
    feature layer collection.
    """

    def __init__(self, url, gis=None):
        super(FeatureLayerCollection, self).__init__(url, gis)

        try:
            if self.properties.syncEnabled:
                self.replicas = SyncManager(self)
        except AttributeError:
            pass

        self._populate_layers()
        self._admin = None
        try:
            from .._impl._server._service._adminfactory import AdminServiceGen
            self.service = AdminServiceGen(service=self, gis=gis)
        except: pass

    def _populate_layers(self):
        """
        populates the layers and tables for this feature service
        """
        layers = []
        tables = []

        for lyr in self.properties.layers:
            lyr = FeatureLayer(self.url + '/' + str(lyr.id), self._gis, self)
            layers.append(lyr)

        for lyr in self.properties.tables:
            lyr = Table(self.url + '/' + str(lyr.id), self._gis, self)
            tables.append(lyr)

        # fsurl = self.url + '/layers'
        # params = { "f" : "json" }
        # allayers = self._con.post(fsurl, params, token=self._token)

        # for layer in allayers['layers']:
        #    layers.append(FeatureLayer(self.url + '/' + str(layer['id']), self._gis))

        # for table in allayers['tables']:
        #    tables.append(FeatureLayer(self.url + '/' + str(table['id']), self._gis))

        self.layers = layers
        self.tables = tables

    @property
    def manager(self):
        """ helper object to manage the feature layer collection, update it's definition, etc """
        if self._admin is None:
            url = self._url
            res = search("/rest/", url).span()
            add_text = "admin/"
            part1 = url[:res[1]]
            part2 = url[res[1]:]
            admin_url = "%s%s%s" % (part1, add_text, part2)

            self._admin = FeatureLayerCollectionManager(admin_url, self._gis, self)
        return self._admin

    def query(self,
              layer_defs_filter=None,
              geometry_filter=None,
              time_filter=None,
              return_geometry=True,
              return_ids_only=False,
              return_count_only=False,
              return_z=False,
              return_m=False,
              out_sr=None):
        """
           queries the feature layer collection
        """
        qurl = self._url + "/query"
        params = {"f": "json",
                  "returnGeometry": return_geometry,
                  "returnIdsOnly": return_ids_only,
                  "returnCountOnly": return_count_only,
                  "returnZ": return_z,
                  "returnM": return_m}
        if layer_defs_filter is not None and \
                isinstance(layer_defs_filter, dict):
            params['layerDefs'] = layer_defs_filter
        elif layer_defs_filter is not None and \
                isinstance(layer_defs_filter, dict):
            pass
        if geometry_filter is not None and \
                isinstance(geometry_filter, dict):
            params['geometryType'] = geometry_filter['geometryType']
            params['spatialRel'] = geometry_filter['spatialRel']
            params['geometry'] = geometry_filter['geometry']
            if 'inSR' in geometry_filter:
                params['inSR'] = geometry_filter['inSR']

        if out_sr is not None and \
                isinstance(out_sr, SpatialReference):
            params['outSR'] = out_sr
        elif out_sr is not None and \
                isinstance(out_sr, dict):
            params['outSR'] = out_sr
        if time_filter is not None and \
                isinstance(time_filter, dict):
            params['time'] = time_filter
        results = self._con.get(path=qurl,
                                params=params, token=self._token)
        if 'error' in results:
            raise ValueError(results)
        if not return_count_only and not return_ids_only:
            return results
            # if returnFeatureClass == True:
            # json_text = json.dumps(results)
            # return results
            # df = json_normalize(results['features'])
            # df.columns = df.columns.str.replace('attributes.', '')
            # return df
            # else:
            #    return results
            # df = json_normalize(results['features'])
            # df.columns = df.columns.str.replace('attributes.', '')
            # return df
        else:
            return FeatureSet.from_dict(results)

    # ----------------------------------------------------------------------
    def query_related_records(self,
                              object_ids,
                              relationship_id,
                              out_fields="*",
                              definition_expression=None,
                              return_geometry=True,
                              max_allowable_offset=None,
                              geometry_precision=None,
                              out_wkid=None,
                              gdb_version=None,
                              return_z=False,
                              return_m=False):
        """
           The Query operation is performed on a feature service layer
           resource. The result of this operation are feature sets grouped
           by source layer/table object IDs. Each feature set contains
           Feature objects including the values for the fields requested by
           the user. For related layers, if you request geometry
           information, the geometry of each feature is also returned in
           the feature set. For related tables, the feature set does not
           include geometries.
           Inputs:
              objectIds - the object IDs of the table/layer to be queried
              relationshipId - The ID of the relationship to be queried.
              outFields - the list of fields from the related table/layer
                          to be included in the returned feature set. This
                          list is a comma delimited list of field names. If
                          you specify the shape field in the list of return
                          fields, it is ignored. To request geometry, set
                          returnGeometry to true.
                          You can also specify the wildcard "*" as the
                          value of this parameter. In this case, the result
                          s will include all the field values.
              definitionExpression - The definition expression to be
                                     applied to the related table/layer.
                                     From the list of objectIds, only those
                                     records that conform to this
                                     expression are queried for related
                                     records.
              returnGeometry - If true, the feature set includes the
                               geometry associated with each feature. The
                               default is true.
              maxAllowableOffset - This option can be used to specify the
                                   maxAllowableOffset to be used for
                                   generalizing geometries returned by the
                                   query operation. The maxAllowableOffset
                                   is in the units of the outSR. If outSR
                                   is not specified, then
                                   maxAllowableOffset is assumed to be in
                                   the unit of the spatial reference of the
                                   map.
              geometryPrecision - This option can be used to specify the
                                  number of decimal places in the response
                                  geometries.
              outWKID - The spatial reference of the returned geometry.
              gdbVersion - The geodatabase version to query. This parameter
                           applies only if the isDataVersioned property of
                           the layer queried is true.
              returnZ - If true, Z values are included in the results if
                        the features have Z values. Otherwise, Z values are
                        not returned. The default is false.
              returnM - If true, M values are included in the results if
                        the features have M values. Otherwise, M values are
                        not returned. The default is false.
        """
        params = {
            "f": "json",
            "objectIds": object_ids,
            "relationshipId": relationship_id,
            "outFields": out_fields,
            "returnGeometry": return_geometry,
            "returnM": return_m,
            "returnZ": return_z
        }
        if gdb_version is not None:
            params['gdbVersion'] = gdb_version
        if definition_expression is not None:
            params['definitionExpression'] = definition_expression
        if out_wkid is not None and \
                isinstance(out_wkid, SpatialReference):
            params['outSR'] = out_wkid
        elif out_wkid is not None and \
                isinstance(out_wkid, dict):
            params['outSR'] = out_wkid
        if max_allowable_offset is not None:
            params['maxAllowableOffset'] = max_allowable_offset
        if geometry_precision is not None:
            params['geometryPrecision'] = geometry_precision
        qrr_url = self._url + "/queryRelatedRecords"
        res = self._con.get(path=qrr_url, params=params, token=self._token)
        return res

    # ----------------------------------------------------------------------
    @property
    def _replicas(self):
        """ returns all the replicas for a feature service """
        params = {
            "f": "json",

        }
        url = self._url + "/replicas"
        return self._con.get(path=url, params=params, token=self._token)

    # ----------------------------------------------------------------------
    def _unregister_replica(self, replica_id):
        """
           removes a replica from a feature service
           Inputs:
             replica_id - The replicaID returned by the feature service
                          when the replica was created.
        """
        params = {
            "f": "json",
            "replicaID": replica_id
        }
        url = self._url + "/unRegisterReplica"
        return self._con.post(path=url, postdata=params, token=self._token)

    # ----------------------------------------------------------------------
    def _replica_info(self, replica_id):
        """
           The replica info resources lists replica metadata for a specific
           replica.
           Inputs:
              replica_id - The replicaID returned by the feature service
                           when the replica was created.
        """
        params = {
            "f": "json"
        }
        url = self._url + "/replicas/" + replica_id
        return self._con.get(path=url, params=params, token=self._token)

    # ----------------------------------------------------------------------
    def _create_replica(self,
                        replica_name,
                        layers,
                        layer_queries=None,
                        geometry_filter=None,
                        replica_sr=None,
                        transport_type="esriTransportTypeUrl",
                        return_attachments=False,
                        return_attachments_data_by_url=False,
                        asynchronous=False,
                        sync_direction=None,
                        target_type="client",
                        attachments_sync_direction="none",
                        sync_model="none",
                        data_format="json",
                        replica_options=None,
                        wait=False,
                        out_path=None):
        """
        The createReplica operation is performed on a feature service
        resource. This operation creates the replica between the feature
        service and a client based on a client-supplied replica definition.
        It requires the Sync capability. See Sync overview for more
        information on sync. The response for createReplica includes
        replicaID, server generation number, and data similar to the
        response from the feature service query operation.
        The createReplica operation returns a response of type
        esriReplicaResponseTypeData, as the response has data for the
        layers in the replica. If the operation is called to register
        existing data by using replicaOptions, the response type will be
        esriReplicaResponseTypeInfo, and the response will not contain data
        for the layers in the replica.

        Inputs:
           replicaName - name of the replica
           layers - layers to export
           layerQueries - In addition to the layers and geometry parameters, the layerQueries
            parameter can be used to further define what is replicated. This
            parameter allows you to set properties on a per layer or per table
            basis. Only the properties for the layers and tables that you want
            changed from the default are required.
            Example:
             layerQueries = {"0":{"queryOption": "useFilter", "useGeometry": true,
             "where": "requires_inspection = Yes"}}
           geometry_filter - spatial filter from arcgis.geometry.filters module to filter results by a
                             spatial relationship with another geometry
           returnAttachments - If true, attachments are added to the replica and returned in the
            response. Otherwise, attachments are not included.
           returnAttachmentDatabyURL -  If true, a reference to a URL will be provided for each
            attachment returned from createReplica. Otherwise,
            attachments are embedded in the response.
           replicaSR - the spatial reference of the replica geometry.
           transportType -  The transportType represents the response format. If the
            transportType is esriTransportTypeUrl, the JSON response is contained in a file,
            and the URL link to the file is returned. Otherwise, the JSON object is returned
            directly. The default is esriTransportTypeUrl.
            If async is true, the results will always be returned as if transportType is
            esriTransportTypeUrl. If dataFormat is sqlite, the transportFormat will always be
            esriTransportTypeUrl regardless of how the parameter is set.
            Values: esriTransportTypeUrl | esriTransportTypeEmbedded
           returnAttachments - If true, attachments are added to the replica and returned in
            the response. Otherwise, attachments are not included. The default is false. This
            parameter is only applicable if the feature service has attachments.
           returnAttachmentsDatabyURL -  If true, a reference to a URL will be provided for
            each attachment returned from createReplica. Otherwise, attachments are embedded
            in the response. The default is true. This parameter is only applicable if the
            feature service has attachments and if returnAttachments is true.
           attachmentsSyncDirection - Client can specify the attachmentsSyncDirection when
            creating a replica. AttachmentsSyncDirection is currently a createReplica property
            and cannot be overridden during sync.
            Values: none, upload, bidirectional
           asynchronous - If true, the request is processed as an asynchronous job, and a URL is
            returned that a client can visit to check the status of the job. See the topic on
            asynchronous usage for more information. The default is false.
           syncModel - Client can specify the attachmentsSyncDirection when creating a replica.
            AttachmentsSyncDirection is currently a createReplica property and cannot be
            overridden during sync.
           dataFormat - The format of the replica geodatabase returned in the response. The
            default is json.
            Values: filegdb, json, sqlite, shapefile
           target_type - This option was added at 10.5.1. Can be set to either server or client.
            If not set, the default is client.A targetType of client will generate a replica that
            matches those generated in pre-10.5.1 releases. These are designed to support syncing
            with lightweight mobile clients and have a single generation number (serverGen or
            replicaServerGen).
            A targetType of server generates a replica that supports syncing in one direction
            between 2 feature services running on servers or between an ArcGIS Server feature
            service and an ArcGIS Online feature service. When the targetType is server, the replica
            information includes a second generation number. This second generation number is called
            replicaServerSibGen for perReplica types and serverSibGen for perLayer types.
            target_type server replicas generated with dataFormat SQLite can be published as new
            services in another ArcGIS Online organization or in ArcGIS Enterprise. When published,
            a replica is generated on these new services with a matching replicaID and a
            replicaServerSibGen or serverSibGens. The replicaServerSibGen or serverSibGens values
            can be used as the replicaServerGen or serverGen values when calling synchronize replica
            on the source service to get the latest changes. These changes can then be imported into
            the new service using the synchronizeReplica operation. When calling synchronizeReplica
            on the new service to import the changes, be sure to pass the new replicaServerGen or
            serverGen from the source service as the replicaServerSibGen or serverSibGen. This will
            update the replica metadata appropriately such that it can be used in the next sync.
            Values: server, client
           sync_direction - Defaults to bidirectional when the targetType is client and download
            when the targetType is server. If set, only bidirectional is supported when
            targetType is client. If set, only upload or download are supported when targetType is
            server.
            A syncDirection of bidirectional matches the functionality from replicas generated in
            pre-10.5.1 releases and allows upload and download of edits. It is only supported
            when targetType is client.
            When targetType is server, only a one way sync is supported thus only upload or
            download are valid options.
            A syncDirection of upload means that the synchronizeReplica operation allows only sync
            with an upload direction. Use this option to allow the upload of edits from the source
            service.
            A syncDirection of download means that the synchronizeReplica operation allows only sync
            with a download direction. Use this option to allow the download of edits to provide to
            the source service.
           replicaOptions - This parameter instructs the createReplica operation to create a
            new replica based on an existing replica definition (refReplicaId). It can be used
            to specify parameters for registration of existing data for sync. The operation
            will create a replica but will not return data. The responseType returned in the
            createReplica response will be esriReplicaResponseTypeInfo.
           wait - if async, wait to pause the process until the async operation is completed.
           out_path - folder path to save the file
        """
        if not self.properties.syncEnabled and "Extract" not in self.properties.capabilities:
            return None
        url = self._url + "/createReplica"
        dataformat = ["filegdb", "json", "sqlite", "shapefile"]
        params = {
            "f": "json",
            "replicaName": replica_name,
            "returnAttachments": json.dumps(return_attachments),
            "returnAttachmentsDatabyUrl": json.dumps(return_attachments_data_by_url),
            "async": json.dumps(asynchronous),
            "syncModel": sync_model,
            "layers": layers,
            "targetType" : target_type,

        }
        if attachments_sync_direction:
            params["attachmentsSyncDirection"] = attachments_sync_direction
        if sync_direction:
            params['syncDirection'] = sync_direction
        if data_format.lower() in dataformat:
            params['dataFormat'] = data_format.lower()
        else:
            raise Exception("Invalid dataFormat")
        if layer_queries is not None:
            params['layerQueries'] = layer_queries
        if geometry_filter is not None and \
                isinstance(geometry_filter, dict):
            params['geometry'] = geometry_filter
            #params.update(geometry_filter)
        if replica_sr is not None:
            params['replicaSR'] = replica_sr
        if replica_options is not None:
            params['replicaOptions'] = replica_options
        if transport_type is not None:
            params['transportType'] = transport_type

        if asynchronous:
            if wait:
                export_job = self._con.post(path=url, postdata=params, token=self._token)
                status = self._replica_status(url=export_job['statusUrl'])
                while status['status'] not in ("Completed", "CompletedWithErrors"):
                    if status['status'] == "Failed":
                        return status
                    # wait before checking again
                    time.sleep(2)
                    status = self._replica_status(url=export_job['statusUrl'])

                res = status

            else:
                res = self._con.post(path=url, postdata=params, token=self._token)
        else:
            res = self._con.post(path=url, postdata=params, token=self._token)

        if out_path is not None and \
                os.path.isdir(out_path):
            dl_url = None
            if 'resultUrl' in res:

                dl_url = res["resultUrl"]
            elif 'responseUrl' in res:
                dl_url = res["responseUrl"]

            if dl_url is not None:

                return self._con.get(path=dl_url, file_name=dl_url.split('/')[-1],
                                     out_folder=out_path, try_json=False, token=self._token)

            else:
                return res
        elif res is not None:
            return res
        return None

    # ----------------------------------------------------------------------
    #TODO: FIX PARAMETERS
    #TODO: FIGURE OUT LAST PART WITH syncLayers
    def _synchronize_replica(self,
                             replica_id,
                             transport_type="esriTransportTypeUrl",
                             replica_server_gen=None,
                             replica_servers_sib_gen=None,
                             return_ids_for_adds=False,
                             edits=None,
                             return_attachment_databy_url=False,
                             asynchronous=False,
                             sync_direction=None,
                             sync_layers="perReplica",
                             edits_upload_id=None,
                             edits_upload_format=None,
                             data_format="json",
                             rollback_on_failure=True,
                             close_replica=False,
                             out_path=None):
        """
        The synchronizeReplica operation is performed on a feature service resource. This operation
        synchronizes changes between the feature service and a client based on the replicaID
        provided by the client. Requires the sync capability. See Sync overview for more information
        on sync.
        The client obtains the replicaID by first calling the _create_replica operation.
        Synchronize applies the client's data changes by importing them into the server's
        geodatabase. It then exports the changes from the server geodatabase that have taken place
        since the last time the client got the data from the server. Edits can be supplied in the
        edits parameter, or, alternatively, by using the editsUploadId and editUploadFormat to
        identify a file containing the edits that were previously uploaded using the upload_item
        operation.
        The response for this operation includes the replicaID, new replica generation number, or
        the layer's generation numbers. The response has edits or layers according to the
        syncDirection/syncLayers. Presence of layers and edits in the response is indicated by the
        responseType.
        If the responseType is esriReplicaResponseTypeEdits or esriReplicaResponseTypeEditsAndData,
        the result of this operation can include arrays of edit results for each layer/table edited
        as specified in edits. Each edit result identifies a single feature on a layer or table and
        indicates if the edits were successful or not. If an edit is not successful, the edit result
        also includes an error code and an error description.
        If syncModel is perReplica and syncDirection is download or bidirectional, the
        _synchronize_replica operation's response will have edits. If syncDirection is snapshot, the
        response will have replacement data.
        If syncModel is perLayer, and syncLayers have syncDirection as download or bidirectional,
        the response will have edits. If syncLayers have syncDirection as download or bidirectional
        for some layers and snapshot for some other layers, the response will have edits and data.
        If syncDirection for all the layers is snapshot, the response will have replacement data.
        When syncModel is perReplica, the createReplica and synchronizeReplica operations' responses
        contain replicaServerGen. When syncModel is perLayer, the createReplica and
        synchronizeReplica operations' responses contain layerServerGens.
        You can provide arguments to the synchronizeReplica operation as defined in the parameters
        table below.

        Parameters:
         :replica_id: The ID of the replica you want to synchronize.
         :transport_type:
         :replica_server_gen: is a generation number that allows the server to keep track of what
          changes have already been synchronized. A new replicaServerGen is sent with the response
          to the synchronizeReplica operation. Clients should persist this value and use it with the
          next synchronizeReplica call.
          It applies to replicas with syncModel = perReplica.
          For replicas with syncModel = perLayer, layer generation numbers are specified using
          parameter: syncLayers; and replicaServerSibGen is not needed.
         :replica_servers_sib_gen:  is a generation number that allows the server to keep track of
          what changes have already been received. It is set when synchronizing where
          syncModel = perReplica and targetType = server. The replicaServerSibGen is updated in the
          replica metadata on the replica resource once the process completes successfully.
          Replicas with targetType = server are designed to allow syncing between services. When
          syncing, the replicaServerSibGen value is derived from the replicaServerGen of the other
          services matching replica.
          For replicas with syncModel = perLayer, layer generation numbers are specified using
          parameter: syncLayers; and replicaServerGen is not needed.
          This value is not set for replicas where the targetType=client.
         :return_ids_for_adds: If true, the objectIDs and globalIDs of features added during the
          synchronize will be returned to the client in the addResults sections of the response.
          Otherwise, the IDs are not returned. The default is false.
          Values: true | false
         :edits: The edits the client wants to apply to the service. Alternatively, the
          edits_upload_ID and editsUploadFormat can be used to specify the edits in a delta file.
          The edits are described using an array where an element in the array includes:
           - The layer or table ID
           - The feature or row edits to apply listed as inserts, updates, and deletes
           - The attachments to apply listed as inserts, updates, and deletes
         For features, adds and updates are specified as feature objects that include geometry and
         attributes.
         Deletes can be specified using globalIDs for features and attachments.
         For attachments, updates and adds are specified using the following set of properties for
         each attachment. If embedding the attachment, set the data property; otherwise, set the url
         property. All other properties are required:
          - globalid - The globalID of the attachment that is to be added or updated.
          - parentGlobalid - The globalID of the feature associated with the attachment.
          - contentType - Describes the file type of the attachment (for example, image/jpeg).
          - name - The file name (for example, hydrant.jpg).
          - data - The base 64 encoded data if embedding the data. Only required if the attachment
            is embedded.
          - url - The location where the service will upload the attachment file (for example,
            http://machinename/arcgisuploads/Hydrant.jpg). Only required if the attachment is not
            embedded.
         :return_attachment_databy_url:  If true, a reference to a URL will be provided for each
          attachment returned from synchronizeReplica. Otherwise, attachments are embedded in the
          response. The default is true. Applies only if attachments are included in the replica.
          Values: true | false
         :asynchronous: If true, the request is processed as an asynchronous job and a URL is
          returned that a client can visit to check the status of the job. See the topic on
          asynchronous usage for more information. The default is false.
          Values: true | false
         :sync_direction: Determines whether to upload, download, or upload and download on sync. By
          default, a replica is synchronized bi-directionally. Only applicable when
          syncModel = perReplica. If syncModel = perLayer, sync direction is specified using
          syncLayers.
          Values: download | upload | bidirectional | snapshot

           - download-The changes that have taken place on the server since last download are
             returned. Client does not need to send any changes. If the changes are sent, service
             will ignore them.
           - upload-The changes submitted in the edits or editsUploadID/editsUploadFormatt
             parameters are applied, and no changes are downloaded from the server.
           - bidirectional-The changes submitted in the edits or editsUploadID/editsUploadFormat
             parameters are applied, and changes on the server are downloaded. This is the default
             value.
           - snapshot-The current state of the features is downloaded from the server. If any edits
             are specified, they will be ignored.
         :sync_layers:  allows a client to specify layer-level generation numbers for a sync
          operation. It can also be used to specify sync directions at layer-level. This parameter
          is needed for replicas with syncModel = perLayer. It is ignored for replicas with
          syncModel = perReplica.
          serverGen is required for layers with syncDirection = bidirectional or download.
          serverSibGen is needed only for replicas where the targetType = server. For replicas with
          syncModel = perLayer, the serverSibGen serves the same purpose at the layer level as the
          replicaServerSibGen does in the case of syncModel = perReplica. See the
          replicaServerSibGen parameter for more information.
          If a sync operation has both the syncDirection and syncLayersparameters, and the replica's
          syncModel is perLayer, the layers that do not have syncDirection values will use the value
          of the syncDirection parameter. If the syncDirection parameter is not specified, the
          default value of bidirectional is used.
          Values: download | upload | bidirectional | snapshot
         :edits_upload_id: The ID for the uploaded item that contains the edits the client wants to
          apply to the service. Used in conjunction with editsUploadFormat.
         :edits_upload_format: The data format of the uploaded data reference in edit_upload_id.
          data_format="json",
         :rollback_on_failure:  Determines the behavior when there are errors while importing edits
          on the server during synchronization. This only applies in cases where edits are being
          uploaded to the server (syncDirection = upload or bidirectional). See the
          RollbackOnFailure and Sync Models topic for more details.
          When true, if an error occurs while importing edits on the server, all edits are rolled
          back (not applied), and the operation returns an error in the response. Use this setting
          when the edits are such that you will either want all or none applied.
          When false, if an error occurs while importing an edit on the server, the import process
          skips the edit and continues. All edits that were skipped are returned in the edits
          results with information describing why the edits were skipped.
         :close_replica:  If true, the replica will be unregistered when the synchronize completes.
          This is the same as calling synchronize and then calling unregisterReplica. Otherwise, the
          replica can continue to be synchronized. The default is false.
          Values: true | false
        """
        url = "{url}/synchronizeReplica".format(url=self._url)
        params = {
            "f": "json",
            "replicaID": replica_id,
        }

        if transport_type is not None:
            params['transportType'] = transport_type
        if edits is not None:
            params['edits'] = edits
        if replica_server_gen is not None:
            params['replicaServerGen'] = replica_server_gen
        if return_ids_for_adds is not None:
            params['returnIdsForAdds'] = return_ids_for_adds
        if return_attachment_databy_url is not None:
            params['returnAttachmentDatabyURL'] = return_attachment_databy_url
        if asynchronous is not None:
            params['async'] = asynchronous
        if sync_direction is not None:
            params['syncDirection'] = sync_direction
        if sync_layers is not None:
            params['syncLayers'] = sync_layers
        if edits_upload_format is not None:
            params['editsUploadFormat'] = edits_upload_format
        if edits_upload_id is not None:
            params['editsUploadID'] = edits_upload_id
        if data_format is not None:
            params['dataFormat'] = data_format
        #if edits_upload_id:
        #    params['dataFormat'] = edits_upload_id
        if rollback_on_failure is not None:
            params['rollbackOnFailure'] = rollback_on_failure
        if close_replica:
            params['closeReplica'] = close_replica
        if replica_servers_sib_gen:
            params['replicaServerSibGen'] = replica_servers_sib_gen
        res = self._con.post(path=url, postdata=params, token=self._token)
        if out_path is not None and \
               os.path.isdir(out_path):
            dl_url = None
            if 'resultUrl' in res:
                dl_url = res["resultUrl"]
            elif 'responseUrl' in res:
                dl_url = res["responseUrl"]
            if dl_url is not None:
                return self._con.get(path=dl_url, file_name=dl_url.split('/')[-1],
                                     out_folder=out_path, try_json=False,
                                     token=self._token)
            else:
                return res
        return res

    # ----------------------------------------------------------------------
    def _replica_status(self, url):
        """gets the replica status when exported async set to True"""
        params = {"f": "json"}
        url += "/status"
        return self._con.get(path=url,
                             params=params, token=self._token)

    #----------------------------------------------------------------------
    def upload(self, path, description=None):
        """
        Uploads a new item to the server. Once the operation is completed
        successfully, the JSON structure of the uploaded item is returned.

        Parameters:
         :path: path of the file to upload
         :description: optional descriptive text for the upload item
        """
        url = self._url + "/uploads/upload"
        params = {
            "f" : "json",
            'filename' : os.path.basename(path),
            'overwrite' : True
        }
        files = {}
        files['file'] = path
        if description:
            params['description'] = description
        res = self._con.post(path=url,
                             postdata=params,
                             files=files)
        if 'status' in res and \
           res['status'] == 'success':
            return True, res
        elif 'success' in res:
            return res['success'], res
        return False, res