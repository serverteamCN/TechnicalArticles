"""
The arcgis.tools module is used for consuming the GIS functionality exposed from ArcGIS Online
or Portal web services. It has implementations for Spatial Analysis tools, GeoAnalytics tools,
Raster Analysis tools, Geoprocessing tools, Geocoders and Geometry Utility services.
These tools primarily operate on items and layers from the GIS.
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import json
import logging
import os
import sys
import random
import string
import tempfile
import time
from contextlib import contextmanager

import arcgis
import arcgis.gis
from arcgis.gis import Item
from arcgis._impl.common._mixins import PropertyMap
from arcgis._impl.common._utils import _DisableLogger
from arcgis.geocoding import Geocoder
from arcgis.geometry import Point, MultiPoint, Polygon, Envelope, Polyline, Geometry
from arcgis.features import Feature, FeatureSet, FeatureCollection

_log = logging.getLogger(__name__)


__all__ = ['_GeoanalyticsTools', '_FeatureAnalysisTools', '_GeometryService', '_RasterAnalysisTools']


class _GISService(object):
    """ a GIS service
    """
    def __init__(self, url, gis=None):
        self._token = None

        self.url = url
        self._url = url

        err = None

        if gis is None:
            gis = arcgis.gis.GIS(set_active=False)
            self._gis = gis
            self._con = gis._con
            self._token = None
        else:
            self._gis = gis
            self._con = gis._con

        with _DisableLogger():
            try:
                # try as a federated server
                if isinstance(self._con, arcgis._impl._ArcGISConnection):
                    self._token = self._con.generate_portal_server_token(url)
                else:
                    self._token = self._con.token
                self._refresh()
            except RuntimeError as e:
                try:
                    # try as a public server
                    self._token = None
                    self._refresh()
                except HTTPError as httperror:
                    _log.error(httperror)
                    err = httperror
                except RuntimeError as e:
                    if 'Token Required' in e.args[0]:
                        # try token in the provided gis
                        self._token = self._con.token
                        self._refresh()

        if err is not None:
            raise RuntimeError('HTTPError: this service url encountered an HTTP Error: ' + self.url)

    def _refresh(self):
        params = {"f": "json"}
        dictdata = self._con.post(self.url, params, token=self._token)
        self.properties = PropertyMap(dictdata)

    def __str__(self):
        return '<%s url:"%s">' % (type(self).__name__, self.url)

    def __repr__(self):
        return '<%s url:"%s">' % (type(self).__name__, self.url)

    def invoke(self, method, **kwargs):
        """Invokes the specified method on this service passing in parameters from the kwargs name-value pairs"""
        url = self._url + "/" + method
        params = { "f" : "json"}
        if len(kwargs) > 0:
            for k,v in kwargs.items():
                params[k] = v
                del k,v
        return self._con.post(path=url, postdata=params, token=self._token)

def _id_generator(size=6, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))


@contextmanager
def _tempinput(data):
    temp = tempfile.NamedTemporaryFile(delete=False)
    temp.write((bytes(data, 'UTF-8')))
    temp.close()
    yield temp.name
    os.unlink(temp.name)


class _AsyncService(_GISService):

    def __init__(self, url, gis):
        super(_AsyncService, self).__init__(url, gis)

    def _refresh(self):
        params = {"f" : "json"}
        dictdata = self._con.get(path=self.url, params=params, token=self._token)
        self.properties = PropertyMap(dictdata)

    def _analysis_job(self, task, params):
        """ Submits an Analysis job and returns the job URL for monitoring the job
            status in addition to the json response data for the submitted job."""

        # Unpack the Analysis job parameters as a dictionary and add token and
        # formatting parameters to the dictionary. The dictionary is used in the
        # HTTP POST request. Headers are also added as a dictionary to be included
        # with the POST.
        #
        #print("Submitting analysis job...")

        task_url = "{}/{}".format(self.url, task)
        submit_url = "{}/submitJob".format(task_url)

        params["f"] = "json"

        resp = self._con.post(submit_url, params, token=self._token)
        #print(resp)
        return task_url, resp

    def _analysis_job_status(self, task_url, job_info):
        """ Tracks the status of the submitted Analysis job."""

        if "jobId" in job_info:
            # Get the id of the Analysis job to track the status.
            #
            job_id = job_info.get("jobId")
            job_url = "{}/jobs/{}".format(task_url, job_id)
            params = { "f" : "json" }
            job_response = self._con.post(job_url, params, token=self._token)

            # Query and report the Analysis job status.
            #
            num_messages = 0

            if "jobStatus" in job_response:
                while not job_response.get("jobStatus") == "esriJobSucceeded":
                    time.sleep(5)

                    job_response = self._con.post(job_url, params, token=self._token)
                    #print(job_response)
                    messages = job_response['messages'] if 'messages' in job_response else []
                    num = len(messages)
                    if num > num_messages:
                        for index in range(num_messages, num):
                            msg = messages[index]
                            if arcgis.env.verbose:
                                print(msg['description'])
                            if msg['type'] == 'esriJobMessageTypeInformative':
                                _log.info(msg['description'])
                            elif msg['type'] == 'esriJobMessageTypeWarning':
                                _log.warn(msg['description'])
                            elif msg['type'] == 'esriJobMessageTypeError':
                                _log.error(msg['description'])
                                # print(msg['description'], file=sys.stderr)
                            else:
                                _log.warn(msg['description'])
                        num_messages = num

                    if job_response.get("jobStatus") == "esriJobFailed":
                        raise Exception("Job failed.")
                    elif job_response.get("jobStatus") == "esriJobCancelled":
                        raise Exception("Job cancelled.")
                    elif job_response.get("jobStatus") == "esriJobTimedOut":
                        raise Exception("Job timed out.")

                if "results" in job_response:
                    return job_response
            else:
                raise Exception("No job results.")
        else:
            raise Exception("No job url.")

    def _analysis_job_results(self, task_url, job_info):
        """ Use the job result json to get information about the feature service
            created from the Analysis job."""

        # Get the paramUrl to get information about the Analysis job results.
        #
        if "jobId" in job_info:
            job_id = job_info.get("jobId")
            if "results" in job_info:
                results = job_info.get("results")
                result_values = {}
                for key in list(results.keys()):
                    param_value = results[key]
                    if "paramUrl" in param_value:
                        param_url = param_value.get("paramUrl")
                        result_url = "{}/jobs/{}/{}".format(task_url,
                                                                            job_id,
                                                                            param_url)

                        params = { "f" : "json" }
                        param_result = self._con.post(result_url, params, token=self._token)

                        job_value = param_result.get("value")
                        result_values[key] = job_value
                return result_values
            else:
                raise Exception("Unable to get analysis job results.")
        else:
            raise Exception("Unable to get analysis job results.")

    def _feature_input(self, input_layer):

        point_fs = {
           "layerDefinition":{
              "currentVersion":10.11,
              "copyrightText":"",
              "defaultVisibility":True,
              "relationships":[

              ],
              "isDataVersioned":False,
              "supportsRollbackOnFailureParameter":True,
              "supportsStatistics":True,
              "supportsAdvancedQueries":True,
              "geometryType":"esriGeometryPoint",
              "minScale":0,
              "maxScale":0,
              "objectIdField":"OBJECTID",
              "templates":[

              ],
              "type":"Feature Layer",
              "displayField":"TITLE",
              "visibilityField":"VISIBLE",
              "name":"startDrawPoint",
              "hasAttachments":False,
              "typeIdField":"TYPEID",
              "capabilities":"Query",
              "allowGeometryUpdates":True,
              "htmlPopupType":"",
              "hasM":False,
              "hasZ":False,
              "globalIdField":"",
              "supportedQueryFormats":"JSON",
              "hasStaticData":False,
              "maxRecordCount":-1,
              "indexes":[

              ],
              "types":[

              ],
              "fields":[
                 {
                    "alias":"OBJECTID",
                    "name":"OBJECTID",
                    "type":"esriFieldTypeOID",
                    "editable":False
                 },
                 {
                    "alias":"Title",
                    "name":"TITLE",
                    "length":50,
                    "type":"esriFieldTypeString",
                    "editable":True
                 },
                 {
                    "alias":"Visible",
                    "name":"VISIBLE",
                    "type":"esriFieldTypeInteger",
                    "editable":True
                 },
                 {
                    "alias":"Description",
                    "name":"DESCRIPTION",
                    "length":1073741822,
                    "type":"esriFieldTypeString",
                    "editable":True
                 },
                 {
                    "alias":"Type ID",
                    "name":"TYPEID",
                    "type":"esriFieldTypeInteger",
                    "editable":True
                 }
              ]
           },
           "featureSet":{
              "features":[
                 {
                    "geometry":{
                       "x":80.27032792000051,
                       "y":13.085227147000467,
                       "spatialReference":{
                          "wkid": 4326,
                          "latestWkid":4326
                       }
                    },
                  "attributes":{
                       "description":"blayer desc",
                       "title":"blayer",
                       "OBJECTID":0,
                       "VISIBLE":1
                    },
                    "symbol":{
                       "angle":0,
                       "xoffset":0,
                       "yoffset":8.15625,
                       "type":"esriPMS",
                       "url":"https://cdn.arcgis.com/cdn/7674/js/jsapi/esri/dijit/images/Directions/greenPoint.png",
                       "imageData":"iVBORw0KGgoAAAANSUhEUgAAABUAAAAdCAYAAABFRCf7AAAAGXRFWHRTb2Z0d2FyZQBBZG9iZSBJbWFnZVJlYWR5ccllPAAAAyRpVFh0WE1MOmNvbS5hZG9iZS54bXAAAAAAADw/eHBhY2tldCBiZWdpbj0i77u/IiBpZD0iVzVNME1wQ2VoaUh6cmVTek5UY3prYzlkIj8+IDx4OnhtcG1ldGEgeG1sbnM6eD0iYWRvYmU6bnM6bWV0YS8iIHg6eG1wdGs9IkFkb2JlIFhNUCBDb3JlIDUuMC1jMDYxIDY0LjE0MDk0OSwgMjAxMC8xMi8wNy0xMDo1NzowMSAgICAgICAgIj4gPHJkZjpSREYgeG1sbnM6cmRmPSJodHRwOi8vd3d3LnczLm9yZy8xOTk5LzAyLzIyLXJkZi1zeW50YXgtbnMjIj4gPHJkZjpEZXNjcmlwdGlvbiByZGY6YWJvdXQ9IiIgeG1sbnM6eG1wPSJodHRwOi8vbnMuYWRvYmUuY29tL3hhcC8xLjAvIiB4bWxuczp4bXBNTT0iaHR0cDovL25zLmFkb2JlLmNvbS94YXAvMS4wL21tLyIgeG1sbnM6c3RSZWY9Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC9zVHlwZS9SZXNvdXJjZVJlZiMiIHhtcDpDcmVhdG9yVG9vbD0iQWRvYmUgUGhvdG9zaG9wIENTNS4xIE1hY2ludG9zaCIgeG1wTU06SW5zdGFuY2VJRD0ieG1wLmlpZDo4OTI1MkU2ODE0QzUxMUUyQURFMUNDNThGMTA3MjkzMSIgeG1wTU06RG9jdW1lbnRJRD0ieG1wLmRpZDo4OTI1MkU2OTE0QzUxMUUyQURFMUNDNThGMTA3MjkzMSI+IDx4bXBNTTpEZXJpdmVkRnJvbSBzdFJlZjppbnN0YW5jZUlEPSJ4bXAuaWlkOjg5MjUyRTY2MTRDNTExRTJBREUxQ0M1OEYxMDcyOTMxIiBzdFJlZjpkb2N1bWVudElEPSJ4bXAuZGlkOjg5MjUyRTY3MTRDNTExRTJBREUxQ0M1OEYxMDcyOTMxIi8+IDwvcmRmOkRlc2NyaXB0aW9uPiA8L3JkZjpSREY+IDwveDp4bXBtZXRhPiA8P3hwYWNrZXQgZW5kPSJyIj8+iVNkdQAABJlJREFUeNp0VltvG0UUnpkdr72261CnCQWEIA9FqOKlqooARUKCtAUhoA+VoBVRhfgFXKSKJ97goRL8ARCIclGgL0VUkBBAoBaVoggEQQVSAhFS06SJje3Y3t25cc7srL3YjddHs3N85pvvfOfMyJRs83n8o+P7POI9yQibooTeBa68ISbSRv+hifpCGHX2s6dnfrrRWjroOPzB0T0+zZ0q8uDRSrniF/MB8X2fADhR8IRRRDphh7Q6rbgtOucU0Sdnj59Z2hb00PtHD+Zp/p2x6uitO4o7iLYP8DMafjVE2wXUboALm50W2ahtXO3q8MTX02fnh0Affu/IkSAXnL55dLzMPU6kURZMIZQhFtRk2VBKcpQTIQVZ21hrdUX4zDcnPv2kBzr59mP3BLnChfGx8YrHPKIAELSzMPhQk+ydzpOvIYwywjFeK7K+vt6IlZw8/+y5RZ4gm9eCUrGCmkUyBkCV0Sd5UlBtTLIhRWQE9ixwsVwe6dY3X4WwJ+j9bx7a7/v5i6O7qlxisFZJAvBF7Rjty56CWlmszilj6BNgXd+syTCO7uNK62nuezyUkWWASTPHDtOjbgOHkJTOsbXAyJhIC+rlODdROM211gcQKBJxoh+EKAs4AGqybHVfBvdICNIU/IDHYbcJiS6le4wwbW1B9UDXJcg9QBxtbglh1BlAJzjoUxIGQZFRwtAypgnjtH0spDG9MWVs34xrN5uBLnEoTKQUgDLgZ6hliLunBaIDhy4LYhyotptZlphGyLUhfyspxxj3AIpaVqikdgyzoGn7p0xNj71rNamweCscWC0qoQ8YRm3K2OgpeFoc+j9FSUYKB+4OgxIK4RcZUJ6RsUgqCrShxWzza9035aw/lzYGY5P4xFSMR5vMcFpm87opL4HjXsr76dLhC2xYhgx3I0BfoS7RCp+3K/e8vn+Ke2zWK+cYofQG9yMlw1eK1aAni9oSWil9eOmFhXkPnbXZ1eXqwVsirfQU9Vynm75lymLbxvpSP4yqI4iR5uWlFxdOI56Xbro5t3qhOrW7ZmL1EOFwp7k6pRXuWaZgBmuwJSIl1fNXXvrxjRTLy2ZTm1v9YeTBXedNbCYZZ1U4pdt+NGiomuKKEvKp5ZM/f5z9zctc1vju1b9cv5q/M/icBd4+KNztlnGWKfYjAMqm+K7zZ/PYP6d+X3TrafbmR8N71QcrOPMLd5RGdj838WFup393orNLWRki6vFv197661i40m6AKwYLneG79BzDPNhNYFWwnfguGyKgPl32bwseoTnKekVpS9n49vorWwv1JsSVwAJHCHcW2Agsk3rBBZXBihhcn11biTfDixpPik1bEZyj34EVXXzJrUccWwrbZo5+B6ztRpvO1kLjjO5qW3YccZ5JeTAecQxqqV0Q6hM5KVIrNL5a/77yQPUyLbK9qiMv49zFhW6MMnPE0dwxlQ48ckXDNHJOq0C2xByreHtxhPk1sK4DEI5dut7+QWCZCyj9MXKLWmD/gl1Xtfhd6F2CI86dv+XiIrdOpeeCDd0VyW7KGbLptn9p/mrgNsIxwzKN0QO3IvlPgAEA3AQhIZtaN54AAAAASUVORK5CYII=",
                       "contentType":"image/png",
                       "width":15.75,
                       "height":21.75
                    }
                 }
              ],
              "geometryType":"esriGeometryPoint"
           },
           "nextObjectId":1
        }

        input_layer_url = ""
        if isinstance(input_layer, arcgis.gis.Item):
            if input_layer.type.lower() == 'feature service':
                input_param =  {"url": input_layer.layers[0].url }
            elif input_layer.type.lower() == 'feature collection':
                fcdict = input_layer.get_data()
                fc = arcgis.features.FeatureCollection(fcdict['layers'][0])
                input_param =  fc.layer
            else:
                raise TypeError("item type must be feature service or feature collection")

        elif isinstance(input_layer, arcgis.features.FeatureLayerCollection):
            input_layer_url = input_layer.layers[0].url #["url"]
            input_param =  {"url": input_layer_url }
        elif isinstance(input_layer, arcgis.features.FeatureCollection):
            input_param =  input_layer.properties
        elif isinstance(input_layer, arcgis.gis.Layer):
            input_layer_url = input_layer.url
            input_param =  {"url": input_layer_url }
        elif isinstance(input_layer, tuple): # geocoding location, convert to point featureset
            input_param = point_fs
            input_param["featureSet"]["features"][0]["geometry"]["x"] = input_layer[1]
            input_param["featureSet"]["features"][0]["geometry"]["y"] = input_layer[0]
        elif isinstance(input_layer, dict): # could add support for geometry one day using geometry -> featureset
            if 'location' in input_layer: # geocoder result
                geom = arcgis.geometry.Geometry(input_layer['location'])
                fset = FeatureSet([Feature(geom)])
                featcoll = {'layerDefinition': {
                        "geometryType": "esriGeometryPoint",
                        "objectIdField": "OBJECTID",
                        "fields": [
                            {
                                "alias": "OBJECTID",
                                "name": "OBJECTID",
                                "type": "esriFieldTypeOID",
                                "editable": False
                            }
                        ]
                    }, 'featureSet': fset.to_dict()}
                input_param = featcoll
            else:
                input_param =  input_layer
        elif isinstance(input_layer, str):
            input_layer_url = input_layer
            input_param =  {"url": input_layer_url }
        else:
            raise Exception("Invalid format of input layer. url string, feature service Item, feature service instance or dict supported")

        return input_param

    def _raster_input(self, input_raster):
        if isinstance(input_raster, arcgis.gis.Item):
            if input_raster.type.lower() == 'image service':
                input_param =  {"itemId": input_raster.itemid }
            else:
                raise TypeError("item type must be image service")
        elif isinstance(input_raster, str):
            input_param =  {"url": input_raster }
        elif isinstance(input_raster, dict):
            input_param =  input_raster
        else:
            raise Exception("Invalid format of input raster. image service Item or image service url, cloud raster uri or shared data path supported")

        return input_param


class _FeatureAnalysisTools(_AsyncService):
    """
    Provides feature analysis tools from the Spatial Analysis service. The SpatialAnalysis service is used for supporting Spatial analysis capability
    in Portal for ArcGIS and ArcGIS Online.

    Several `FeatureAnalysisTools` accept feature layers as inputs. The input layer can be passed in using several different formats:
    * a Feature Service Item. The first layer in the Feature Service is used as input
    * a Feature Collection Item. The first layer in the Feature Collection is used as input
    * an `arcgis.lyr.FeatureService` object. The first layer in the Feature Service is used as input
    * an `arcgis.lyr.FeatureCollection` object. The first layer in the Feature Collection is used as input
    * an `arcgis.lyr.Layer` object. The object could be any sub-class of Layer that has features
    * a Feature Collection specified as a python dictionary (with layer definition and a feature set)
    * a string with the url of the feature service
    """

    def __init__(self, url, gis):
        """
        Constructs a client to the service given it's url from ArcGIS Online or Portal.
        """
        super(_FeatureAnalysisTools, self).__init__(url, gis)

    def aggregate_points(self,
                       point_layer,
                       polygon_layer,
                       keep_boundaries_with_no_points=True,
                       summary_fields=[],
                       group_by_field=None,
                       minority_majority=False,
                       percent_points=False,
                       output_name=None,
                       context=None):
        """
        Aggregate points task allows you to aggregate or count the total number of points that are distributed within specified areas or boundaries (polygons). You can also summarize Sum, Mean, Min, Max and Standard deviation calculations for attributes of the point layer to understand the general characteristics of aggregated points.

        Parameters
        ----------
        point_layer : Required layer (see Feature Input in documentation)
            Point layer to be aggregated
        polygon_layer : Required layer (see Feature Input in documentation)
            Polygon layer to which the points should be aggregated.
        keep_boundaries_with_no_points : Optional bool
            Specify whether the polygons without any points should be returned in the output.
        summary_fields : Optional list of strings
            A list of field names and summary type. Example [fieldName1 summaryType1,fieldName2 summaryType2].
        group_by_field : Optional string
            A field name from PointLayer based on which the points will be grouped.
        minority_majority : Optional bool
            This boolean parameter is applicable only when a groupByField is specified. If true, the minority (least dominant) or the majority (most dominant) attribute values within each group, within each boundary will be calculated.
        percent_points : Optional bool
            This boolean parameter is applicable only when a groupByField is specified. If set to true, the percentage count of points for each unique groupByField value is calculated.
        output_name : Optional string
            Additional properties such as output feature service name.
        context : Optional string
            Additional settings such as processing extent and output spatial reference.

        Returns
        -------
        dict with the following keys:
           "aggregated_layer" : layer (FeatureCollection)
           "group_summary" : layer (FeatureCollection)
        """

        task ="AggregatePoints"

        params = {}

        params["pointLayer"] = super()._feature_input(point_layer)
        params["polygonLayer"] = super()._feature_input(polygon_layer)
        if keep_boundaries_with_no_points is not None:
            params["keepBoundariesWithNoPoints"] = keep_boundaries_with_no_points
        if summary_fields is not None:
            params["summaryFields"] = summary_fields
        if group_by_field is not None:
            params["groupByField"] = group_by_field
        if minority_majority is not None:
            params["minorityMajority"] = minority_majority
        if percent_points is not None:
            params["percentPoints"] = percent_points
        if output_name is not None:
            params["outputName"] = {"serviceProperties": {"name": output_name }}
        if context is not None:
            params["context"] = context

        task_url, job_info = super()._analysis_job(task, params)

        job_info = super()._analysis_job_status(task_url, job_info)
        job_values = super()._analysis_job_results(task_url, job_info)
        #print(job_values)
        if output_name is not None:
            itemid = job_values['aggregatedLayer']['itemId']
            item = arcgis.gis.Item(self._gis, itemid)
            return item
        else:
            # Feature Collection

            aggregated_layer = arcgis.features.FeatureCollection(job_values['aggregatedLayer'])

            group_summary = arcgis.features.FeatureCollection(job_values['groupSummary'])
            return { "aggregated_layer":aggregated_layer, "group_summary":group_summary, }


    def find_hot_spots(self,
                       analysis_layer,
                       analysis_field=None,
                       divided_by_field=None,
                       bounding_polygon_layer=None,
                       aggregation_polygon_layer=None,
                       output_name=None,
                       context=None):
        """
        The Find Hot Spots task finds statistically significant clusters of incident points, weighted points, or weighted polygons. For incident data, the analysis field (weight) is obtained by aggregation. Output is a hot spot map.

        Parameters
        ----------
        analysis_layer : Required layer (see Feature Input in documentation)
            The point or polygon feature layer for which hot spots will be calculated.
        analysis_field : Optional string
            The numeric field in the AnalysisLayer that will be analyzed.
        divided_by_field : Optional string

        bounding_polygon_layer : Optional layer (see Feature Input in documentation)
            When the analysis layer is points and no AnalysisField is specified, you can provide polygons features that define where incidents could have occurred.
        aggregation_polygon_layer : Optional layer (see Feature Input in documentation)
            When the AnalysisLayer contains points and no AnalysisField is specified, you can provide polygon features into which the points will be aggregated and analyzed, such as administrative units.
        output_name : Optional string
            Additional properties such as output feature service name.
        context : Optional string
            Additional settings such as processing extent and output spatial reference.

        Returns
        -------
        dict with the following keys:
           "hot_spots_result_layer" : layer (FeatureCollection)
           "process_info" : list of messages
        """

        task ="FindHotSpots"

        params = {}

        params["analysisLayer"] = super()._feature_input(analysis_layer)
        if analysis_field is not None:
            params["analysisField"] = analysis_field
        if divided_by_field is not None:
            params["dividedByField"] = divided_by_field
        if bounding_polygon_layer is not None:
            params["boundingPolygonLayer"] = super()._feature_input(bounding_polygon_layer)
        if aggregation_polygon_layer is not None:
            params["aggregationPolygonLayer"] = super()._feature_input(aggregation_polygon_layer)
        if output_name is not None:
            params["outputName"] = {"serviceProperties": {"name": output_name }}
        if context is not None:
            params["context"] = context

        task_url, job_info = super()._analysis_job(task, params)

        job_info = super()._analysis_job_status(task_url, job_info)
        job_values = super()._analysis_job_results(task_url, job_info)
        #print(job_values)
        if output_name is not None:
            itemid = job_values['hotSpotsResultLayer']['itemId']
            item = arcgis.gis.Item(self._gis, itemid)
            return item
        else:
            # Feature Collection

            hot_spots_result_layer = arcgis.features.FeatureCollection(job_values['hotSpotsResultLayer'])

            process_info = job_values['processInfo']
            return { "hot_spots_result_layer":hot_spots_result_layer, "process_info":process_info, }


    def create_buffers(self,
                       input_layer,
                       distances=[],
                       field=None,
                       units="Meters",
                       dissolve_type="None",
                       ring_type="Disks",
                       side_type="Full",
                       end_type="Round",
                       output_name=None,
                       context=None):
        """
        Creates buffer polygon(s) around input features.

        Parameters
        ----------
        input_layer : Required layer (see Feature Input in documentation)
            The input to be buffered.
        distances : Optional list of floats
            The distance(s) that will be buffered.
        field : Optional string
            Buffers will be created using field values.
        units : Optional string
            The linear unit to be used with the distance value(s).
        dissolve_type : Optional string
            Specifies the dissolve to be performed to remove buffer overlap.
        ring_type : Optional string
            The ring type.
        side_type : Optional string
            The side(s) of the input that will be buffered.
        end_type : Optional string
            The shape of the buffer at the end of buffered line features.
        output_name : Optional string
            Additional properties such as output feature service name.
        context : Optional string
            Additional settings such as processing extent and output spatial reference.

        Returns
        -------
        buffer_layer : layer (FeatureCollection)
        """

        task ="CreateBuffers"

        params = {}

        params["inputLayer"] = super()._feature_input(input_layer)
        if distances is not None:
            params["distances"] = distances
        if field is not None:
            params["field"] = field
        if units is not None:
            params["units"] = units
        if dissolve_type is not None:
            params["dissolveType"] = dissolve_type
        if ring_type is not None:
            params["ringType"] = ring_type
        if side_type is not None:
            params["sideType"] = side_type
        if end_type is not None:
            params["endType"] = end_type
        if output_name is not None:
            params["outputName"] = {"serviceProperties": {"name": output_name }}
        if context is not None:
            params["context"] = context

        task_url, job_info = super()._analysis_job(task, params)

        job_info = super()._analysis_job_status(task_url, job_info)
        job_values = super()._analysis_job_results(task_url, job_info)
        #print(job_values)
        if output_name is not None:
            itemid = job_values['bufferLayer']['itemId']
            item = arcgis.gis.Item(self._gis, itemid)
            return item
        else:
            # Feature Collection
            return arcgis.features.FeatureCollection(job_values['bufferLayer'])


    def create_drive_time_areas(self,
                       input_layer,
                       break_values=[5, 10, 15],
                       break_units="Minutes",
                       travel_mode="Driving",
                       overlap_policy="Overlap",
                       time_of_day=None,
                       time_zone_for_time_of_day="GeoLocal",
                       output_name=None,
                       context=None):
        """


        Parameters
        ----------
        input_layer : Required layer (see Feature Input in documentation)

        break_values : Optional list of floats

        break_units : Optional string

        travel_mode : Optional string

        overlap_policy : Optional string

        time_of_day : Optional datetime.date

        time_zone_for_time_of_day : Optional string

        output_name : Optional string
            Additional properties such as output feature service name.
        context : Optional string
            Additional settings such as processing extent and output spatial reference.

        Returns
        -------
        drive_time_areas_layer : layer (FeatureCollection)
        """

        task ="CreateDriveTimeAreas"

        params = {}

        params["inputLayer"] = super()._feature_input(input_layer)
        if break_values is not None:
            params["breakValues"] = break_values
        if break_units is not None:
            params["breakUnits"] = break_units
        if travel_mode is not None:
            params["travelMode"] = travel_mode
        if overlap_policy is not None:
            params["overlapPolicy"] = overlap_policy
        if time_of_day is not None:
            params["timeOfDay"] = time_of_day
        if time_zone_for_time_of_day is not None:
            params["timeZoneForTimeOfDay"] = time_zone_for_time_of_day
        if output_name is not None:
            params["outputName"] = {"serviceProperties": {"name": output_name }}
        if context is not None:
            params["context"] = context

        task_url, job_info = super()._analysis_job(task, params)

        job_info = super()._analysis_job_status(task_url, job_info)
        job_values = super()._analysis_job_results(task_url, job_info)
        #print(job_values)
        if output_name is not None:
            itemid = job_values['driveTimeAreasLayer']['itemId']
            item = arcgis.gis.Item(self._gis, itemid)
            return item
        else:
            # Feature Collection
            return arcgis.features.FeatureCollection(job_values['driveTimeAreasLayer'])


    def dissolve_boundaries(self,
                       input_layer,
                       dissolve_fields=[],
                       summary_fields=[],
                       output_name=None,
                       context=None):
        """
        Dissolve features based on specified fields.

        Parameters
        ----------
        input_layer : Required layer (see Feature Input in documentation)
            The layer containing polygon features that will be dissolved.
        dissolve_fields : Optional list of strings
            One or more fields from the input that control which polygons are merged. If no fields are supplied, all polygons that overlap or shared a common border will be dissolved into one polygon.
        summary_fields : Optional list of strings
            A list of field names and statistical types that will be used to summarize the output. Supported statistics include: Sum, Mean, Min, Max, and Stddev.
        output_name : Optional string
            Additional properties such as output feature service name.
        context : Optional string
            Additional settings such as processing extent and output spatial reference.

        Returns
        -------
        dissolved_layer : layer (FeatureCollection)
        """

        task ="DissolveBoundaries"

        params = {}

        params["inputLayer"] = super()._feature_input(input_layer)
        if dissolve_fields is not None:
            params["dissolveFields"] = dissolve_fields
        if summary_fields is not None:
            params["summaryFields"] = summary_fields
        if output_name is not None:
            params["outputName"] = {"serviceProperties": {"name": output_name }}
        if context is not None:
            params["context"] = context

        task_url, job_info = super()._analysis_job(task, params)

        job_info = super()._analysis_job_status(task_url, job_info)
        job_values = super()._analysis_job_results(task_url, job_info)
        #print(job_values)
        if output_name is not None:
            itemid = job_values['dissolvedLayer']['itemId']
            item = arcgis.gis.Item(self._gis, itemid)
            return item
        else:
            # Feature Collection
            return arcgis.features.FeatureCollection(job_values['dissolvedLayer'])


    def merge_layers(self,
                       input_layer,
                       merge_layer,
                       merging_attributes=[],
                       output_name=None,
                       context=None):
        """
        Combines two inputs of the same feature data type into a new output.

        Parameters
        ----------
        input_layer : Required layer (see Feature Input in documentation)
             The point, line, or polygon  features to merge with the mergeLayer.
        merge_layer : Required layer (see Feature Input in documentation)
            The point, line or polygon features to merge with inputLayer.  mergeLayer must contain the same feature type (point, line, or polygon) as the inputLayer.
        merging_attributes : Optional list of strings
            An array of values that describe how fields from the mergeLayer are to be modified.  By default all fields from both inputs will be carried across to the output.
        output_name : Optional string
            Additional properties such as output feature service name.
        context : Optional string
            Additional settings such as processing extent and output spatial reference.

        Returns
        -------
        merged_layer : layer (FeatureCollection)
        """

        task ="MergeLayers"

        params = {}

        params["inputLayer"] = super()._feature_input(input_layer)
        params["mergeLayer"] = super()._feature_input(merge_layer)
        if merging_attributes is not None:
            params["mergingAttributes"] = merging_attributes
        if output_name is not None:
            params["outputName"] = {"serviceProperties": {"name": output_name }}
        if context is not None:
            params["context"] = context

        task_url, job_info = super()._analysis_job(task, params)

        job_info = super()._analysis_job_status(task_url, job_info)
        job_values = super()._analysis_job_results(task_url, job_info)
        #print(job_values)
        if output_name is not None:
            itemid = job_values['mergedLayer']['itemId']
            item = arcgis.gis.Item(self._gis, itemid)
            return item
        else:
            # Feature Collection
            return arcgis.features.FeatureCollection(job_values['mergedLayer'])


    def summarize_within(self,
                       sum_within_layer,
                       summary_layer,
                       sum_shape=True,
                       shape_units=None,
                       summary_fields=[],
                       group_by_field=None,
                       minority_majority=False,
                       percent_shape=False,
                       output_name=None,
                       context=None):
        """
        The SummarizeWithin task helps you to summarize and find statistics on the point, line, or polygon features (or portions of these features) that are within the boundaries of polygons in another layer. For example:Given a layer of watershed boundaries and a layer of land-use boundaries by land-use type, calculate total acreage of land-use type for each watershed.Given a layer of parcels in a county and a layer of city boundaries, summarize the average value of vacant parcels within each city boundary.Given a layer of counties and a layer of roads, summarize the total mileage of roads by road type within each county.

        Parameters
        ----------
        sum_within_layer : Required layer (see Feature Input in documentation)
            A polygon feature layer or featurecollection. Features, or portions of features, in the summaryLayer (below) that fall within the boundaries of these polygons will be summarized.
        summary_layer : Required layer (see Feature Input in documentation)
            Point, line, or polygon features that will be summarized for each polygon in the sumWithinLayer.
        sum_shape : Optional bool
            A boolean value that instructs the task to calculate count of points, length of lines or areas of polygons of the summaryLayer within each polygon in sumWithinLayer.
        shape_units : Optional string
            Specify units to summarize the length or areas when sumShape is set to true. Units is not required to summarize points.
        summary_fields : Optional list of strings
            A list of field names and statistical summary type that you wish to calculate for all features in the  summaryLayer that are within each polygon in the sumWithinLayer . Eg: ["fieldname1 summary", "fieldname2 summary"]
        group_by_field : Optional string
            Specify a field from the summaryLayer features to calculate statistics separately for each unique attribute value.
        minority_majority : Optional bool
            This boolean parameter is applicable only when a groupByField is specified. If true, the minority (least dominant) or the majority (most dominant) attribute values within each group, within each boundary will be calculated.
        percent_shape : Optional bool
            This boolean parameter is applicable only when a groupByField is specified. If set to true, the percentage of shape (eg. length for lines) for each unique groupByField value is calculated.
        output_name : Optional string
            Additional properties such as output feature service name.
        context : Optional string
            Additional settings such as processing extent and output spatial reference.

        Returns
        -------
        dict with the following keys:
           "result_layer" : layer (FeatureCollection)
           "group_by_summary" : layer (FeatureCollection)
        """

        task ="SummarizeWithin"

        params = {}

        params["sumWithinLayer"] = super()._feature_input(sum_within_layer)
        params["summaryLayer"] = super()._feature_input(summary_layer)
        if sum_shape is not None:
            params["sumShape"] = sum_shape
        if shape_units is not None:
            params["shapeUnits"] = shape_units
        if summary_fields is not None:
            params["summaryFields"] = summary_fields
        if group_by_field is not None:
            params["groupByField"] = group_by_field
        if minority_majority is not None:
            params["minorityMajority"] = minority_majority
        if percent_shape is not None:
            params["percentShape"] = percent_shape
        if output_name is not None:
            params["outputName"] = {"serviceProperties": {"name": output_name }}
        if context is not None:
            params["context"] = context

        task_url, job_info = super()._analysis_job(task, params)

        job_info = super()._analysis_job_status(task_url, job_info)
        job_values = super()._analysis_job_results(task_url, job_info)
        #print(job_values)
        if output_name is not None:
            itemid = job_values['resultLayer']['itemId']
            item = arcgis.gis.Item(self._gis, itemid)
            return item
        else:
            # Feature Collection

            result_layer = arcgis.features.FeatureCollection(job_values['resultLayer'])

            group_by_summary = arcgis.features.FeatureCollection(job_values['groupBySummary'])
            return { "result_layer":result_layer, "group_by_summary":group_by_summary, }

    def join_features(self,
        target_layer,
        join_layer,
        spatial_relationship,
        spatial_relationship_distance,
        spatial_relationship_distance_units,
        attribute_relationship,
        join_operation,
        summary_fields,
        output_name,
        context):

        task ="JoinFeatures"

        params = {}

        params["targetLayer"] = super()._feature_input(target_layer)
        params["joinLayer"] = super()._feature_input(join_layer)
        if spatial_relationship is not None:
            params["spatialRelationship"] = spatial_relationship
        if spatial_relationship_distance is not None:
            params["spatialRelationshipDistance"] = spatial_relationship_distance
        if spatial_relationship_distance_units is not None:
            params["spatialRelationshipDistanceUnits"] = spatial_relationship_distance_units
        if attribute_relationship is not None:
            params["attributeRelationship"] = attribute_relationship
        if summary_fields is not None:
            params["summaryFields"] = summary_fields
        if join_operation is not None:
            params["joinOperation"] = join_operation
        if output_name is not None:
            params["outputName"] = {"serviceProperties": {"name": output_name }}
        if context is not None:
            params["context"] = context

        task_url, job_info = super()._analysis_job(task, params)

        job_info = super()._analysis_job_status(task_url, job_info)
        job_values = super()._analysis_job_results(task_url, job_info)
        #print(job_values)
        if output_name is not None:
            itemid = job_values['outputLayer']['itemId']
            item = arcgis.gis.Item(self._gis, itemid)
            return item
        else:
            # Feature Collection
            return arcgis.features.FeatureCollection(job_values['outputLayer'])

    def enrich_layer(self,
                       input_layer,
                       data_collections=[],
                       analysis_variables=[],
                       country=None,
                       buffer_type=None,
                       distance=None,
                       units=None,
                       output_name=None,
                       context=None):
        """
        The Enrich Layer task enriches your data by getting facts about the people, places, and businesses that surround your data locations. For example: What kind of people live here? What do people like to do in this area? What are their habits and lifestyles? What kind of businesses are there in this area?The result will be a new layer of input features that includes all demographic and geographic information from given data collections.

        Parameters
        ----------
        input_layer : Required layer (see Feature Input in documentation)
            Feature layer to enrich with new data
        data_collections : Optional list of strings
            Data collections you wish to add to your features.
        analysis_variables : Optional list of strings
            A subset of specific variables instead of dataCollections.
        country : Optional string
            The two character country code that specifies the country of the input features. Eg. US (United States),  FR (France), GB (United Kingdom) etc.
        buffer_type : Optional string
            Area to be created around the point or line features for enrichment. Default is 1 Mile straight-line buffer radius.
        distance : Optional float
            A double value that defines the straight-line distance or time (when drivingTime is used).
        units : Optional string
            The unit (eg. Miles, Minutes) to be used with the distance value(s) specified in the distance parameter to calculate the area.
        output_name : Optional string
            Additional properties such as output feature service name.
        context : Optional string
            Additional settings such as processing extent and output spatial reference.

        Returns
        -------
        enriched_layer : layer (FeatureCollection)
        """

        task ="EnrichLayer"

        params = {}

        params["inputLayer"] = super()._feature_input(input_layer)
        if data_collections is not None:
            params["dataCollections"] = data_collections
        if analysis_variables is not None:
            params["analysisVariables"] = analysis_variables
        if country is not None:
            params["country"] = country
        if buffer_type is not None:
            params["bufferType"] = buffer_type
        if distance is not None:
            params["distance"] = distance
        if units is not None:
            params["units"] = units
        if output_name is not None:
            params["outputName"] = {"serviceProperties": {"name": output_name }}
        if context is not None:
            params["context"] = context

        task_url, job_info = super()._analysis_job(task, params)

        job_info = super()._analysis_job_status(task_url, job_info)
        job_values = super()._analysis_job_results(task_url, job_info)
        #print(job_values)
        if output_name is not None:
            itemid = job_values['enrichedLayer']['itemId']
            item = arcgis.gis.Item(self._gis, itemid)
            return item
        else:
            # Feature Collection
            return arcgis.features.FeatureCollection(job_values['enrichedLayer'])


    def overlay_layers(self,
                       input_layer,
                       overlay_layer,
                       overlay_type="Intersect",
                       snap_to_input=False,
                       output_type="Input",
                       tolerance=None,
                       output_name=None,
                       context=None):
        """
        Overlays the input layer with the overlay layer. Overlay operations supported are Intersect, Union, and Erase.

        Parameters
        ----------
        input_layer : Required layer (see Feature Input in documentation)
            The input analysis layer.
        overlay_layer : Required layer (see Feature Input in documentation)
            The layer to be overlaid with the analysis layer.
        overlay_type : Optional string
            The overlay type (INTERSECT, UNION, or ERASE) defines how the analysis layer and the overlay layer are combined.
        snap_to_input : Optional bool
            When the distance between features is less than the tolerance, the features in the overlay layer will snap to the features in the input layer.
        output_type : Optional string
            The type of intersection (INPUT, LINE, POINT).
        tolerance : Optional float
            The minimum distance separating all feature coordinates (nodes and vertices) as well as the distance a coordinate can move in X or Y (or both).
        output_name : Optional string
            Additional properties such as output feature service name.
        context : Optional string
            Additional settings such as processing extent and output spatial reference.

        Returns
        -------
        output_layer : layer (FeatureCollection)
        """

        task ="OverlayLayers"

        params = {}

        params["inputLayer"] = super()._feature_input(input_layer)
        params["overlayLayer"] = super()._feature_input(overlay_layer)
        if overlay_type is not None:
            params["overlayType"] = overlay_type
        if snap_to_input is not None:
            params["snapToInput"] = snap_to_input
        if output_type is not None:
            params["outputType"] = output_type
        if tolerance is not None:
            params["tolerance"] = tolerance
        if output_name is not None:
            params["outputName"] = {"serviceProperties": {"name": output_name }}
        if context is not None:
            params["context"] = context

        task_url, job_info = super()._analysis_job(task, params)

        job_info = super()._analysis_job_status(task_url, job_info)
        job_values = super()._analysis_job_results(task_url, job_info)
        #print(job_values)
        if output_name is not None:
            itemid = job_values['outputLayer']['itemId']
            item = arcgis.gis.Item(self._gis, itemid)
            return item
        else:
            # Feature Collection
            return arcgis.features.FeatureCollection(job_values['outputLayer'])


    def extract_data(self,
                       input_layers=[],
                       extent=None,
                       clip=False,
                       data_format=None,
                       output_name=None,
                       context=None):
        """
        Select and download data for a specified area of interest. Layers that you select will be added to a zip file or layer package.

        Parameters
        ----------
        input_layers : Required list of strings
            The layers from which you can extract features.
        extent : Optional string
            The area that defines which features will be included in the output zip file or layer package.
        clip : Optional bool
            Select features that intersect the extent or clip features within the extent.
        data_format : Optional string
            Format of the data that will be extracted and downloaded.  Layer packages will always include file geodatabases. eg CSV
        output_name : Optional string
            Additional properties such as output name of the item
        context : Optional string
            Additional settings such as processing extent and output spatial reference.

        Returns
        -------
        an item in the GIS
        """

        task ="ExtractData"

        params = {}

        input_layers_param = []
        for input_lyr in input_layers:
            input_layers_param.append(super()._feature_input(input_lyr))

        params["inputLayers"] = input_layers_param
        if extent is not None:
            params["extent"] = extent
        if clip is not None:
            params["clip"] = clip
        if data_format is not None:
            params["dataFormat"] = data_format
        if output_name is not None:
            params["outputName"] = {"serviceProperties": {"name": output_name }}
        if context is not None:
            params["context"] = context

        task_url, job_info = super()._analysis_job(task, params)

        job_info = super()._analysis_job_status(task_url, job_info)
        job_values = super()._analysis_job_results(task_url, job_info)
        return self._gis.content.get(job_values['contentID']['itemId'])


    def find_existing_locations(self,
                       input_layers=[],
                       expressions=[],
                       output_name=None,
                       context=None):
        """
        The Find Existing Locations task selects features in the input layer that meet a query you specify. A query is made up of one or more expressions. There are two types of expressions: attribute and spatial. An example of an attribute expression is that a parcel must be vacant, which is an attribute of the Parcels layer (where STATUS = 'VACANT'). An example of a spatial expression is that the parcel must also be within a certain distance of a river (Parcels within a distance of 0.75 Miles from Rivers).

        Parameters
        ----------
        input_layers : Required list of strings
            A list of layers that will be used in the expressions parameter.
        expressions : Required string
            Specify a list of expressions. Please refer documentation at http://developers.arcgis.com for more information on creating expressions.
        output_name : Optional string
            Additional properties such as output feature service name.
        context : Optional string
            Additional settings such as processing extent and output spatial reference.

        Returns
        -------
        result_layer : layer (FeatureCollection)
        """

        task ="FindExistingLocations"

        params = {}

        params["inputLayers"] = input_layers
        params["expressions"] = expressions
        if output_name is not None:
            params["outputName"] = {"serviceProperties": {"name": output_name }}
        if context is not None:
            params["context"] = context

        task_url, job_info = super()._analysis_job(task, params)

        job_info = super()._analysis_job_status(task_url, job_info)
        job_values = super()._analysis_job_results(task_url, job_info)
        #print(job_values)
        if output_name is not None:
            itemid = job_values['resultLayer']['itemId']
            item = arcgis.gis.Item(self._gis, itemid)
            return item
        else:
            # Feature Collection
            return arcgis.features.FeatureCollection(job_values['resultLayer'])


    def derive_new_locations(self,
                       input_layers=[],
                       expressions=[],
                       output_name=None,
                       context=None):
        """
        The Derive New Locations task derives new features from the input layers that meet a query you specify. A query is made up of one or more expressions. There are two types of expressions: attribute and spatial. An example of an attribute expression is that a parcel must be vacant, which is an attribute of the Parcels layer (where STATUS = 'VACANT'). An example of a spatial expression is that the parcel must also be within a certain distance of a river (Parcels within a distance of 0.75 Miles from Rivers).The Derive New Locations task is very similar to the Find Existing Locations task, the main difference is that the result of Derive New Locations can contain partial features.In both tasks, the attribute expression  where and the spatial relationships within and contains return the same result. This is because these relationships return entire features.When intersects or withinDistance is used, Derive New Locations creates new features in the result. For example, when intersecting a parcel feature and a flood zone area that partially overlap each other, Find Existing Locations will return the entire parcel whereas Derive New Locations will return just the portion of the parcel that is within the flood zone.

        Parameters
        ----------
        input_layers : Required list of strings
            A list of layers that will be used in the expressions parameter.
        expressions : Required string
            Specify a list of expressions. Please refer documentation at http://developers.arcgis.com for more information on expressions.
        output_name : Optional string
            Additional properties such as output feature service name.
        context : Optional string
            Additional settings such as processing extent and output spatial reference.

        Returns
        -------
        result_layer : layer (FeatureCollection)
        """

        task ="DeriveNewLocations"

        params = {}

        params["inputLayers"] = input_layers
        params["expressions"] = expressions
        if output_name is not None:
            params["outputName"] = {"serviceProperties": {"name": output_name }}
        if context is not None:
            params["context"] = context

        task_url, job_info = super()._analysis_job(task, params)

        job_info = super()._analysis_job_status(task_url, job_info)
        job_values = super()._analysis_job_results(task_url, job_info)
        #print(job_values)
        if output_name is not None:
            itemid = job_values['resultLayer']['itemId']
            item = arcgis.gis.Item(self._gis, itemid)
            return item
        else:
            # Feature Collection
            return arcgis.features.FeatureCollection(job_values['resultLayer'])


    def field_calculator(self,
                       input_layer,
                       expressions,
                       output_name=None,
                       context=None):
        """
        Calculates existing fields or creates and calculates new fields.

        Parameters
        ----------
        input_layer : Required layer (see Feature Input in documentation)

        expressions : Required string

        output_name : Optional string

        context : Optional string


        Returns
        -------
        result_layer : layer (FeatureCollection)
        """

        task ="FieldCalculator"

        params = {}

        params["inputLayer"] = super()._feature_input(input_layer)
        params["expressions"] = expressions
        if output_name is not None:
            params["outputName"] = {"serviceProperties": {"name": output_name }}
        if context is not None:
            params["context"] = context

        task_url, job_info = super()._analysis_job(task, params)

        job_info = super()._analysis_job_status(task_url, job_info)
        job_values = super()._analysis_job_results(task_url, job_info)
        #print(job_values)
        if output_name is not None:
            itemid = job_values['resultLayer']['itemId']
            item = arcgis.gis.Item(self._gis, itemid)
            return item
        else:
            # Feature Collection
            return arcgis.features.FeatureCollection(job_values['resultLayer'])


    def interpolate_points(self,
                       input_layer,
                       field,
                       interpolate_option="5",
                       output_prediction_error=False,
                       classification_type="GeometricInterval",
                       num_classes=10,
                       class_breaks=[],
                       bounding_polygon_layer=None,
                       predict_at_point_layer=None,
                       output_name=None,
                       context=None):
        """
        The Interpolate Points task allows you to predict values at new locations based on measurements from a collection of points. The task takes point data with values at each point and returns areas classified by predicted values.

        Parameters
        ----------
        input_layer : Required layer (see Feature Input in documentation)
            The point layer whose features will be interpolated.
        field : Required string
            Name of the numeric field containing the values you wish to interpolate.
        interpolate_option : Optional string
            Integer value declaring your preference for speed versus accuracy, from 1 (fastest) to 9 (most accurate). More accurate predictions take longer to calculate.
        output_prediction_error : Optional bool
            If True, a polygon layer of standard errors for the interpolation predictions will be returned in the predictionError output parameter.
        classification_type : Optional string
            Determines how predicted values will be classified into areas.
        num_classes : Optional int
            This value is used to divide the range of interpolated values into distinct classes. The range of values in each class is determined by the classificationType parameter. Each class defines the boundaries of the result polygons.
        class_breaks : Optional list of floats
            If classificationType is Manual, supply desired class break values separated by spaces. These values define the upper limit of each class, so the number of classes will equal the number of entered values. Areas will not be created for any locations with predicted values above the largest entered break value. You must enter at least two values and no more than 32.
        bounding_polygon_layer : Optional layer (see Feature Input in documentation)
            A layer specifying the polygon(s) where you want values to be interpolated.
        predict_at_point_layer : Optional layer (see Feature Input in documentation)
            An optional layer specifying point locations to calculate prediction values. This allows you to make predictions at specific locations of interest.
        output_name : Optional string
            Additional properties such as output feature service name.
        context : Optional string
            Additional settings such as processing extent and output spatial reference.

        Returns
        -------
        dict with the following keys:
           "result_layer" : layer (FeatureCollection)
           "prediction_error" : layer (FeatureCollection)
           "predicted_point_layer" : layer (FeatureCollection)
        """

        task ="InterpolatePoints"

        params = {}

        params["inputLayer"] = super()._feature_input(input_layer)
        params["field"] = field
        if interpolate_option is not None:
            params["interpolateOption"] = interpolate_option
        if output_prediction_error is not None:
            params["outputPredictionError"] = output_prediction_error
        if classification_type is not None:
            params["classificationType"] = classification_type
        if num_classes is not None:
            params["numClasses"] = num_classes
        if class_breaks is not None:
            params["classBreaks"] = class_breaks
        if bounding_polygon_layer is not None:
            params["boundingPolygonLayer"] = super()._feature_input(bounding_polygon_layer)
        if predict_at_point_layer is not None:
            params["predictAtPointLayer"] = super()._feature_input(predict_at_point_layer)
        if output_name is not None:
            params["outputName"] = {"serviceProperties": {"name": output_name }}
        if context is not None:
            params["context"] = context

        task_url, job_info = super()._analysis_job(task, params)

        job_info = super()._analysis_job_status(task_url, job_info)
        job_values = super()._analysis_job_results(task_url, job_info)
        #print(job_values)
        if output_name is not None:
            itemid = job_values['resultLayer']['itemId']
            item = arcgis.gis.Item(self._gis, itemid)
            return item
        else:
            # Feature Collection

            result_layer = arcgis.features.FeatureCollection(job_values['resultLayer'])

            prediction_error = arcgis.features.FeatureCollection(job_values['predictionError'])

            predicted_point_layer = arcgis.features.FeatureCollection(job_values['predictedPointLayer'])
            return { "result_layer":result_layer, "prediction_error":prediction_error, "predicted_point_layer":predicted_point_layer, }


    def calculate_density(self,
                       input_layer,
                       field=None,
                       cell_size=None,
                       cell_size_units="Meters",
                       radius=None,
                       radius_units=None,
                       bounding_polygon_layer=None,
                       area_units=None,
                       classification_type="EqualInterval",
                       num_classes=10,
                       output_name=None,
                       context=None):
        """
        The Calculate Density task creates a density map from point or line features by spreading known quantities of some phenomenon (represented as attributes of the points or lines) across the map. The result is a layer of areas classified from least dense to most dense.

        Parameters
        ----------
        input_layer : Required layer (see Feature Input in documentation)
            The point or line features from which to calculate density.
        field : Optional string
            A numeric field name specifying the number of incidents at each location. If not specified, each location will be assumed to represent a single count.
        cell_size : Optional float
            This value is used to create a mesh of points where density values are calculated. The default is approximately 1/1000th of the smaller of the width and height of the analysis extent as defined in the context parameter.
        cell_size_units : Optional string
            The units of the cellSize value
        radius : Optional float
            A distance specifying how far to search to find point or line features when calculating density values.
        radius_units : Optional string
            The units of the radius parameter.
        bounding_polygon_layer : Optional layer (see Feature Input in documentation)
            A layer specifying the polygon(s) where you want densities to be calculated.
        area_units : Optional string
            The units of the calculated density values.
        classification_type : Optional string
            Determines how density values will be classified into polygons.
        num_classes : Optional int
            This value is used to divide the range of predicted values into distinct classes. The range of values in each class is determined by the classificationType parameter.
        output_name : Optional string
            Additional properties such as output feature service name.
        context : Optional string
            Additional settings such as processing extent and output spatial reference.

        Returns
        -------
        result_layer : layer (FeatureCollection)
        """

        task ="CalculateDensity"

        params = {}

        params["inputLayer"] = super()._feature_input(input_layer)
        if field is not None:
            params["field"] = field
        if cell_size is not None:
            params["cellSize"] = cell_size
        if cell_size_units is not None:
            params["cellSizeUnits"] = cell_size_units
        if radius is not None:
            params["radius"] = radius
        if radius_units is not None:
            params["radiusUnits"] = radius_units
        if bounding_polygon_layer is not None:
            params["boundingPolygonLayer"] = super()._feature_input(bounding_polygon_layer)
        if area_units is not None:
            params["areaUnits"] = area_units
        if classification_type is not None:
            params["classificationType"] = classification_type
        if num_classes is not None:
            params["numClasses"] = num_classes
        if output_name is not None:
            params["outputName"] = {"serviceProperties": {"name": output_name }}
        if context is not None:
            params["context"] = context

        task_url, job_info = super()._analysis_job(task, params)

        job_info = super()._analysis_job_status(task_url, job_info)
        job_values = super()._analysis_job_results(task_url, job_info)
        #print(job_values)
        if output_name is not None:
            itemid = job_values['resultLayer']['itemId']
            item = arcgis.gis.Item(self._gis, itemid)
            return item
        else:
            # Feature Collection
            return arcgis.features.FeatureCollection(job_values['resultLayer'])


    def summarize_nearby(self,
                       sum_nearby_layer,
                       summary_layer,
                       near_type="StraightLine",
                       distances=[],
                       units="Meters",
                       time_of_day=None,
                       time_zone_for_time_of_day="GeoLocal",
                       return_boundaries=True,
                       sum_shape=True,
                       shape_units=None,
                       summary_fields=[],
                       group_by_field=None,
                       minority_majority=False,
                       percent_shape=False,
                       output_name=None,
                       context=None):
        """
        The SummarizeNearby task finds features that are within a specified distance of features in the input layer. Distance can be measured as a straight-line distance, a drive-time distance (for example, within 10 minutes), or a drive distance (within 5 kilometers). Statistics are then calculated for the nearby features. For example:Calculate the total population within five minutes of driving time of a proposed new store location.Calculate the number of freeway access ramps within a one-mile driving distance of a proposed new store location to use as a measure of store accessibility.

        Parameters
        ----------
        sum_nearby_layer : Required layer (see Feature Input in documentation)
            Point, line, or polygon features from which distances will be measured to features in the summarizeLayer.
        summary_layer : Required layer (see Feature Input in documentation)
            Point, line, or polygon features. Features in this layer that are within the specified distance to features in the sumNearbyLayer will be summarized.
        near_type : Optional string
            Defines what kind of distance measurement you want to use to create areas around the nearbyLayer features.
        distances : Required list of floats
            An array of double values that defines the search distance for creating areas mentioned above
        units : Optional string
            The linear unit for distances parameter above. Eg. Miles, Kilometers, Minutes Seconds etc
        time_of_day : Optional datetime.date
            For timeOfDay, set the time and day according to the number of milliseconds elapsed since the Unix epoc (January 1, 1970 UTC). When specified and if relevant for the nearType parameter, the traffic conditions during the time of the day will be considered.
        time_zone_for_time_of_day : Optional string
            Determines if the value specified for timeOfDay is specified in UTC or in a time zone that is local to the location of the origins.
        return_boundaries : Optional bool
            If true, will return a result layer of areas that contain the requested summary information.  The resulting areas are defined by the specified nearType.  For example, if using a StraightLine of 5 miles, your result will contain areas with a 5 mile radius around the input features and specified summary information.If false, the resulting layer will return the same features as the input analysis layer with requested summary information.
        sum_shape : Optional bool
            A boolean value that instructs the task to calculate count of points, length of lines or areas of polygons of the summaryLayer within each polygon in sumWithinLayer.
        shape_units : Optional string
            Specify units to summarize the length or areas when sumShape is set to true. Units is not required to summarize points.
        summary_fields : Optional list of strings
            A list of field names and statistical summary type that you wish to calculate for all features in the summaryLayer that are within each polygon in the sumWithinLayer . Eg: ["fieldname1 summary", "fieldname2 summary"]
        group_by_field : Optional string
            Specify a field from the summaryLayer features to calculate statistics separately for each unique value of the field.
        minority_majority : Optional bool
            This boolean parameter is applicable only when a groupByField is specified. If true, the minority (least dominant) or the majority (most dominant) attribute values within each group, within each boundary will be calculated.
        percent_shape : Optional bool
            This boolean parameter is applicable only when a groupByField is specified. If set to true, the percentage of shape (eg. length for lines) for each unique groupByField value is calculated.
        output_name : Optional string
            Additional properties such as output feature service name.
        context : Optional string
            Additional settings such as processing extent and output spatial reference.

        Returns
        -------
        dict with the following keys:
           "result_layer" : layer (FeatureCollection)
           "group_by_summary" : layer (FeatureCollection)
        """

        task ="SummarizeNearby"

        params = {}

        params["sumNearbyLayer"] = super()._feature_input(sum_nearby_layer)
        params["summaryLayer"] = super()._feature_input(summary_layer)
        if near_type is not None:
            params["nearType"] = near_type
        params["distances"] = distances
        if units is not None:
            params["units"] = units
        if time_of_day is not None:
            params["timeOfDay"] = time_of_day
        if time_zone_for_time_of_day is not None:
            params["timeZoneForTimeOfDay"] = time_zone_for_time_of_day
        if return_boundaries is not None:
            params["returnBoundaries"] = return_boundaries
        if sum_shape is not None:
            params["sumShape"] = sum_shape
        if shape_units is not None:
            params["shapeUnits"] = shape_units
        if summary_fields is not None:
            params["summaryFields"] = summary_fields
        if group_by_field is not None:
            params["groupByField"] = group_by_field
        if minority_majority is not None:
            params["minorityMajority"] = minority_majority
        if percent_shape is not None:
            params["percentShape"] = percent_shape
        if output_name is not None:
            params["outputName"] = {"serviceProperties": {"name": output_name }}
        if context is not None:
            params["context"] = context

        task_url, job_info = super()._analysis_job(task, params)

        job_info = super()._analysis_job_status(task_url, job_info)
        job_values = super()._analysis_job_results(task_url, job_info)
        #print(job_values)
        if output_name is not None:
            itemid = job_values['resultLayer']['itemId']
            item = arcgis.gis.Item(self._gis, itemid)
            return item
        else:
            # Feature Collection

            result_layer = arcgis.features.FeatureCollection(job_values['resultLayer'])

            group_by_summary = arcgis.features.FeatureCollection(job_values['groupBySummary'])
            return { "result_layer":result_layer, "group_by_summary":group_by_summary, }


    def create_viewshed(self,
                       input_layer,
                       dem_resolution="Finest",
                       maximum_distance=None,
                       max_distance_units="Meters",
                       observer_height=None,
                       observer_height_units="Meters",
                       target_height=None,
                       target_height_units="Meters",
                       generalize=True,
                       output_name=None,
                       context=None):
        """


        Parameters
        ----------
        input_layer : Required layer (see Feature Input in documentation)

        dem_resolution : Optional string

        maximum_distance : Optional float

        max_distance_units : Optional string

        observer_height : Optional float

        observer_height_units : Optional string

        target_height : Optional float

        target_height_units : Optional string

        generalize : Optional bool

        output_name : Optional string

        context : Optional string


        Returns
        -------
        viewshed_layer : layer (FeatureCollection)
        """

        task ="CreateViewshed"

        params = {}

        params["inputLayer"] = super()._feature_input(input_layer)
        if dem_resolution is not None:
            params["demResolution"] = dem_resolution
        if maximum_distance is not None:
            params["maximumDistance"] = maximum_distance
        if max_distance_units is not None:
            params["maxDistanceUnits"] = max_distance_units
        if observer_height is not None:
            params["observerHeight"] = observer_height
        if observer_height_units is not None:
            params["observerHeightUnits"] = observer_height_units
        if target_height is not None:
            params["targetHeight"] = target_height
        if target_height_units is not None:
            params["targetHeightUnits"] = target_height_units
        if generalize is not None:
            params["generalize"] = generalize
        if output_name is not None:
            params["outputName"] = {"serviceProperties": {"name": output_name }}
        if context is not None:
            params["context"] = context

        task_url, job_info = super()._analysis_job(task, params)

        job_info = super()._analysis_job_status(task_url, job_info)
        job_values = super()._analysis_job_results(task_url, job_info)
        #print(job_values)
        if output_name is not None:
            itemid = job_values['viewshedLayer']['itemId']
            item = arcgis.gis.Item(self._gis, itemid)
            return item
        else:
            # Feature Collection
            return arcgis.features.FeatureCollection(job_values['viewshedLayer'])


    def find_similar_locations(self,
                       input_layer,
                       search_layer,
                       analysis_fields=[],
                       input_query=None,
                       number_of_results=0,
                       output_name=None,
                       context=None):
        """


        Parameters
        ----------
        input_layer : Required layer (see Feature Input in documentation)

        search_layer : Required layer (see Feature Input in documentation)

        analysis_fields : Required list of strings

        input_query : Optional string

        number_of_results : Optional int

        output_name : Optional string

        context : Optional string


        Returns
        -------
        dict with the following keys:
           "similar_result_layer" : layer (FeatureCollection)
           "process_info" : layer (FeatureCollection)
        """

        task ="FindSimilarLocations"

        params = {}

        params["inputLayer"] = super()._feature_input(input_layer)
        params["searchLayer"] = super()._feature_input(search_layer)
        params["analysisFields"] = analysis_fields
        if input_query is not None:
            params["inputQuery"] = input_query
        if number_of_results is not None:
            params["numberOfResults"] = number_of_results
        if output_name is not None:
            params["outputName"] = {"serviceProperties": {"name": output_name }}
        if context is not None:
            params["context"] = context

        task_url, job_info = super()._analysis_job(task, params)

        job_info = super()._analysis_job_status(task_url, job_info)
        job_values = super()._analysis_job_results(task_url, job_info)
        #print(job_values)
        if output_name is not None:
            itemid = job_values['similarResultLayer']['itemId']
            item = arcgis.gis.Item(self._gis, itemid)
            return item
        else:
            # Feature Collection

            similar_result_layer = arcgis.features.FeatureCollection(job_values['similarResultLayer'])

            process_info = arcgis.features.FeatureCollection(job_values['processInfo'])
            return { "similar_result_layer":similar_result_layer, "process_info":process_info, }


    def create_watersheds(self,
                       input_layer,
                       search_distance=None,
                       search_units="Meters",
                       source_database="FINEST",
                       generalize=True,
                       output_name=None,
                       context=None):
        """


        Parameters
        ----------
        input_layer : Required layer (see Feature Input in documentation)

        search_distance : Optional float

        search_units : Optional string

        source_database : Optional string

        generalize : Optional bool

        output_name : Optional string

        context : Optional string


        Returns
        -------
        dict with the following keys:
           "snap_pour_pts_layer" : layer (FeatureCollection)
           "watershed_layer" : layer (FeatureCollection)
        """

        task ="CreateWatersheds"

        params = {}

        params["inputLayer"] = super()._feature_input(input_layer)
        if search_distance is not None:
            params["searchDistance"] = search_distance
        if search_units is not None:
            params["searchUnits"] = search_units
        if source_database is not None:
            params["sourceDatabase"] = source_database
        if generalize is not None:
            params["generalize"] = generalize
        if output_name is not None:
            params["outputName"] = {"serviceProperties": {"name": output_name }}
        if context is not None:
            params["context"] = context

        task_url, job_info = super()._analysis_job(task, params)

        job_info = super()._analysis_job_status(task_url, job_info)
        job_values = super()._analysis_job_results(task_url, job_info)
        #print(job_values)
        if output_name is not None:
            itemid = job_values['snapPourPtsLayer']['itemId']
            item = arcgis.gis.Item(self._gis, itemid)
            return item
        else:
            # Feature Collection

            snap_pour_pts_layer = arcgis.features.FeatureCollection(job_values['snapPourPtsLayer'])

            watershed_layer = arcgis.features.FeatureCollection(job_values['watershedLayer'])
            return { "snap_pour_pts_layer":snap_pour_pts_layer, "watershed_layer":watershed_layer, }


    def find_nearest(self,
                       analysis_layer,
                       near_layer,
                       measurement_type="StraightLine",
                       max_count=100,
                       search_cutoff=2147483647,
                       search_cutoff_units=None,
                       time_of_day=None,
                       time_zone_for_time_of_day="GeoLocal",
                       output_name=None,
                       context=None):
        """
        Measures the straight-line distance, driving distance, or driving time from features in the analysis layer to features in the near layer, and copies the nearest features in the near layer to a new layer. Returns a layer containing the nearest features and a line layer that links the start locations to their nearest locations.

        Parameters
        ----------
        analysis_layer : Required layer (see Feature Input in documentation)
            For each feature in this layer, the task finds the nearest features from the nearLayer.
        near_layer : Required layer (see Feature Input in documentation)
            The features from which the nearest locations are found.
        measurement_type : Required string
            The nearest locations can be determined by measuring straight-line distance, driving distance, or driving time
        max_count : Optional int
            The maximum number of near locations to find for each feature in analysisLayer.
        search_cutoff : Optional float
            Limits the search range to this value
        search_cutoff_units : Optional string
            The units for the value specified as searchCutoff
        time_of_day : Optional datetime.date
            When measurementType is DrivingTime, this value specifies the time of day to be used for driving time calculations based on traffic.
        time_zone_for_time_of_day : Optional string

        output_name : Optional string
            Additional properties such as output feature service name
        context : Optional string
            Additional settings such as processing extent and output spatial reference

        Returns
        -------
        dict with the following keys:
           "nearest_layer" : layer (FeatureCollection)
           "connecting_lines_layer" : layer (FeatureCollection)
        """

        task ="FindNearest"

        params = {}

        params["analysisLayer"] = super()._feature_input(analysis_layer)
        params["nearLayer"] = super()._feature_input(near_layer)
        params["measurementType"] = measurement_type
        if max_count is not None:
            params["maxCount"] = max_count
        if search_cutoff is not None:
            params["searchCutoff"] = search_cutoff
        if search_cutoff_units is not None:
            params["searchCutoffUnits"] = search_cutoff_units
        if time_of_day is not None:
            params["timeOfDay"] = time_of_day
        if time_zone_for_time_of_day is not None:
            params["timeZoneForTimeOfDay"] = time_zone_for_time_of_day
        if output_name is not None:
            params["outputName"] = {"serviceProperties": {"name": output_name }}
        if context is not None:
            params["context"] = context

        task_url, job_info = super()._analysis_job(task, params)

        job_info = super()._analysis_job_status(task_url, job_info)
        job_values = super()._analysis_job_results(task_url, job_info)
        #print(job_values)
        if output_name is not None:
            itemid = job_values['nearestLayer']['itemId']
            item = arcgis.gis.Item(self._gis, itemid)
            return item
        else:
            # Feature Collection

            nearest_layer = arcgis.features.FeatureCollection(job_values['nearestLayer'])

            connecting_lines_layer = arcgis.features.FeatureCollection(job_values['connectingLinesLayer'])
            return { "nearest_layer":nearest_layer, "connecting_lines_layer":connecting_lines_layer, }


    def plan_routes(self,
                       stops_layer,
                       route_count,
                       max_stops_per_route,
                       route_start_time,
                       start_layer,
                       start_layer_route_id_field=None,
                       return_to_start=True,
                       end_layer=None,
                       end_layer_route_id_field=None,
                       travel_mode="Driving",
                       stop_service_time=0,
                       max_route_time=525600,
                       output_name=None,
                       context=None):
        """


        Parameters
        ----------
        stops_layer : Required layer (see Feature Input in documentation)

        route_count : Required int

        max_stops_per_route : Required int

        route_start_time : Required datetime.date

        start_layer : Required layer (see Feature Input in documentation)

        start_layer_route_id_field : Optional string

        return_to_start : Optional bool

        end_layer : Optional layer (see Feature Input in documentation)

        end_layer_route_id_field : Optional string

        travel_mode : Optional string

        stop_service_time : Optional float

        max_route_time : Optional float

        output_name : Optional string

        context : Optional string


        Returns
        -------
        dict with the following keys:
           "routes_layer" : layer (FeatureCollection)
           "assigned_stops_layer" : layer (FeatureCollection)
           "unassigned_stops_layer" : layer (FeatureCollection)
        """

        task ="PlanRoutes"

        params = {}

        params["stopsLayer"] = super()._feature_input(stops_layer)
        params["routeCount"] = route_count
        params["maxStopsPerRoute"] = max_stops_per_route
        params["routeStartTime"] = route_start_time
        params["startLayer"] = super()._feature_input(start_layer)
        if start_layer_route_id_field is not None:
            params["startLayerRouteIDField"] = start_layer_route_id_field
        if return_to_start is not None:
            params["returnToStart"] = return_to_start
        if end_layer is not None:
            params["endLayer"] = super()._feature_input(end_layer)
        if end_layer_route_id_field is not None:
            params["endLayerRouteIDField"] = end_layer_route_id_field
        if travel_mode is not None:
            params["travelMode"] = travel_mode
        if stop_service_time is not None:
            params["stopServiceTime"] = stop_service_time
        if max_route_time is not None:
            params["maxRouteTime"] = max_route_time
        if output_name is not None:
            params["outputName"] = {"serviceProperties": {"name": output_name }}
        if context is not None:
            params["context"] = context

        task_url, job_info = super()._analysis_job(task, params)

        job_info = super()._analysis_job_status(task_url, job_info)
        job_values = super()._analysis_job_results(task_url, job_info)
        #print(job_values)
        if output_name is not None:
            itemid = job_values['routesLayer']['itemId']
            item = arcgis.gis.Item(self._gis, itemid)
            return item
        else:
            # Feature Collection

            routes_layer = arcgis.features.FeatureCollection(job_values['routesLayer'])

            assigned_stops_layer = arcgis.features.FeatureCollection(job_values['assignedStopsLayer'])

            unassigned_stops_layer = arcgis.features.FeatureCollection(job_values['unassignedStopsLayer'])
            return { "routes_layer":routes_layer, "assigned_stops_layer":assigned_stops_layer, "unassigned_stops_layer":unassigned_stops_layer, }


    def trace_downstream(self,
                       input_layer,
                       split_distance=None,
                       split_units="Kilometers",
                       max_distance=None,
                       max_distance_units="Kilometers",
                       bounding_polygon_layer=None,
                       source_database=None,
                       generalize=True,
                       output_name=None,
                       context=None):
        """


        Parameters
        ----------
        input_layer : Required layer (see Feature Input in documentation)

        split_distance : Optional float

        split_units : Optional string

        max_distance : Optional float

        max_distance_units : Optional string

        bounding_polygon_layer : Optional layer (see Feature Input in documentation)

        source_database : Optional string

        generalize : Optional bool

        output_name : Optional string

        context : Optional string


        Returns
        -------
        trace_layer : layer (FeatureCollection)
        """

        task ="TraceDownstream"

        params = {}

        params["inputLayer"] = super()._feature_input(input_layer)
        if split_distance is not None:
            params["splitDistance"] = split_distance
        if split_units is not None:
            params["splitUnits"] = split_units
        if max_distance is not None:
            params["maxDistance"] = max_distance
        if max_distance_units is not None:
            params["maxDistanceUnits"] = max_distance_units
        if bounding_polygon_layer is not None:
            params["boundingPolygonLayer"] = super()._feature_input(bounding_polygon_layer)
        if source_database is not None:
            params["sourceDatabase"] = source_database
        if generalize is not None:
            params["generalize"] = generalize
        if output_name is not None:
            params["outputName"] = {"serviceProperties": {"name": output_name }}
        if context is not None:
            params["context"] = context

        task_url, job_info = super()._analysis_job(task, params)

        job_info = super()._analysis_job_status(task_url, job_info)
        job_values = super()._analysis_job_results(task_url, job_info)
        #print(job_values)
        if output_name is not None:
            itemid = job_values['traceLayer']['itemId']
            item = arcgis.gis.Item(self._gis, itemid)
            return item
        else:
            # Feature Collection
            return arcgis.features.FeatureCollection(job_values['traceLayer'])


    def connect_origins_to_destinations(self,
                       origins_layer,
                       destinations_layer,
                       measurement_type="DrivingTime",
                       origins_layer_route_id_field=None,
                       destinations_layer_route_id_field=None,
                       time_of_day=None,
                       time_zone_for_time_of_day="GeoLocal",
                       output_name=None,
                       context=None):
        """
        Calculates routes between pairs of points.

        Parameters
        ----------
        origins_layer : Required layer (see Feature Input in documentation)
            The routes start from points in the origins layer.
        destinations_layer : Required layer (see Feature Input in documentation)
            The routes end at points in the destinations layer.
        measurement_type : Required string
            The routes can be determined by measuring travel distance or travel time along street network using different travel modes or by measuring straight line distance.
        origins_layer_route_id_field : Optional string
            The field in the origins layer containing the IDs that are used to match an origin with a destination.
        destinations_layer_route_id_field : Optional string
            The field in the destinations layer containing the IDs that are used to match an origin with a destination.
        time_of_day : Optional datetime.date
            When measurementType is DrivingTime, this value specifies the time of day to be used for driving time calculations based on traffic. WalkingTime and TruckingTime measurementType do not support calculations based on traffic.
        time_zone_for_time_of_day : Optional string
            Determines if the value specified for timeOfDay is specified in UTC or in a time zone that is local to the location of the origins.
        output_name : Optional string
            Additional properties such as output feature service name.
        context : Optional string
            Additional settings such as processing extent and output spatial reference.

        Returns
        -------
        dict with the following keys:
           "routes_layer" : layer (FeatureCollection)
           "unassigned_origins_layer" : layer (FeatureCollection)
           "unassigned_destinations_layer" : layer (FeatureCollection)
        """

        task ="ConnectOriginsToDestinations"

        params = {}

        params["originsLayer"] = super()._feature_input(origins_layer)
        params["destinationsLayer"] = super()._feature_input(destinations_layer)
        params["measurementType"] = measurement_type
        if origins_layer_route_id_field is not None:
            params["originsLayerRouteIDField"] = origins_layer_route_id_field
        if destinations_layer_route_id_field is not None:
            params["destinationsLayerRouteIDField"] = destinations_layer_route_id_field
        if time_of_day is not None:
            params["timeOfDay"] = time_of_day
        if time_zone_for_time_of_day is not None:
            params["timeZoneForTimeOfDay"] = time_zone_for_time_of_day
        if output_name is not None:
            params["outputName"] = {"serviceProperties": {"name": output_name }}
        if context is not None:
            params["context"] = context

        task_url, job_info = super()._analysis_job(task, params)

        job_info = super()._analysis_job_status(task_url, job_info)
        job_values = super()._analysis_job_results(task_url, job_info)
        #print(job_values)
        if output_name is not None:
            itemid = job_values['routesLayer']['itemId']
            item = arcgis.gis.Item(self._gis, itemid)
            return item
        else:
            # Feature Collection

            routes_layer = arcgis.features.FeatureCollection(job_values['routesLayer'])

            unassigned_origins_layer = arcgis.features.FeatureCollection(job_values['unassignedOriginsLayer'])

            unassigned_destinations_layer = arcgis.features.FeatureCollection(job_values['unassignedDestinationsLayer'])
            return { "routes_layer":routes_layer, "unassigned_origins_layer":unassigned_origins_layer, "unassigned_destinations_layer":unassigned_destinations_layer, }

    def create_route_layers(self,
                       route_data_item,
                       delete_route_data_item=False,
                       output_name=None):
        """


        Parameters
        ----------
        route_data_item : Required item

        delete_route_data_item : Required boolean

        output_name: Optional dict

        Returns
        -------
        route_layers : list (items)
        """

        task ="CreateRouteLayers"

        params = {}

        params["routeData"] = {"itemId": route_data_item.itemid}
        params["deleteRouteData"] = delete_route_data_item
        if output_name:
            params["outputName"] = output_name

        task_url, job_info = super()._analysis_job(task, params)
        job_info = super()._analysis_job_status(task_url, job_info)
        job_values = super()._analysis_job_results(task_url, job_info)
        route_layer_items = []

        for itemid in job_values["routeLayers"]["items"]:
            item = arcgis.gis.Item(self._gis, itemid)
            route_layer_items.append(item)

        return route_layer_items

class _RasterAnalysisTools(_AsyncService):
    "Exposes the Raster Analysis Tools. The RasterAnalysisTools service is used by ArcGIS Server to provide distributed raster analysis."

    def __init__(self, url, gis):
        """
        Constructs a client to the service given it's url from ArcGIS Online or Portal.
        """
        super(_RasterAnalysisTools, self).__init__(url, gis)

    def _create_output_image_service(self, output_name, task):
        ok = self._gis.content.is_service_name_available(output_name, "Image Service")
        if not ok:
            raise RuntimeError("An Image Service by this name already exists: " + output_name)

        createParameters = {
                "name": output_name,
                "description": "",
                "capabilities": "Image",
                "properties": {
                    "path": "@",
                    "description": "",
                    "copyright": ""
                    }
                }

        output_service = self._gis.content.create_service(output_name, create_params=createParameters, service_type="imageService")
        description = "Image Service generated from running the " + task + " tool."
        item_properties = {
                "description" : description,
                "tags" : "Analysis Result, " + task,
                "snippet": "Analysis Image Service generated from " + task
                }
        output_service.update(item_properties)
        return output_service

    def generate_raster(self,
                       raster_function,
                       function_arguments=None,
                       output_raster=None,
                       output_raster_properties=None,
                       context=None,
                       num_instances=None):
        """


        Parameters
        ----------
        raster_function : Required, see http://resources.arcgis.com/en/help/rest/apiref/israsterfunctions.html

        function_arguments : Optional,  for specifying input Raster alone, portal Item can be passed

        output_raster : Optional. If not provided, an Image Service is created by the method and used as the output raster.
            You can pass in an existing Image Service Item from your GIS to use that instead.
            Alternatively, you can pass in the name of the output Image Service that should be created by this method to be used as the output for the tool.
            A RuntimeError is raised if a service by that name already exists

        output_raster_properties : Optional string

        context : Optional

        num_instances : Optional, number of instances to use


        Returns
        -------
        out_raster : Image Service item
        """

        task ="GenerateRaster"

        output_service = None

        if output_raster is None:
            output_ras_name = 'GeneratedRasterProduct' + '_' + _id_generator()
            output_service = self._create_output_image_service(output_ras_name, task)
        elif isinstance(output_raster, str):
            output_service = self._create_output_image_service(output_raster, task)
        elif isinstance(output_raster, Item):
            output_service = output_raster
        else:
            raise TypeError("output_raster should be a string (service name) or Item")

        output_raster =  { 'itemId' : output_service.itemid }

        if isinstance(function_arguments, arcgis.gis.Item):
            if function_arguments.type.lower() == 'image service':
                function_arguments =  { "Raster":{"itemId": function_arguments.itemid } }
            else:
                raise TypeError("The item type of function_arguments must be an image service")

        params = {}

        params["rasterFunction"] = raster_function
        params["outputRaster"] = output_raster
        if function_arguments is not None:
            params["functionArguments"] = function_arguments
        if output_raster_properties is not None:
            params["outputRasterProperties"] = output_raster_properties
        if context is not None:
            params["context"] = context
        if num_instances is not None:
            params["numInstances"] = num_instances

        task_url, job_info = super()._analysis_job(task, params)

        job_info = super()._analysis_job_status(task_url, job_info)
        job_values = super()._analysis_job_results(task_url, job_info)
        #print(job_values)
        item_properties = {
            "properties":{
                "jobUrl": task_url + '/jobs/' + job_info['jobId'],
                "jobType": "GPServer",
                "jobId": job_info['jobId'],
                "jobStatus": "completed"
                }
            }
        output_service.update(item_properties)
        return output_service


    def rasterize(self,
                       input_table,
                       output_raster,
                       raster_info,
                       value_field=None,
                       context=None,
                       num_instances=None):
        """


        Parameters
        ----------
        input_table : Required string

        output_raster : Required string

        raster_info : Required string

        value_field : Optional string

        context : Optional string

        num_instances : Optional string


        Returns
        -------
        out_raster : layer
        """

        task ="Rasterize"

        output_service = None

        if output_raster is None:
            output_ras_name = 'GeneratedRasterProduct' + '_' + _id_generator()
            output_service = self._create_output_image_service(output_ras_name, task)
        elif isinstance(output_raster, str):
            output_service = self._create_output_image_service(output_raster, task)
        elif isinstance(output_raster, Item):
            output_service = output_raster
        else:
            raise TypeError("output_raster should be a string (service name) or Item")

        output_raster =  { 'itemId' : output_service.itemid }

        params = {}

        params["inputTable"] = input_table
        params["outputRaster"] = output_raster
        params["rasterInfo"] = raster_info
        if value_field is not None:
            params["valueField"] = value_field
        if context is not None:
            params["context"] = context
        if num_instances is not None:
            params["numInstances"] = num_instances

        task_url, job_info = super()._analysis_job(task, params)

        job_info = super()._analysis_job_status(task_url, job_info)
        job_values = super()._analysis_job_results(task_url, job_info)
        #print(job_values)
        item_properties = {
                "properties":{
                    "jobUrl": task_url + '/jobs/' + job_info['jobId'],
                    "jobType": "GPServer",
                    "jobId": job_info['jobId'],
                    "jobStatus": "completed"
                    }
                }
        output_service.update(item_properties)
        return output_service



    def interpolate(self,
                       input_table,
                       output_raster,
                       raster_info,
                       value_field=None,
                       interpolation_method="Nearest",
                       radius=None,
                       context=None,
                       num_instances=None):
        """


        Parameters
        ----------
        input_table : Required string

        output_raster : Required string

        raster_info : Required string

        value_field : Optional string

        interpolation_method : Optional string
            One of the following: ['Nearest', 'Bilinear', 'Linear', 'NaturalNeighbor']
        radius : Optional float

        context : Optional string

        num_instances : Optional string


        Returns
        -------
        out_raster : layer (Feature Service item)
        """

        task ="Interpolate"
        output_service = None

        if output_raster is None:
            output_ras_name = 'GeneratedRasterProduct' + '_' + _id_generator()
            output_service = self._create_output_image_service(output_ras_name, task)
        elif isinstance(output_raster, str):
            output_service = self._create_output_image_service(output_raster, task)
        elif isinstance(output_raster, Item):
            output_service = output_raster
        else:
            raise TypeError("output_raster should be a string (service name) or Item")

        output_raster =  { 'itemId' : output_service.itemid }


        params = {}

        params["inputTable"] = input_table
        params["outputRaster"] = output_raster
        params["rasterInfo"] = raster_info
        if value_field is not None:
            params["valueField"] = value_field
        if interpolation_method is not None:
            params["interpolationMethod"] = interpolation_method
        if radius is not None:
            params["radius"] = radius
        if context is not None:
            params["context"] = context
        if num_instances is not None:
            params["numInstances"] = num_instances

        task_url, job_info = super()._analysis_job(task, params)

        job_info = super()._analysis_job_status(task_url, job_info)
        job_values = super()._analysis_job_results(task_url, job_info)
        #print(job_values)
        item_properties = {
                "properties":{
                    "jobUrl": task_url + '/jobs/' + job_info['jobId'],
                    "jobType": "GPServer",
                    "jobId": job_info['jobId'],
                    "jobStatus": "completed"
                    }
                }
        output_service.update(item_properties)
        return output_service


    def copy_raster(self,
                       input_raster,
                       output_raster,
                       output_cellsize=None,
                       resampling_method="NEAREST",
                       clipping_geometry=None,
                       context=None,
                       num_instances=None):
        """


        Parameters
        ----------
        input_raster : Required string

        output_raster : Required string

        output_cellsize : Optional string

        resampling_method : Optional string
            One of the following: ['NEAREST', 'BILINEAR', 'CUBIC', 'MAJORITY']
        clipping_geometry : Optional string

        context : Optional string

        num_instances : Optional string


        Returns
        -------
        out_raster : layer
        """

        task ="CopyRaster"
        output_service = None

        if output_raster is None:
            output_ras_name = 'GeneratedRasterProduct' + '_' + _id_generator()
            output_service = self._create_output_image_service(output_ras_name, task)
        elif isinstance(output_raster, str):
            output_service = self._create_output_image_service(output_raster, task)
        elif isinstance(output_raster, Item):
            output_service = output_raster
        else:
            raise TypeError("output_raster should be a string (service name) or Item")

        output_raster =  { 'itemId' : output_service.itemid }

        params = {}

        params["inputRaster"] = input_raster
        params["outputRaster"] = output_raster
        if output_cellsize is not None:
            params["outputCellsize"] = output_cellsize
        if resampling_method is not None:
            params["resamplingMethod"] = resampling_method
        if clipping_geometry is not None:
            params["clippingGeometry"] = clipping_geometry
        if context is not None:
            params["context"] = context
        if num_instances is not None:
            params["numInstances"] = num_instances

        task_url, job_info = super()._analysis_job(task, params)

        job_info = super()._analysis_job_status(task_url, job_info)
        job_values = super()._analysis_job_results(task_url, job_info)
        #print(job_values)
        item_properties = {
                "properties":{
                    "jobUrl": task_url + '/jobs/' + job_info['jobId'],
                    "jobType": "GPServer",
                    "jobId": job_info['jobId'],
                    "jobStatus": "completed"
                    }
                }
        output_service.update(item_properties)
        return output_service

    def summarize_raster_within(self,
                       input_zone_layer,
                       zone_field,
                       input_raster_layerto_summarize,
                       output_name,
                       statistic_type="Mean",
                       ignore_missing_values=True,
                       context=None):
        """


        Parameters
        ----------
        input_zone_layer : Required layer

        zone_field : Required string

        input_raster_layerto_summarize : Required string

        output_name : Required string

        statistic_type : Optional string
            One of the following: ['Mean', 'Majority', 'Maximum', 'Median', 'Minimum', 'Minority', 'Range', 'STD', 'SUM', 'Variety']
        ignore_missing_values : Optional bool

        context : Optional string


        Returns
        -------
        out_raster : layer
        """

        task ="Summarize Raster Within"

        output_service = None

        if output_name is None:
            output_ras_name = 'GeneratedRasterProduct' + '_' + _id_generator()
            output_service = self._create_output_image_service(output_ras_name, task)
        elif isinstance(output_name, str):
            output_service = self._create_output_image_service(output_name, task)
        elif isinstance(output_name, Item):
            output_service = output_raster
        else:
            raise TypeError("output_raster should be a string (service name) or Item")

        output_raster =  { 'itemId' : output_service.itemid }


        params = {}

        params["inputZoneLayer"] = super()._feature_input(input_zone_layer)
        params["zoneField"] = zone_field
        params["inputRasterLayertoSummarize"] = input_raster_layerto_summarize

        params["outputRaster"] = output_raster
        params["outputName"] = json.dumps({"serviceProperties": {"name" : output_name, "serviceUrl" : output_service.url}, "itemProperties": {"itemId" : output_service.itemid}})
        if statistic_type is not None:
            params["statisticType"] = statistic_type
        if ignore_missing_values is not None:
            params["ignoreMissingValues"] = ignore_missing_values
        if context is not None:
            params["context"] = context

        task_url, job_info = super()._analysis_job(task, params)

        job_info = super()._analysis_job_status(task_url, job_info)
        job_values = super()._analysis_job_results(task_url, job_info)
        #print(job_values)
        item_properties = {
                "properties":{
                    "jobUrl": task_url + '/jobs/' + job_info['jobId'],
                    "jobType": "GPServer",
                    "jobId": job_info['jobId'],
                    "jobStatus": "completed"
                    }
                }
        output_service.update(item_properties)
        return output_service


    def density(self,
                       input_feature_class,
                       output_raster,
                       value_field,
                       raster_info=None,
                       method="Point_Density",
                       neighborhood=None,
                       area_units="Square_map_units",
                       context=None):
        """


        Parameters
        ----------
        input_feature_class : Required string

        output_raster : Required string

        value_field : Required string

        raster_info : Optional string

        method : Optional string
            One of the following: ['Point_Density', 'Line_Density', 'Kernel_Density_Densities_Planar', 'Kernel_Density_Densities_Geodesic', 'Kernel_Density_Counts_Planar', 'Kernel_Density_Counts_Geodesic']
        neighborhood : Optional string

        area_units : Optional string
            One of the following: ['Square_map_units', 'Square_miles', 'Square_kilometers', 'Arces', 'Hectares', 'Square_yards', 'Square_feet', 'Square_inches', 'Square_meters', 'Square_centimeters', 'Square_millimeters']
        context : Optional string


        Returns
        -------
        out_raster : layer (Feature Service item)
        """

        task ="Density"
        output_service = None

        if output_raster is None:
            output_ras_name = 'GeneratedRasterProduct' + '_' + _id_generator()
            output_service = self._create_output_image_service(output_ras_name, task)
        elif isinstance(output_raster, str):
            output_service = self._create_output_image_service(output_raster, task)
        elif isinstance(output_raster, Item):
            output_service = output_raster
        else:
            raise TypeError("output_raster should be a string (service name) or Item")

        output_raster =  { 'itemId' : output_service.itemid }


        params = {}

        params["inputFeatureClass"] = input_feature_class
        params["outputRaster"] = output_raster
        params["valueField"] = value_field
        if raster_info is not None:
            params["rasterInfo"] = raster_info
        if method is not None:
            params["method"] = method
        if neighborhood is not None:
            params["neighborhood"] = neighborhood
        if area_units is not None:
            params["areaUnits"] = area_units
        if context is not None:
            params["context"] = context

        task_url, job_info = super()._analysis_job(task, params)

        job_info = super()._analysis_job_status(task_url, job_info)
        job_values = super()._analysis_job_results(task_url, job_info)
        item_properties = {
                "properties":{
                    "jobUrl": task_url + '/jobs/' + job_info['jobId'],
                    "jobType": "GPServer",
                    "jobId": job_info['jobId'],
                    "jobStatus": "completed"
                    }
                }
        output_service.update(item_properties)
        return output_service


    def classify(self,
                       input_raster,
                       input_classifier_definition,
                       output_raster,
                       additional_input_raster=None,
                       number_of_instances="4"):
        """


        Parameters
        ----------
        input_raster : Required string

        input_classifier_definition : Required string

        output_raster : Required string

        additional_input_raster : Optional string

        number_of_instances : Required string


        Returns
        -------
        """

        task ="Classify"

        output_service = None

        if output_raster is None:
            output_ras_name = 'GeneratedRasterProduct' + '_' + _id_generator()
            output_service = self._create_output_image_service(output_ras_name, task)
        elif isinstance(output_raster, str):
            output_service = self._create_output_image_service(output_raster, task)
        elif isinstance(output_raster, Item):
            output_service = output_raster
        else:
            raise TypeError("output_raster should be a string (service name) or Item")

        output_raster =  { 'itemId' : output_service.itemid }

        params = {}

        params["Input_Raster"] = input_raster
        params["Input_Classifier_Definition"] = input_classifier_definition
        params["Output_Classified_Raster"] = output_raster
        if additional_input_raster is not None:
            params["Additional_Input_Raster"] = additional_input_raster
        params["Number_of_Instances"] = number_of_instances

        task_url, job_info = super()._analysis_job(task, params)

        job_info = super()._analysis_job_status(task_url, job_info)
        job_values = super()._analysis_job_results(task_url, job_info)
        #print(job_values)
        item_properties = {
            "properties":{
                "jobUrl": task_url + '/jobs/' + job_info['jobId'],
                "jobType": "GPServer",
                "jobId": job_info['jobId'],
                "jobStatus": "completed"
                }
            }
        output_service.update(item_properties)
        return output_service


    def segment_mean_shift(self,
                       input_raster,
                       output_raster,
                       spectral_detail="15.5",
                       spatial_detail="15",
                       minimum_segment_size_in_pixels="20",
                       band_indexes="1,2,3",
                       remove_tiiling_artifacts="false",
                       number_of_instances="4"):
        """


        Parameters
        ----------
        input_raster : Required string

        output_raster : Required string

        spectral_detail : Required string

        spatial_detail : Required string

        minimum_segment_size_in_pixels : Required string

        band_indexes : Required string

        remove_tiiling_artifacts : Required string

        number_of_instances : Required string


        Returns
        -------
        """

        task ="Segment Mean Shift"

        output_service = None

        if output_raster is None:
            output_ras_name = 'GeneratedRasterProduct' + '_' + _id_generator()
            output_service = self._create_output_image_service(output_ras_name, task)
        elif isinstance(output_raster, str):
            output_service = self._create_output_image_service(output_raster, task)
        elif isinstance(output_raster, Item):
            output_service = output_raster
        else:
            raise TypeError("output_raster should be a string (service name) or Item")

        output_raster =  { 'itemId' : output_service.itemid }

        params = {}

        params["Input_Raster"] = input_raster
        params["Output_Raster_Dataset"] = output_raster
        params["Spectral_Detail"] = spectral_detail
        params["Spatial_Detail"] = spatial_detail
        params["Minimum_Segment_Size_In_Pixels"] = minimum_segment_size_in_pixels
        params["Band_Indexes"] = band_indexes
        params["Remove_Tiiling_Artifacts"] = remove_tiiling_artifacts
        params["Number_of_Instances"] = number_of_instances

        task_url, job_info = super()._analysis_job(task, params)

        job_info = super()._analysis_job_status(task_url, job_info)
        job_values = super()._analysis_job_results(task_url, job_info)
        #print(job_values)
        item_properties = {
            "properties":{
                "jobUrl": task_url + '/jobs/' + job_info['jobId'],
                "jobType": "GPServer",
                "jobId": job_info['jobId'],
                "jobStatus": "completed"
                }
            }
        output_service.update(item_properties)
        return output_service


    def train_classifier(self,
                       input_raster,
                       input_training_sample_json,
                       segmented_raster,
                       classifier_parameters,
                       segment_attributes="COLOR;MEAN"):
        """


        Parameters
        ----------
        input_raster : Required string

        input_training_sample_json : Required string

        segmented_raster : Required string

        classifier_parameters : Required string

        segment_attributes : Required string


        Returns
        -------
        output_classifier_definition : layer
        """

        task ="Train Classifier"

        params = {}

        params["Input_Raster"] = input_raster
        params["Input_Training_Sample_JSON"] = input_training_sample_json
        params["Segmented_Raster"] = segmented_raster
        params["Classifier_Parameters"] = classifier_parameters
        params["Segment_Attributes"] = segment_attributes

        task_url, job_info = super()._analysis_job(task, params)

        job_info = super()._analysis_job_status(task_url, job_info)
        job_values = super()._analysis_job_results(task_url, job_info)

        return job_values['Output_Classifier_Definition']

    def _create_output_feature_service(self, output_name, task):
        ok = self._gis.content.is_service_name_available(output_name, "Feature Service")
        if not ok:
            raise RuntimeError("A Feature Service by this name already exists: " + output_name)

        createParameters = {
                "currentVersion": 10.2,
                "serviceDescription": "",
                "hasVersionedData": False,
                "supportsDisconnectedEditing": False,
                "hasStaticData": True,
                "maxRecordCount": 2000,
                "supportedQueryFormats": "JSON",
                "capabilities": "Query",
                "description": "",
                "copyrightText": "",
                "allowGeometryUpdates": False,
                "syncEnabled": False,
                "editorTrackingInfo": {
                    "enableEditorTracking": False,
                    "enableOwnershipAccessControl": False,
                    "allowOthersToUpdate": True,
                    "allowOthersToDelete": True
                },
                "xssPreventionInfo": {
                    "xssPreventionEnabled": True,
                    "xssPreventionRule": "InputOnly",
                    "xssInputRule": "rejectInvalid"
                },
                "tables": [],
                "name": output_name,
                "options": {
                    "dataSourceType": "spatiotemporal"
                }
            }

        output_service = self._gis.content.create_service(output_name, create_params=createParameters, service_type="featureService")
        description = "Feature Service generated from running the " + task + " tool."
        item_properties = {
                "description" : description,
                "tags" : "Analysis Result, " + task,
                "snippet": "Analysis Feature Service generated from " + task
                }
        output_service.update(item_properties)
        return output_service


    def convert_raster_to_feature(self,
                       input_raster,
                       output_name,
                       field="Value",
                       output_type="Point",
                       simplify_lines_or_polygons=True,
                       context=None):
        """
        This service tool converts imagery data to feature class vector data.

        Parameters
        ----------
        input_raster : Required string

        output_name : Required string

        field : Optional string

        output_type : Optional string
            One of the following: ['Point', 'Line', 'Polygon']
        simplify_lines_or_polygons : Optional bool

        context : Optional string


        Returns
        -------
        output_feature : layer (Feature Service item)
        """

        task ="Convert Raster To Feature"

        params = {}

        params["inputRaster"] = input_raster

        output_service = self._create_output_feature_service(output_name, task)

        params["outputName"] = json.dumps({"serviceProperties": {"name" : output_name, "serviceUrl" : output_service.url}, "itemProperties": {"itemId" : output_service.itemid}})
        if field is not None:
            params["field"] = field
        if output_type is not None:
            params["outputType"] = output_type
        if simplify_lines_or_polygons is not None:
            params["simplifyLinesOrPolygons"] = simplify_lines_or_polygons
        if context is not None:
            params["context"] = context

        task_url, job_info = super()._analysis_job(task, params)

        job_info = super()._analysis_job_status(task_url, job_info)
        job_values = super()._analysis_job_results(task_url, job_info)
        #print(job_values)
        item_properties = {
                "properties":{
                    "jobUrl": task_url + '/jobs/' + job_info['jobId'],
                    "jobType": "GPServer",
                    "jobId": job_info['jobId'],
                    "jobStatus": "completed"
                    }
                }
        output_service.update(item_properties)
        return output_service


class _GeoanalyticsTools(_AsyncService):
    """
    The Geoanalytics Tools from the GIS.
    GeoAnalyticsTools are provided for distributed analysis of large datasets.
    """

    def __init__(self, url, gis):
        """
        Constructs a client to the service given it's url from ArcGIS Online or Portal.
        """
        # super(RasterAnalysisTools, self).__init__(url, gis)
        super(_GeoanalyticsTools, self).__init__(url, gis)

    def _create_output_service(self, output_name, task):
        ok = self._gis.content.is_service_name_available(output_name, "Feature Service")
        if not ok:
            raise RuntimeError("A Feature Service by this name already exists: " + output_name)

        createParameters = {
                "currentVersion": 10.2,
                "serviceDescription": "",
                "hasVersionedData": False,
                "supportsDisconnectedEditing": False,
                "hasStaticData": True,
                "maxRecordCount": 2000,
                "supportedQueryFormats": "JSON",
                "capabilities": "Query",
                "description": "",
                "copyrightText": "",
                "allowGeometryUpdates": False,
                "syncEnabled": False,
                "editorTrackingInfo": {
                    "enableEditorTracking": False,
                    "enableOwnershipAccessControl": False,
                    "allowOthersToUpdate": True,
                    "allowOthersToDelete": True
                },
                "xssPreventionInfo": {
                    "xssPreventionEnabled": True,
                    "xssPreventionRule": "InputOnly",
                    "xssInputRule": "rejectInvalid"
                },
                "tables": [],
                "name": output_name,
                "options": {
                    "dataSourceType": "spatiotemporal"
                }
            }

        output_service = self._gis.content.create_service(output_name, create_params=createParameters, service_type="featureService")
        description = "Feature Service generated from running the " + task + " tool."
        item_properties = {
                "description" : description,
                "tags" : "Analysis Result, " + task,
                "snippet": "Analysis Feature Service generated from " + task
                }
        output_service.update(item_properties)
        return output_service




    def aggregate_points(self,
                       point_layer,
                       output_name,
                       distance_interval=None,
                       distance_interval_unit=None,
                       bin_type="SQUARE",
                       polygon_layer=None,
                       time_interval=None,
                       time_interval_unit=None,
                       time_repeat=None,
                       time_repeat_unit=None,
                       time_reference=None,
                       summary_fields=None,
                       out_sr=None,
                         process_sr=None,
                       out_extent=None,
                       datastore="GDB"):
        """


        Parameters
        ----------
        point_layer : Required FeatureSet

        distance_interval : Optional float

        distance_interval_unit : Optional string
            One of the following: ['Feet', 'Yards', 'Miles', 'Meters', 'Kilometers', 'Nautical Miles']
        bin_type : Optional string
            One of the following: ['SQUARE', 'HEXAGON']
        polygon_layer : Optional FeatureSet

        time_interval : Optional int

        time_interval_unit : Optional string
            One of the following: ['Years', 'Months', 'Weeks', 'Days', 'Hours', 'Minutes', 'Seconds', 'Milliseconds']
        time_repeat : Optional int

        time_repeat_unit : Optional string
            One of the following: ['Years', 'Months', 'Weeks', 'Days', 'Hours', 'Minutes', 'Seconds', 'Milliseconds']
        time_reference : Optional datetime.date

        summary_fields : Optional string

        output_name : Required string

        out_sr : Optional int

        process_sr : Optional int

        out_extent : Optional string

        datastore : Optional string
            One of the following: ['BDS', 'GDB']


        Returns
        -------
        output : layer (Feature Service item)
        """

        task ="AggregatePoints"

        params = {}
        context = {}

        params["pointLayer"] = super()._feature_input(point_layer)
        if distance_interval is not None:
            params["distanceInterval"] = distance_interval
        if distance_interval_unit is not None:
            params["distanceIntervalUnit"] = distance_interval_unit
        if bin_type is not None:
            params["binType"] = bin_type
        if polygon_layer is not None:
            params["polygonLayer"] = super()._feature_input(polygon_layer)
        if time_interval is not None:
            params["timeInterval"] = time_interval
        if time_interval_unit is not None:
            params["timeIntervalUnit"] = time_interval_unit
        if time_repeat is not None:
            params["timeRepeat"] = time_repeat
        if time_repeat_unit is not None:
            params["timeRepeatUnit"] = time_repeat_unit
        if time_reference is not None:
            params["timeReference"] = time_reference
        if summary_fields is not None:
            params["summaryFields"] = summary_fields

        output_service = self._create_output_service(output_name, task)

        params["outputName"] = json.dumps({"serviceProperties": {"name" : output_name, "serviceUrl" : output_service.url}, "itemProperties": {"itemId" : output_service.itemid}})
        if out_sr is not None:
            context['outSR'] = {'wkid': int(out_sr)}
        if out_extent is not None:
            context['extent'] = out_extent
        if process_sr is not None:
            context['processSR'] = {'wkid': int(process_sr)}
        # if datastore is not None:
        #     params["gax:env:datastore"] = datastore
        if context is not None:
            params["context"] = json.dumps(context)

        task_url, job_info = super()._analysis_job(task, params)

        job_info = super()._analysis_job_status(task_url, job_info)
        job_values = super()._analysis_job_results(task_url, job_info)
        #print(job_values)
        if output_name is not None:
            #url = job_values['output']['url']
            #return FeatureLayer(url, self._gis) #item
            item_properties = {
                "properties":{
                    "jobUrl": task_url + '/jobs/' + job_info['jobId'],
                    "jobType": "GPServer",
                    "jobId": job_info['jobId'],
                    "jobStatus": "completed"
                    }
                }
            output_service.update(item_properties)
            return output_service
        else:
            # Feature Collection
            return arcgis.features.FeatureCollection(job_values['output'])


    def describe_dataset(self,
                       in_dataset,
                       out_sr=None,
                       out_extent=None,
                       datastore="GDB",
                       context=None):
        """


        Parameters
        ----------
        in_dataset : Required FeatureSet

        out_sr : Optional string

        out_extent : Optional string

        datastore : Optional string
            One of the following: ['BDS', 'GDB']
        context : Optional string


        Returns
        -------
        output_json : layer (Feature Service item)
        """

        task ="DescribeDataset"

        params = {}

        params["in_dataset"] = in_dataset
        if out_sr is not None:
            params["gax:env:out_sr"] = out_sr
        if out_extent is not None:
            params["gax:env:outExtent"] = out_extent
        if datastore is not None:
            params["gax:env:datastore"] = datastore
        if context is not None:
            params["context"] = context

        task_url, job_info = super()._analysis_job(task, params)

        job_info = super()._analysis_job_status(task_url, job_info)
        job_values = super()._analysis_job_results(task_url, job_info)
        #print(job_values)
        if output_name is not None:
            #url = job_values['output']['url']
            #return FeatureLayer(url, self._gis) #item
            item_properties = {
                "properties":{
                    "jobUrl": task_url + '/jobs/' + job_info['jobId'],
                    "jobType": "GPServer",
                    "jobId": job_info['jobId'],
                    "jobStatus": "completed"
                    }
                }
            output_service.update(item_properties)
            return output_service
        else:
            # Feature Collection
            return arcgis.features.FeatureCollection(job_values['output_json'])


    def join_features(self,
                       target_layer,
                       join_layer,
                       output_name,
                       join_operation="Join one to one",
                       join_fields=None,
                       summary_fields=None,
                       spatial_relationship=None,
                       spatial_near_distance=None,
                       spatial_near_distance_unit=None,
                       temporal_relationship=None,
                       temporal_near_distance=None,
                       temporal_near_distance_unit=None,
                       attribute_relationship=None,
                       join_condition=None,
                       out_sr=None,
                      process_sr = None,
                       out_extent=None,
                       datastore="GDB"):
        """


        Parameters
        ----------
        target_layer : Required FeatureSet

        join_layer : Required FeatureSet

        join_operation : Required string
            One of the following: ['Join one to one', 'Join one to many']
        join_fields : Optional string

        summary_fields : Optional string

        spatial_relationship : Optional string
            One of the following: ['Equals', 'Intersects', 'Contains', 'Within', 'Crosses', 'Touches', 'Overlaps', 'Near']
        spatial_near_distance : Optional float

        spatial_near_distance_unit : Optional string
            One of the following: ['Feet', 'Yards', 'Miles', 'Meters', 'Kilometers', 'Nautical Miles']
        temporal_relationship : Optional string
            One of the following: ['Equals', 'Intersects', 'During', 'Contains', 'Finishes', 'FinishedBy', 'Meets', 'MetBy', 'Overlaps', 'OverlappedBy', 'Starts', 'StartedBy', 'Near']
        temporal_near_distance : Optional int

        temporal_near_distance_unit : Optional string
            One of the following: ['Years', 'Months', 'Weeks', 'Days', 'Hours', 'Minutes', 'Seconds', 'Milliseconds']
        attribute_relationship : Optional string

        join_condition : Optional string

        output_name : Required string

        out_sr : Optional int

        process_sr : Optional int

        out_extent : Optional string

        datastore : Optional string
            One of the following: ['BDS', 'GDB']


        Returns
        -------
        output : layer (Feature Service item)
        """

        task ="JoinFeatures"

        params = {}
        context = {}

        params["targetLayer"] = super()._feature_input(target_layer)
        params["joinLayer"] = super()._feature_input(join_layer)
        params["joinOperation"] = join_operation
        if join_fields is not None:
            params["joinFields"] = join_fields
        if summary_fields is not None:
            params["summaryFields"] = summary_fields
        if spatial_relationship is not None:
            params["spatialRelationship"] = spatial_relationship
        if spatial_near_distance is not None:
            params["spatialNearDistance"] = spatial_near_distance
        if spatial_near_distance_unit is not None:
            params["spatialNearDistanceUnit"] = spatial_near_distance_unit
        if temporal_relationship is not None:
            params["temporalRelationship"] = temporal_relationship
        if temporal_near_distance is not None:
            params["temporalNearDistance"] = temporal_near_distance
        if temporal_near_distance_unit is not None:
            params["temporalNearDistanceUnit"] = temporal_near_distance_unit
        if attribute_relationship is not None:
            params["attributeRelationship"] = attribute_relationship
        if join_condition is not None:
            params["joinCondition"] = join_condition

        output_service = self._create_output_service(output_name, task)

        params["outputName"] = json.dumps({"serviceProperties": {"name" : output_name, "serviceUrl" : output_service.url}, "itemProperties": {"itemId" : output_service.itemid}})
        if out_sr is not None:
            context['outSR'] = {'wkid': int(out_sr)}
        if process_sr is not None:
            context['processSR'] = {'wkid': int(process_sr)}
        if out_extent is not None:
            context["extent"] = out_extent
            # if datastore is not None:
            #     params["gax:env:datastore"] = datastore
        if context is not None:
            params["context"] = json.dumps(context)

        task_url, job_info = super()._analysis_job(task, params)

        job_info = super()._analysis_job_status(task_url, job_info)
        job_values = super()._analysis_job_results(task_url, job_info)
        #print(job_values)
        if output_name is not None:
            #url = job_values['output']['url']
            #return FeatureLayer(url, self._gis) #item
            item_properties = {
                "properties":{
                    "jobUrl": task_url + '/jobs/' + job_info['jobId'],
                    "jobType": "GPServer",
                    "jobId": job_info['jobId'],
                    "jobStatus": "completed"
                    }
                }
            output_service.update(item_properties)
            return output_service
        else:
            # Feature Collection
            return arcgis.features.FeatureCollection(job_values['output'])


    def create_buffers(self,
                       input_layer,
                       output_name,
                       distance=None,
                       distance_unit=None,
                       field=None,
                       method="PLANAR",
                       dissolve_option="NONE",
                       dissolve_fields=None,
                       summary_fields=None,
                       multipart=False,
                       out_sr=None,
                       process_sr = None,
                       out_extent=None,
                       datastore="GDB"):
        """


        Parameters
        ----------
        input_layer : Required FeatureSet

        distance : Optional float

        distance_unit : Optional string
            One of the following: ['Feet', 'Yards', 'Miles', 'Meters', 'Kilometers', 'Nautical Miles']
        field : Optional string

        method : Required string
            One of the following: ['GEODESIC', 'PLANAR']
        dissolve_option : Optional string
            One of the following: ['ALL', 'LIST', 'NONE']
        dissolve_fields : Optional string

        summary_fields : Optional string

        multipart : Optional bool

        output_name : Required string

        out_sr : Optional int

        process_sr : Optional int

        out_extent : Optional string

        datastore : Optional string
            One of the following: ['BDS', 'GDB']


        Returns
        -------
        output : layer (Feature Service item)
        """

        task ="CreateBuffers"

        params = {}
        context = {}

        params["inputLayer"] = super()._feature_input(input_layer)
        if distance is not None:
            params["distance"] = distance
        if distance_unit is not None:
            params["distanceUnit"] = distance_unit
        if field is not None:
            params["field"] = field
        params["method"] = method
        if dissolve_option is not None:
            params["dissolveOption"] = dissolve_option
        if dissolve_fields is not None:
            params["dissolveFields"] = dissolve_fields
        if summary_fields is not None:
            params["summaryFields"] = summary_fields
        if multipart is not None:
            params["multipart"] = multipart

        output_service = self._create_output_service(output_name, task)

        params["outputName"] = json.dumps({"serviceProperties": {"name" : output_name, "serviceUrl" : output_service.url}, "itemProperties": {"itemId" : output_service.itemid}})
        if out_sr is not None:
            context["outSR"] = {'wkid': int(out_sr)}
        if process_sr is not None:
            context["processSR"] = {'wkid': int(process_sr)}
        if out_extent is not None:
            context["extent"] = out_extent
        # if datastore is not None:
        #     params["gax:env:datastore"] = datastore
        if context is not None:
            params["context"] = json.dumps(context)

        task_url, job_info = super()._analysis_job(task, params)

        job_info = super()._analysis_job_status(task_url, job_info)
        job_values = super()._analysis_job_results(task_url, job_info)
        #print(job_values)
        if output_name is not None:
            #url = job_values['output']['url']
            #return FeatureLayer(url, self._gis) #item
            item_properties = {
                "properties":{
                    "jobUrl": task_url + '/jobs/' + job_info['jobId'],
                    "jobType": "GPServer",
                    "jobId": job_info['jobId'],
                    "jobStatus": "completed"
                    }
                }
            output_service.update(item_properties)
            return output_service
        else:
            # Feature Collection
            return arcgis.features.FeatureCollection(job_values['output'])


    def calculate_density(self,
                       input_layer,
                       bin_size,
                       bin_size_unit,
                       radius,
                       radius_unit,
                       output_name,
                       fields=None,
                       weight="UNIFORM",
                       bin_type="SQUARE",
                       time_interval=None,
                       time_interval_unit=None,
                       time_repeat=None,
                       time_repeat_unit=None,
                       time_reference=None,
                       area_units=None,
                       out_sr=None,
                          process_sr = None,
                       out_extent=None,
                       datastore="GDB"):
        """


        Parameters
        ----------
        input_layer : Required FeatureSet

        fields : Optional string

        weight : Required string
            One of the following: ['UNIFORM', 'KERNEL']
        bin_size : Required float

        bin_size_unit : Required string
            One of the following: ['Feet', 'Yards', 'Miles', 'Meters', 'Kilometers', 'Nautical Miles']
        bin_type : Required string
            One of the following: ['SQUARE', 'HEXAGON']
        time_interval : Optional int

        time_interval_unit : Optional string
            One of the following: ['Years', 'Months', 'Weeks', 'Days', 'Hours', 'Minutes', 'Seconds', 'Milliseconds']
        time_repeat : Optional int

        time_repeat_unit : Optional string
            One of the following: ['Years', 'Months', 'Weeks', 'Days', 'Hours', 'Minutes', 'Seconds', 'Milliseconds']
        time_reference : Optional datetime.date

        radius : Required float

        radius_unit : Required string
            One of the following: ['Feet', 'Yards', 'Miles', 'Meters', 'Kilometers', 'Nautical Miles']
        area_units : Optional string
            One of the following: ['ACRES', 'SQUARE_KILOMETERS', 'SQUARE_INCHES', 'SQUARE_FEET', 'SQUARE_YARDS', 'SQUARE_MAP_UNITS', 'SQUARE_METERS', 'SQUARE_MILES', 'HECTARES']
        output_name : Required string

        out_sr : Optional int

        process_sr : Optional int

        out_extent : Optional int

        datastore : Optional string
            One of the following: ['BDS', 'GDB']


        Returns
        -------
        output : layer (Feature Service item)
        """

        task ="CalculateDensity"

        params = {}
        context = {}

        params["inputLayer"] = super()._feature_input(input_layer)
        if fields is not None:
            params["fields"] = fields
        params["weight"] = weight
        params["binSize"] = bin_size
        params["binSizeUnit"] = bin_size_unit
        params["binType"] = bin_type
        if time_interval is not None:
            params["timeInterval"] = time_interval
        if time_interval_unit is not None:
            params["timeIntervalUnit"] = time_interval_unit
        if time_repeat is not None:
            params["timeRepeat"] = time_repeat
        if time_repeat_unit is not None:
            params["timeRepeatUnit"] = time_repeat_unit
        if time_reference is not None:
            params["timeReference"] = time_reference
        params["radius"] = radius
        params["radiusUnit"] = radius_unit
        if area_units is not None:
            params["areaUnits"] = area_units

        output_service = self._create_output_service(output_name, task)

        params["outputName"] = json.dumps({"serviceProperties": {"name" : output_name, "serviceUrl" : output_service.url}, "itemProperties": {"itemId" : output_service.itemid}})
        if out_sr is not None:
            context['outSR'] = {'wkid': int(out_sr)}
        if process_sr is not None:
            context['processSR'] = {'wkid': int(process_sr)}
        if out_extent is not None:
            context["extent"] = out_extent
        # if datastore is not None:
        #     params["gax:env:datastore"] = datastore
        if context is not None:
            params["context"] = json.dumps(context)

        task_url, job_info = super()._analysis_job(task, params)

        job_info = super()._analysis_job_status(task_url, job_info)
        job_values = super()._analysis_job_results(task_url, job_info)
        #print(job_values)
        if output_name is not None:
            #url = job_values['output']['url']
            #return FeatureLayer(url, self._gis) #item
            item_properties = {
                "properties":{
                    "jobUrl": task_url + '/jobs/' + job_info['jobId'],
                    "jobType": "GPServer",
                    "jobId": job_info['jobId'],
                    "jobStatus": "completed"
                    }
                }
            output_service.update(item_properties)
            return output_service
        else:
            # Feature Collection
            return arcgis.features.FeatureCollection(job_values['output'])


    def reconstruct_tracks(self,
                           input_layer,
                           track_fields,
                           output_name,
                           method="PLANAR",
                           buffer_field=None,
                           summary_fields=None,
                           time_split=None,
                           time_split_unit=None,
                           out_sr=None,
                           process_sr=None,
                           out_extent=None,
                           datastore="GDB"):
        """


        Parameters
        ----------
        input_layer : Required FeatureSet

        track_fields : Required string

        method : Required string
            One of the following: ['GEODESIC', 'PLANAR']
        buffer_field : Optional string

        summary_fields : Optional string

        time_split : Optional int

        time_split_unit : Optional string
            One of the following: ['Years', 'Months', 'Weeks', 'Days', 'Hours', 'Minutes', 'Seconds', 'Milliseconds']
        output_name : Required string

        out_sr : Optional int

        process_sr : Optional int

        out_extent : Optional string

        datastore : Optional string
            One of the following: ['BDS', 'GDB']


        Returns
        -------
        output : layer (Feature Service item)
        """

        task ="ReconstructTracks"

        params = {}
        context = {}

        params["inputLayer"] = super()._feature_input(input_layer)
        params["trackFields"] = track_fields
        params["method"] = method
        if buffer_field is not None:
            params["bufferField"] = buffer_field
        if summary_fields is not None:
            params["summaryFields"] = summary_fields
        if time_split is not None:
            params["timeSplit"] = time_split
        if time_split_unit is not None:
            params["timeSplitUnit"] = time_split_unit

        output_service = self._create_output_service(output_name, task)

        params["outputName"] = json.dumps({"serviceProperties": {"name" : output_name, "serviceUrl" : output_service.url}, "itemProperties": {"itemId" : output_service.itemid}})
        if out_sr is not None:
            context['outSR'] = {'wkid': int(out_sr)}
        if process_sr is not None:
            context['processSR'] = {'wkid': int(process_sr)}
        if out_extent is not None:
            context["extent"] = out_extent
            # if datastore is not None:
            #     params["gax:env:datastore"] = datastore
        if context is not None:
            params["context"] = json.dumps(context)

        task_url, job_info = super()._analysis_job(task, params)

        job_info = super()._analysis_job_status(task_url, job_info)
        job_values = super()._analysis_job_results(task_url, job_info)
        #print(job_values)
        if output_name is not None:
            #url = job_values['output']['url']
            #return FeatureLayer(url, self._gis) #item
            item_properties = {
                "properties":{
                    "jobUrl": task_url + '/jobs/' + job_info['jobId'],
                    "jobType": "GPServer",
                    "jobId": job_info['jobId'],
                    "jobStatus": "completed"
                    }
                }
            output_service.update(item_properties)
            return output_service
        else:
            # Feature Collection
            return arcgis.features.FeatureCollection(job_values['output'])


    def create_space_time_cube(self,
                               point_layer,
                               distance_interval,
                               distance_interval_unit,
                               time_interval,
                               time_interval_unit,
                               output_name,
                               time_interval_alignment=None,
                               reference_time=None,
                               summary_fields=None,
                               out_sr=None,
                               process_sr = None,
                               out_extent=None,
                               datastore="GDB"):
        """


        Parameters
        ----------
        point_layer : Required FeatureSet

        distance_interval : Required float

        distance_interval_unit : Required string
            One of the following: ['Feet', 'Yards', 'Miles', 'Meters', 'Kilometers', 'Nautical Miles']
        time_interval : Required int

        time_interval_unit : Required string
            One of the following: ['Years', 'Months', 'Weeks', 'Days', 'Hours', 'Minutes', 'Seconds', 'Milliseconds']
        time_interval_alignment : Optional string
            One of the following: ['END_TIME', 'START_TIME', 'REFERENCE_TIME']
        reference_time : Optional datetime.date

        summary_fields : Optional string

        output_name : Required string

        out_sr : Optional int

        process_sr : Optional int

        out_extent : Optional string

        datastore : Optional string
            One of the following: ['BDS', 'GDB']


        Returns
        -------
        output_cube : layer (Feature Service item)
        """

        task ="CreateSpaceTimeCube"

        params = {}
        context = {}

        params["pointLayer"] = super()._feature_input(point_layer)
        params["distanceInterval"] = distance_interval
        params["distanceIntervalUnit"] = distance_interval_unit
        params["timeInterval"] = time_interval
        params["timeIntervalUnit"] = time_interval_unit
        if time_interval_alignment is not None:
            params["timeIntervalAlignment"] = time_interval_alignment
        if reference_time is not None:
            params["referenceTime"] = reference_time
        if summary_fields is not None:
            params["summaryFields"] = summary_fields

        output_service = self._create_output_service(output_name, task)

        params["outputName"] = json.dumps({"serviceProperties": {"name" : output_name, "serviceUrl" : output_service.url}, "itemProperties": {"itemId" : output_service.itemid}})
        if out_sr is not None:
            context['outSR'] = {'wkid': int(out_sr)}
        if process_sr is not None:
            context['processSR'] = {'wkid': int(process_sr)}
        if out_extent is not None:
            context["extent"] = out_extent
        # if datastore is not None:
        #     params["gax:env:datastore"] = datastore
        if context is not None:
            params["context"] = json.dumps(context)

        task_url, job_info = super()._analysis_job(task, params)

        job_info = super()._analysis_job_status(task_url, job_info)
        job_values = super()._analysis_job_results(task_url, job_info)
        #print(job_values)
        if output_name is not None:
            #url = job_values['output']['url']
            #return FeatureLayer(url, self._gis) #item
            item_properties = {
                "properties":{
                    "jobUrl": task_url + '/jobs/' + job_info['jobId'],
                    "jobType": "GPServer",
                    "jobId": job_info['jobId'],
                    "jobStatus": "completed"
                    }
                }
            output_service.update(item_properties)
            return output_service
        else:
            # Feature Collection
            return arcgis.features.FeatureCollection(job_values['outputCube'])


    def create_panel_data(self,
                       in_target_features,
                       in_join_features,
                       time_interval,
                       time_interval_unit,
                       time_repeat,
                       time_repeat_unit,
                       time_reference,
                       out_features_name,
                       in_summary_stats=None,
                       in_spatial_relationship=None,
                       in_spatial_distance=None,
                       in_spatial_distance_unit=None,
                       in_attribute_relationship=None,
                       out_sr=None,
                       out_extent=None,
                       datastore="GDB",
                       context=None):
        """


        Parameters
        ----------
        in_target_features : Required FeatureSet

        in_join_features : Required FeatureSet

        in_summary_stats : Optional string

        in_spatial_relationship : Optional string
            One of the following: ['Intersect', 'Contains', 'Within', 'Crosses', 'Touches', 'Overlaps', 'Near']
        in_spatial_distance : Optional float

        in_spatial_distance_unit : Optional string
            One of the following: ['Feet', 'Yards', 'Miles', 'Meters', 'Kilometers', 'Nautical Miles']
        in_attribute_relationship : Optional string

        time_interval : Required int

        time_interval_unit : Required string
            One of the following: ['Years', 'Months', 'Weeks', 'Days', 'Hours', 'Minutes', 'Seconds', 'Milliseconds']
        time_repeat : Required int

        time_repeat_unit : Required string
            One of the following: ['Years', 'Months', 'Weeks', 'Days', 'Hours', 'Minutes', 'Seconds', 'Milliseconds']
        time_reference : Required datetime.date

        out_features_name : Required string

        out_sr : Optional string

        out_extent : Optional string

        datastore : Optional string
            One of the following: ['BDS', 'GDB']
        context : Optional string


        Returns
        -------
        out_features : layer (Feature Service item)
        """

        task ="CreatePanelData"

        params = {}

        params["in_target_features"] = in_target_features
        params["in_join_features"] = in_join_features
        if in_summary_stats is not None:
            params["in_summary_stats"] = in_summary_stats
        if in_spatial_relationship is not None:
            params["in_spatial_relationship"] = in_spatial_relationship
        if in_spatial_distance is not None:
            params["in_spatial_distance"] = in_spatial_distance
        if in_spatial_distance_unit is not None:
            params["in_spatial_distanceUnit"] = in_spatial_distance_unit
        if in_attribute_relationship is not None:
            params["in_attribute_relationship"] = in_attribute_relationship
        params["timeInterval"] = time_interval
        params["timeIntervalUnit"] = time_interval_unit
        params["timeRepeat"] = time_repeat
        params["timeRepeatUnit"] = time_repeat_unit
        params["timeReference"] = time_reference
        params["out_featuresName"] = out_features_name
        if out_sr is not None:
            params["gax:env:out_sr"] = out_sr
        if out_extent is not None:
            params["gax:env:outExtent"] = out_extent
        if datastore is not None:
            params["gax:env:datastore"] = datastore
        if context is not None:
            params["context"] = context

        task_url, job_info = super()._analysis_job(task, params)

        job_info = super()._analysis_job_status(task_url, job_info)
        job_values = super()._analysis_job_results(task_url, job_info)
        #print(job_values)
        if output_name is not None:
            #url = job_values['output']['url']
            #return FeatureLayer(url, self._gis) #item
            item_properties = {
                "properties":{
                    "jobUrl": task_url + '/jobs/' + job_info['jobId'],
                    "jobType": "GPServer",
                    "jobId": job_info['jobId'],
                    "jobStatus": "completed"
                    }
                }
            output_service.update(item_properties)
            return output_service
        else:
            # Feature Collection
            return arcgis.features.FeatureCollection(job_values['out_features'])


    def generate_manifest(self,
                       data_store_item_id,
                       update_data_item=False,
                       out_sr=None,
                       out_extent=None,
                       datastore="GDB",
                       context=None):
        """


        Parameters
        ----------
        data_store_item_id : Required string

        update_data_item : Optional bool

        out_sr : Optional string

        out_extent : Optional string

        datastore : Optional string
            One of the following: ['BDS', 'GDB']
        context : Optional string


        Returns
        -------
        manifest : layer (Feature Service item)
        """

        task ="GenerateManifest"

        params = {}

        params["dataStoreItemId"] = data_store_item_id
        if update_data_item is not None:
            params["updateDataItem"] = update_data_item
        if out_sr is not None:
            params["gax:env:out_sr"] = out_sr
        if out_extent is not None:
            params["gax:env:outExtent"] = out_extent
        if datastore is not None:
            params["gax:env:datastore"] = datastore
        if context is not None:
            params["context"] = context

        task_url, job_info = super()._analysis_job(task, params)

        job_info = super()._analysis_job_status(task_url, job_info)
        job_values = super()._analysis_job_results(task_url, job_info)
        #print(job_values)
        if output_name is not None:
            #url = job_values['output']['url']
            #return FeatureLayer(url, self._gis) #item
            item_properties = {
                "properties":{
                    "jobUrl": task_url + '/jobs/' + job_info['jobId'],
                    "jobType": "GPServer",
                    "jobId": job_info['jobId'],
                    "jobStatus": "completed"
                    }
                }
            output_service.update(item_properties)
            return output_service
        else:
            # Feature Collection
            return arcgis.features.FeatureCollection(job_values['manifest'])


    def create_sample(self,
                       input_layer,
                       output_layer_name,
                       out_sr=None,
                       out_extent=None,
                       datastore="GDB",
                       context=None):
        """


        Parameters
        ----------
        input_layer : Required FeatureSet

        output_layer_name : Required string

        out_sr : Optional string

        out_extent : Optional string

        datastore : Optional string
            One of the following: ['BDS', 'GDB']
        context : Optional string


        Returns
        -------
        output_layer : layer (Feature Service item)
        """

        task ="CreateSample"

        params = {}

        params["inputLayer"] = super()._feature_input(input_layer)
        params["outputLayerName"] = output_layer_name
        if out_sr is not None:
            params["gax:env:out_sr"] = out_sr
        if out_extent is not None:
            params["gax:env:outExtent"] = out_extent
        if datastore is not None:
            params["gax:env:datastore"] = datastore
        if context is not None:
            params["context"] = context

        task_url, job_info = super()._analysis_job(task, params)

        job_info = super()._analysis_job_status(task_url, job_info)
        job_values = super()._analysis_job_results(task_url, job_info)
        #print(job_values)
        if output_name is not None:
            #url = job_values['output']['url']
            #return FeatureLayer(url, self._gis) #item
            item_properties = {
                "properties":{
                    "jobUrl": task_url + '/jobs/' + job_info['jobId'],
                    "jobType": "GPServer",
                    "jobId": job_info['jobId'],
                    "jobStatus": "completed"
                    }
                }
            output_service.update(item_properties)
            return output_service
        else:
            # Feature Collection
            return arcgis.features.FeatureCollection(job_values['outputLayer'])


    def copy_to_data_store(self,
                       input_layer,
                       output_name,
                       out_sr=None,
                       out_extent=None,
                       datastore="GDB",
                       context=None):
        """


        Parameters
        ----------
        input_layer : Required FeatureSet

        output_name : Required string

        out_sr : Optional string

        out_extent : Optional string

        datastore : Optional string
            One of the following: ['BDS', 'GDB']
        context : Optional string


        Returns
        -------
        output : layer (Feature Service item)
        """

        task ="CopyToDataStore"

        params = {}

        params["inputLayer"] = super()._feature_input(input_layer)

        output_service = self._create_output_service(output_name, task)

        params["outputName"] = json.dumps({"serviceProperties": {"name" : output_name, "serviceUrl" : output_service.url}, "itemProperties": {"itemId" : output_service.itemid}})
        if out_sr is not None:
            params["gax:env:out_sr"] = out_sr
        if out_extent is not None:
            params["gax:env:outExtent"] = out_extent
        if datastore is not None:
            params["gax:env:datastore"] = datastore
        if context is not None:
            params["context"] = context

        task_url, job_info = super()._analysis_job(task, params)

        job_info = super()._analysis_job_status(task_url, job_info)
        job_values = super()._analysis_job_results(task_url, job_info)
        #print(job_values)
        if output_name is not None:
            #url = job_values['output']['url']
            #return FeatureLayer(url, self._gis) #item
            item_properties = {
                "properties":{
                    "jobUrl": task_url + '/jobs/' + job_info['jobId'],
                    "jobType": "GPServer",
                    "jobId": job_info['jobId'],
                    "jobStatus": "completed"
                    }
                }
            output_service.update(item_properties)
            return output_service
        else:
            # Feature Collection
            return arcgis.features.FeatureCollection(job_values['output'])


    def summarize_attributes(self,
                       input_layer,
                       fields,
                       output_name,
                       summary_fields=None,
                       out_sr=None,
                             process_sr = None,
                       out_extent=None,
                       datastore="GDB"):
        """


        Parameters
        ----------
        input_layer : Required FeatureSet

        fields : Required string

        summary_fields : Optional string

        output_name : Required string

        out_sr : Optional int

        process_sr : Optional int

        out_extent : Optional string

        datastore : Optional string
            One of the following: ['BDS', 'GDB']


        Returns
        -------
        output : layer (Feature Service item)
        """

        task ="SummarizeAttributes"

        params = {}
        context = {}

        params["inputLayer"] = super()._feature_input(input_layer)
        params["fields"] = fields
        if summary_fields is not None:
            params["summaryFields"] = summary_fields

        output_service = self._create_output_service(output_name, task)

        params["outputName"] = json.dumps({"serviceProperties": {"name" : output_name, "serviceUrl" : output_service.url}, "itemProperties": {"itemId" : output_service.itemid}})
        if out_sr is not None:
            context['outSR'] = {'wkid': int(out_sr)}
        if process_sr is not None:
            context['processSR'] = {'wkid': int(process_sr)}
        if out_extent is not None:
            context["extent"] = out_extent
        # if datastore is not None:
        #     params["gax:env:datastore"] = datastore
        if context is not None:
            params["context"] = json.dumps(context)

        task_url, job_info = super()._analysis_job(task, params)

        job_info = super()._analysis_job_status(task_url, job_info)
        job_values = super()._analysis_job_results(task_url, job_info)
        #print(job_values)
        if output_name is not None:
            #url = job_values['output']['url']
            #return FeatureLayer(url, self._gis) #item
            item_properties = {
                "properties":{
                    "jobUrl": task_url + '/jobs/' + job_info['jobId'],
                    "jobType": "GPServer",
                    "jobId": job_info['jobId'],
                    "jobStatus": "completed"
                    }
                }
            output_service.update(item_properties)
            return output_service
        else:
            # Feature Collection
            return arcgis.features.FeatureCollection(job_values['output'])


    def summarize_within(self,
                       summary_layer,
                       output_name,
                       bin_size=None,
                       bin_size_unit=None,
                       bin_type="SQUARE",
                       sum_within_layer=None,
                       time_interval=None,
                       time_interval_unit=None,
                       time_repeat=None,
                       time_repeat_unit=None,
                       time_reference=None,
                       summary_fields=None,
                       proportional_weighting=False,
                       out_sr=None,
                         process_sr=None,
                       out_extent=None,
                       datastore="GDB"):
        """


        Parameters
        ----------
        summary_layer : Required FeatureSet

        bin_size : Optional float

        bin_size_unit : Optional string
            One of the following: ['Feet', 'Yards', 'Miles', 'Meters', 'Kilometers', 'Nautical Miles']
        bin_type : Optional string
            One of the following: ['SQUARE', 'HEXAGON']
        sum_within_layer : Optional FeatureSet

        time_interval : Optional int

        time_interval_unit : Optional string
            One of the following: ['Years', 'Months', 'Weeks', 'Days', 'Hours', 'Minutes', 'Seconds', 'Milliseconds']
        time_repeat : Optional int

        time_repeat_unit : Optional string
            One of the following: ['Years', 'Months', 'Weeks', 'Days', 'Hours', 'Minutes', 'Seconds', 'Milliseconds']
        time_reference : Optional datetime.date

        summary_fields : Optional string

        proportional_weighting : Optional bool

        output_name : Required string

        out_sr : Optional int

        process_sr : Optional int

        out_extent : Optional string

        datastore : Optional string
            One of the following: ['BDS', 'GDB']


        Returns
        -------
        output : layer (Feature Service item)
        """

        task ="SummarizeWithin"

        params = {}
        context = {}

        params["summaryLayer"] = super()._feature_input(summary_layer)
        if bin_size is not None:
            params["binSize"] = bin_size
        if bin_size_unit is not None:
            params["binSizeUnit"] = bin_size_unit
        if bin_type is not None:
            params["binType"] = bin_type
        if sum_within_layer is not None:
            params["sumWithinLayer"] = super()._feature_input(sum_within_layer)
        if time_interval is not None:
            params["timeInterval"] = time_interval
        if time_interval_unit is not None:
            params["timeIntervalUnit"] = time_interval_unit
        if time_repeat is not None:
            params["timeRepeat"] = time_repeat
        if time_repeat_unit is not None:
            params["timeRepeatUnit"] = time_repeat_unit
        if time_reference is not None:
            params["timeReference"] = time_reference
        if summary_fields is not None:
            params["summaryFields"] = summary_fields
        if proportional_weighting is not None:
            params["proportionalWeighting"] = proportional_weighting

        output_service = self._create_output_service(output_name, task)

        params["outputName"] = json.dumps({"serviceProperties": {"name" : output_name, "serviceUrl" : output_service.url}, "itemProperties": {"itemId" : output_service.itemid}})
        if out_sr is not None:
            context['outSR'] = {'wkid': int(out_sr)}
        if process_sr is not None:
            context['processSR'] = {'wkid': int(process_sr)}
        if out_extent is not None:
            context["extent"] = out_extent
        # if datastore is not None:
        #     params["gax:env:datastore"] = datastore
        if context is not None:
            params["context"] = json.dumps(context)

        task_url, job_info = super()._analysis_job(task, params)

        job_info = super()._analysis_job_status(task_url, job_info)
        job_values = super()._analysis_job_results(task_url, job_info)
        #print(job_values)
        if output_name is not None:
            #url = job_values['output']['url']
            #return FeatureLayer(url, self._gis) #item
            item_properties = {
                "properties":{
                    "jobUrl": task_url + '/jobs/' + job_info['jobId'],
                    "jobType": "GPServer",
                    "jobId": job_info['jobId'],
                    "jobStatus": "completed"
                    }
                }
            output_service.update(item_properties)
            return output_service
        else:
            # Feature Collection
            return arcgis.features.FeatureCollection(job_values['output'])


    def find_hot_spots(self,
                       point_layer,
                       bin_size,
                       bin_size_unit,
                       output_name,
                       time_step_interval=None,
                       time_step_interval_unit=None,
                       time_step_alignment=None,
                       referencetime=None,
                       neighborhood_distance=None,
                       neighborhood_distance_unit=None,
                       out_sr=None,
                       process_sr = None,
                       out_extent=None,
                       datastore="GDB"):
        """


        Parameters
        ----------
        point_layer : Required FeatureSet

        bin_size : Required float

        bin_size_unit : Required string
            One of the following: ['Feet', 'Yards', 'Miles', 'Meters', 'Kilometers', 'Nautical Miles']
        time_step_interval : Optional int

        time_step_interval_unit : Optional string
            One of the following: ['Years', 'Months', 'Weeks', 'Days', 'Hours', 'Minutes', 'Seconds', 'Milliseconds']
        time_step_alignment : Optional string
            One of the following: ['END_TIME', 'START_TIME', 'REFERENCE_TIME']
        referencetime : Optional datetime.date

        neighborhood_distance : Optional float

        neighborhood_distance_unit : Optional string
            One of the following: ['Feet', 'Yards', 'Miles', 'Meters', 'Kilometers', 'Nautical Miles']
        output_name : Required string

        out_sr : Optional int

        process_sr : Optional int

        out_extent : Optional string

        datastore : Optional string
            One of the following: ['BDS', 'GDB']


        Returns
        -------
        output : layer (Feature Service item)
        """

        task ="FindHotSpots"

        params = {}
        context = {}

        params["pointLayer"] = super()._feature_input(point_layer)
        params["binSize"] = bin_size
        params["binSizeUnit"] = bin_size_unit
        if time_step_interval is not None:
            params["time_step_interval"] = time_step_interval
        if time_step_interval_unit is not None:
            params["time_step_intervalUnit"] = time_step_interval_unit
        if time_step_alignment is not None:
            params["time_step_alignment"] = time_step_alignment
        if referencetime is not None:
            params["reference time"] = referencetime
        if neighborhood_distance is not None:
            params["neighborhoodDistance"] = neighborhood_distance
        if neighborhood_distance_unit is not None:
            params["neighborhoodDistanceUnit"] = neighborhood_distance_unit

        output_service = self._create_output_service(output_name, task)

        params["outputName"] = json.dumps({"serviceProperties": {"name" : output_name, "serviceUrl" : output_service.url}, "itemProperties": {"itemId" : output_service.itemid}})
        if out_sr is not None:
            context['outSR'] = {'wkid': int(out_sr)}
        if process_sr is not None:
            context['processSR'] = {'wkid': int(process_sr)}
        if out_extent is not None:
            context["extent"] = out_extent
        # if datastore is not None:
        #     params["gax:env:datastore"] = datastore
        if context is not None:
            params["context"] = json.dumps(context)

        task_url, job_info = super()._analysis_job(task, params)

        job_info = super()._analysis_job_status(task_url, job_info)
        job_values = super()._analysis_job_results(task_url, job_info)
        #print(job_values)
        if output_name is not None:
            #url = job_values['output']['url']
            #return FeatureLayer(url, self._gis) #item
            item_properties = {
                "properties":{
                    "jobUrl": task_url + '/jobs/' + job_info['jobId'],
                    "jobType": "GPServer",
                    "jobId": job_info['jobId'],
                    "jobStatus": "completed"
                    }
                }
            output_service.update(item_properties)
            return output_service
        else:
            # Feature Collection
            return arcgis.features.FeatureCollection(job_values['output'])


    # def find_similar_locations(self):
    #     """
    #
    #
    #     Parameters
    #     ----------
    #
    #     Returns
    #     -------
    #     """
    #
    #     task ="FindSimilarLocations"
    #
    #     params = {}
    #
    #     return { }


class _GeometryService(_GISService):
    """
    A geometry service contains utility methods that provide access to
    sophisticated and frequently used geometric operations. An ArcGIS
    Server web site can only expose one geometry service with the static
    name GeometryService.
    """

    def __init__(self, url, gis=None):
        super(_GeometryService, self).__init__(url, gis)

    @classmethod
    def fromitem(cls, item):
        if not item.type == 'Geometry Service':
            raise TypeError("item must be a type of Geometry Service, not " + item.type)
        return cls(item.url, item._gis)

    #----------------------------------------------------------------------
    def areas_and_lengths(self,
                        polygons,
                        lengthUnit,
                        areaUnit,
                        calculationType,
                        sr=4326):
        """
           The areasAndLengths operation is performed on a geometry service
           resource. This operation calculates areas and perimeter lengths
           for each polygon specified in the input array.

           Inputs:
              polygons - The array of polygons whose areas and lengths are
                         to be computed.
              lengthUnit - The length unit in which the perimeters of
                           polygons will be calculated. If calculationType
                           is planar, then lengthUnit can be any esriUnits
                           constant. If lengthUnit is not specified, the
                           units are derived from sr. If calculationType is
                           not planar, then lengthUnit must be a linear
                           esriUnits constant, such as esriSRUnit_Meter or
                           esriSRUnit_SurveyMile. If lengthUnit is not
                           specified, the units are meters. For a list of
                           valid units, see esriSRUnitType Constants and
                           esriSRUnit2Type Constant.
              areaUnit - The area unit in which areas of polygons will be
                         calculated. If calculationType is planar, then
                         areaUnit can be any esriUnits constant. If
                         areaUnit is not specified, the units are derived
                         from sr. If calculationType is not planar, then
                         areaUnit must be a linear esriUnits constant such
                         as esriSRUnit_Meter or esriSRUnit_SurveyMile. If
                         areaUnit is not specified, then the units are
                         meters. For a list of valid units, see
                         esriSRUnitType Constants and esriSRUnit2Type
                         constant.
                         The list of valid esriAreaUnits constants include,
                         esriSquareInches | esriSquareFeet |
                         esriSquareYards | esriAcres | esriSquareMiles |
                         esriSquareMillimeters | esriSquareCentimeters |
                         esriSquareDecimeters | esriSquareMeters | esriAres
                         | esriHectares | esriSquareKilometers.
              calculationType -  The type defined for the area and length
                                 calculation of the input geometries. The
                                 type can be one of the following values:
                                 planar - Planar measurements use 2D
                                          Euclidean distance to calculate
                                          area and length. Th- should
                                          only be used if the area or
                                          length needs to be calculated in
                                          the given spatial reference.
                                          Otherwise, use preserveShape.
                                 geodesic - Use this type if you want to
                                          calculate an area or length using
                                          only the vertices of the polygon
                                          and define the lines between the
                                          points as geodesic segments
                                          independent of the actual shape
                                          of the polygon. A geodesic
                                          segment is the shortest path
                                          between two points on an ellipsoid.
                                 preserveShape - This type calculates the
                                          area or length of the geometry on
                                          the surface of the Earth
                                          ellipsoid. The shape of the
                                          geometry in its coordinate system
                                          is preserved.
           Output:
              JSON as dictionary
        """
        url = self._url + "/areasAndLengths"
        params = {
            "f" : "json",
            "lengthUnit" : lengthUnit,
            "areaUnit" : {"areaUnit" : areaUnit},
            "calculationType" : calculationType,
            'sr' : sr
        }
        if isinstance(polygons, list) and len(polygons) > 0:
            p = polygons[0]
            if isinstance(p, Polygon):
                if hasattr(p, 'spatialReference'):
                    params['sr'] = p.spatialReference
                params['polygons'] = polygons
            elif isinstance(p, dict):
                params['polygons'] = polygons
            del p
        elif isinstance(polygons, dict):
            params['polygons'] = [polygons]
        elif isinstance(polygons, Polygon):
            params['polygons'] = [polygons]
        else:
            return "No polygons provided, please submit a list of polygon geometries"
        return self._con.post(path=url, postdata=params, token=self._token)
    #----------------------------------------------------------------------
    def __geometryListToGeomTemplate(self, geometries):
        """
            converts a list of common.Geometry objects to the geometry
            template value
            Input:
               geometries - list of common.Geometry objects
            Output:
               Dictionary in geometry service template
        """
        template = {"geometryType": None,
                    "geometries" : []}
        if isinstance(geometries, list) and len(geometries) > 0:
            for g in geometries:

                if not isinstance(g, Geometry):
                    g = Geometry(g)

                if isinstance(g, Polyline):
                    template['geometryType'] = "esriGeometryPolyline"
                elif isinstance(g, Polygon):
                    template['geometryType'] = "esriGeometryPolygon"
                elif isinstance(g, Point):
                    template['geometryType'] = "esriGeometryPoint"
                elif isinstance(g, MultiPoint):
                    template['geometryType'] = "esriGeometryMultipoint"
                elif isinstance(g, Envelope):
                    template['geometryType'] = "esriGeometryEnvelope"
                else:
                    raise AttributeError("Invalid geometry type")
                template['geometries'].append(g)
                del g
            return template
        return template
    #----------------------------------------------------------------------
    def __geometryToGeomTemplate(self, geometry):
        """
           Converts a single geometry object to a geometry service geometry
           template value.

           Input:
              geometry - geometry object
           Output:
              python dictionary of geometry template
        """
        template = {"geometryType": None,
                    "geometry" : None}

        if not isinstance(geometry, Geometry):
            geometry = Geometry(geometry)
        if isinstance(geometry, Polyline):
            template['geometryType'] = "esriGeometryPolyline"
        elif isinstance(geometry, Polygon):
            template['geometryType'] = "esriGeometryPolygon"
        elif isinstance(geometry, Point):
            template['geometryType'] = "esriGeometryPoint"
        elif isinstance(geometry, MultiPoint):
            template['geometryType'] = "esriGeometryMultipoint"
        elif isinstance(geometry, Envelope):
            template['geometryType'] = "esriGeometryEnvelope"
        else:
            raise AttributeError("Invalid geometry type")
        template['geometry'] = geometry
        return template
    #----------------------------------------------------------------------
    def __geomToStringArray(self, geometries, returnType="str"):
        """ function to convert the geomtries to strings """
        listGeoms = []
        for g in geometries:

            if not isinstance(g, Geometry):
                g = Geometry(g)
            if isinstance(g, Point):
                listGeoms.append(g)
            elif isinstance(g, Polygon):
                listGeoms.append(g)
            elif isinstance(g, Polyline):
                listGeoms.append({'paths' : g['paths']})
        if returnType == "str":
            return json.dumps(listGeoms)
        elif returnType == "list":
            return listGeoms
        else:
            return json.dumps(listGeoms)
    #----------------------------------------------------------------------
    def _process_results(self, results):
        if isinstance(results, list):
            vals = []
            for result in results:
                if isinstance(result, dict):
                    vals.append(Geometry(result))
                del result
            return vals
        elif isinstance(results, dict):
            if 'geometries' in results:
                return self._process_results(results['geometries'])
            elif 'geometry' in results:
                return Geometry(results['geometry'])
            else:
                return Geometry(results)
        else:
            return results
    #----------------------------------------------------------------------
    def auto_complete(self,
                     polygons=None,
                     polylines=None,
                     sr=None
                     ):
        """
           The autoComplete operation simplifies the process of
           constructing new polygons that are adjacent to other polygons.
           It constructs polygons that fill in the gaps between existing
           polygons and a set of polylines.

           Inputs:
              polygons - array of Polygon objects
              polylines - list of Polyline objects
              sr - spatial reference of the input geometries WKID
        """
        url = self._url + "/autoComplete"
        params = {"f":"json"}
        if polygons is None:
            polygons = []
        if polylines is None:
            polylines = []
        if sr is not None:
            params['sr'] = sr
        if isinstance(polygons, list):
            params['polygons'] = polygons
        elif isinstance(polygons, Polygon):
            params['polygons'] = [polygons]
        if isinstance(polylines, Polyline):
            params['polylines'] = [polylines]
        elif isinstance(polylines, list):
            params['polylines'] = polylines
        result = self._con.post(path=url, postdata=params, token=self._token)
        if 'error' in result:
            return result
        return self._process_results(result)
    #----------------------------------------------------------------------
    def buffer(self,
               geometries,
               inSR,
               distances,
               unit,
               outSR=None,
               bufferSR=None,
               unionResults=None,
               geodesic=None
               ):
        """
           The buffer operation is performed on a geometry service resource
           The result of this operation is buffered polygons at the
           specified distances for the input geometry array. Options are
           available to union buffers and to use geodesic distance.

           Inputs:
             geometries - The array of geometries to be buffered.
             isSR - The well-known ID of the spatial reference or a spatial
              reference JSON object for the input geometries.
             distances - The distances that each of the input geometries is
              buffered.
             unit - The units for calculating each buffer distance. If unit
              is not specified, the units are derived from bufferSR. If
              bufferSR is not specified, the units are derived from inSR.
             outSR - The well-known ID of the spatial reference or a
              spatial reference JSON object for the input geometries.
             bufferSR - The well-known ID of the spatial reference or a
              spatial reference JSON object for the input geometries.
             unionResults -  If true, all geometries buffered at a given
              distance are unioned into a single (possibly multipart)
              polygon, and the unioned geometry is placed in the output
              array. The default is false
             geodesic - Set geodesic to true to buffer the input geometries
              using geodesic distance. Geodesic distance is the shortest
              path between two points along the ellipsoid of the earth. If
              geodesic is set to false, the 2D Euclidean distance is used
              to buffer the input geometries. The default value depends on
              the geometry type, unit and bufferSR.
        """
        url = self._url + "/buffer"
        params = {
            "f" : "json",
            "inSR" : inSR
        }
        if geodesic is not None:
            params['geodesic'] = geodesic
        if unionResults is not None:
            params['unionResults'] = unionResults

        if isinstance(geometries, list) and len(geometries) > 0:
            g = geometries[0]
            if isinstance(g, Polygon):
                params['geometries'] = {"geometryType": "esriGeometryPolygon",
                                        "geometries" : self.__geomToStringArray(geometries, "list")}
            elif isinstance(g, Point):
                params['geometries'] = {"geometryType": "esriGeometryPoint",
                                        "geometries" : self.__geomToStringArray(geometries, "list")}
            elif isinstance(g, Polyline):
                params['geometries'] = {"geometryType": "esriGeometryPolyline",
                                                        "geometries" : self.__geomToStringArray(geometries, "list")}
            elif isinstance(g, dict):
                params['geometries'] = geometries
            else:
                print('The passed in geometries are in an unsupported format. '
                      'List of dicts or Geometry objects are supported')
                return None
        if isinstance(distances, list):
            distances = [str(d) for d in distances]

            params['distances'] = ",".join(distances)
        else:
            params['distances'] = str(distances)
        params['units'] = unit
        if bufferSR is not None:
            params['bufferSR'] = bufferSR
        if outSR is not None:
            params['outSR'] = outSR

        results = self._con.post(path=url, postdata=params, token=self._token)
        if 'error' in results:
            return results
        return self._process_results(results)
    #----------------------------------------------------------------------
    def convex_hull(self,
                   geometries,
                   sr=None):
        """
        The convexHull operation is performed on a geometry service
        resource. It returns the convex hull of the input geometry. The
        input geometry can be a point, multipoint, polyline, or polygon.
        The convex hull is typically a polygon but can also be a polyline
        or point in degenerate cases.

        Inputs:
           geometries - The geometries whose convex hull is to be created.
           sr - The well-known ID or a spatial reference JSON object for
                the output geometry.
        """
        url = self._url + "/convexHull"
        params = {
            "f" : "json"
        }
        if isinstance(geometries, list) and len(geometries) > 0:
            g = geometries[0]
            if sr is not None:
                params['sr'] = sr
            else:
                params['sr'] = g.spatialreference
            if isinstance(g, Polygon):
                params['geometries'] = {"geometryType": "esriGeometryPolygon",
                                        "geometries" : self.__geomToStringArray(geometries, "list")}
            elif isinstance(g, Point):
                params['geometries'] = {"geometryType": "esriGeometryPoint",
                                        "geometries" : self.__geomToStringArray(geometries, "list")}
            elif isinstance(g, Polyline):
                params['geometries'] = {"geometryType": "esriGeometryPolyline",
                                                        "geometries" : self.__geomToStringArray(geometries, "list")}
        else:
            return None
        results = self._con.post(path=url, postdata=params, token=self._token)
        if 'error' in results:
            return results
        return self._process_results(results)
    #----------------------------------------------------------------------
    def cut(self,
            cutter,
            target,
            sr=None):
        """
        The cut operation is performed on a geometry service resource. This
        operation splits the target polyline or polygon where it's crossed
        by the cutter polyline.
        At 10.1 and later, this operation calls simplify on the input
        cutter and target geometries.

        Inputs:
           cutter - The polyline that will be used to divide the target
            into pieces where it crosses the target.The spatial reference
            of the polylines is specified by sr. The structure of the
            polyline is the same as the structure of the JSON polyline
            objects returned by the ArcGIS REST API.
           target - The array of polylines/polygons to be cut. The
            structure of the geometry is the same as the structure of the
            JSON geometry objects returned by the ArcGIS REST API. The
            spatial reference of the target geometry array is specified by
            sr.
           sr - The well-known ID or a spatial reference JSON object for
            the output geometry.
        """
        url = self._url + "/cut"
        params = {
            "f" : "json"
        }
        if sr is not None:
            params['sr'] = sr
        if isinstance(cutter, (Polyline, dict)):
            params['cutter'] = cutter
        else:
            raise AttributeError("Input must be type Polyline/Dictionary")
        if isinstance(target, list) and len(target) > 0:
            template = {"geometryType": "",
                        "geometries" : []}
            for g in target:
                if isinstance(g, Polygon):
                    template['geometryType'] = "esriGeometryPolygon"
                    template['geometries'].append(g)
                if isinstance(g, Polyline):
                    template['geometryType'] = "esriGeometryPolyline"
                    template['geometries'].append(g)
                else:
                    AttributeError("Invalid geometry in target, entries can only be Polygon or Polyline")
                del g
            params['target'] = template
        else:
            AttributeError("You must provide at least 1 Polygon/Polyline geometry in a list")
        results = self._con.post(path=url, postdata=params, token=self._token)
        if 'error' in results:
            return results
        return self._process_results(results)
    #----------------------------------------------------------------------
    def densify(self,
                geometries,
                sr,
                maxSegmentLength,
                lengthUnit,
                geodesic=False,
                ):
        """
        The densify operation is performed on a geometry service resource.
        This operation densifies geometries by plotting points between
        existing vertices.

        Inputs:
           geometries - The array of geometries to be densified. The
            structure of each geometry in the array is the same as the
            structure of the JSON geometry objects returned by the ArcGIS
            REST API.
           sr - The well-known ID or a spatial reference JSON object for
            the input polylines. For a list of valid WKID values, see
            Projected coordinate systems and Geographic coordinate systems.
           maxSegmentLength - All segments longer than maxSegmentLength are
            replaced with sequences of lines no longer than
            maxSegmentLength.
           lengthUnit - The length unit of maxSegmentLength. If geodesic is
            set to false, then the units are derived from sr, and
            lengthUnit is ignored. If geodesic is set to true, then
            lengthUnit must be a linear unit. In a case where lengthUnit is
            not specified and sr is a PCS, the units are derived from sr.
            In a case where lengthUnit is not specified and sr is a GCS,
            then the units are meters.
           geodesic - If geodesic is set to true, then geodesic distance is
            used to calculate maxSegmentLength. Geodesic distance is the
            shortest path between two points along the ellipsoid of the
            earth. If geodesic is set to false, then 2D Euclidean distance
            is used to calculate maxSegmentLength. The default is false.
        """
        url = self._url + "/densify"
        template = {"geometryType": None,
                    "geometries" : []}
        params = {
            "f" : "json",
            "sr" : sr,
            "maxSegmentLength" : maxSegmentLength,
            "lengthUnit" : lengthUnit,
            "geodesic" : geodesic
        }
        if isinstance(geometries, list) and len(geometries) > 0:
            for g in geometries:

                if not isinstance(g, Geometry):
                    g = Geometry(g)
                if isinstance(g, Polyline):
                    template['geometryType'] = "esriGeometryPolyline"
                elif isinstance(g, Polygon):
                    template['geometryType'] = "esriGeometryPolygon"
                else:
                    raise AttributeError("Invalid geometry type")

                template['geometries'].append(g)

        elif isinstance(geometries, dict):

            if not isinstance(geometries, Geometry):
                g = Geometry(geometries)

            if isinstance(g, Polyline):
                template['geometryType'] = "esriGeometryPolyline"
            elif isinstance(g, Polygon):
                template['geometryType'] = "esriGeometryPolygon"
            template['geometries'].append(g)
        params['geometries'] = template
        results =  self._con.post(path=url, postdata=params, token=self._token)
        if 'error' in results:
            return results
        return self._process_results(results)
    #----------------------------------------------------------------------
    def difference(self,
                   geometries,
                   sr,
                   geometry
                   ):
        """
        The difference operation is performed on a geometry service
        resource. This operation constructs the set-theoretic difference
        between each element of an array of geometries and another geometry
        the so-called difference geometry. In other words, let B be the
        difference geometry. For each geometry, A, in the input geometry
        array, it constructs A-B.

        Inputs:
          geometries -  An array of points, multipoints, polylines or
           polygons. The structure of each geometry in the array is the
           same as the structure of the JSON geometry objects returned by
           the ArcGIS REST API.
          geometry - A single geometry of any type and of a dimension equal
           to or greater than the elements of geometries. The structure of
           geometry is the same as the structure of the JSON geometry
           objects returned by the ArcGIS REST API. The use of simple
           syntax is not supported.
          sr - The well-known ID of the spatial reference or a spatial
           reference JSON object for the input geometries.
        """
        url = self._url + "/difference"
        params = {
            "f" : "json",
            "sr" : sr

        }
        if isinstance(geometries, list) and len(geometries) > 0:
            template = {"geometryType": None,
                        "geometries" : []}
            for g in geometries:
                if isinstance(g, Polyline):
                    template['geometryType'] = "esriGeometryPolyline"
                elif isinstance(g, Polygon):
                    template['geometryType'] = "esriGeometryPolygon"
                elif isinstance(g, Point):
                    template['geometryType'] = "esriGeometryPoint"
                elif isinstance(g, Point):
                    template['geometryType'] = "esriGeometryMultipoint"
                else:
                    raise AttributeError("Invalid geometry type")
                template['geometries'].append(g)
                del g
            params['geometries'] = template
        geomTemplate = {"geometryType": None,
                        "geometries" : []
                        }
        if isinstance(geometry, Polyline):
            geomTemplate['geometryType'] = "esriGeometryPolyline"
        elif isinstance(geometry, Polygon):
            geomTemplate['geometryType'] = "esriGeometryPolygon"
        elif isinstance(geometry, Point):
            geomTemplate['geometryType'] = "esriGeometryPoint"
        elif isinstance(geometry, Point):
            geomTemplate['geometryType'] = "esriGeometryMultipoint"
        else:
            raise AttributeError("Invalid geometry type")
        geomTemplate['geometry'] = geometry
        params['geometry'] = geomTemplate
        results =  self._con.post(path=url, postdata=params, token=self._token)
        if 'error' in results:
            return results
        return self._process_results(results)
    #----------------------------------------------------------------------
    def distance(self,
                 sr,
                 geometry1,
                 geometry2,
                 distanceUnit="",
                 geodesic=False
                 ):
        """
        The distance operation is performed on a geometry service resource.
        It reports the 2D Euclidean or geodesic distance between the two
        geometries.

        Inputs:
         sr - The well-known ID or a spatial reference JSON object for
          input geometries.
         geometry1 - The geometry from which the distance is to be
          measured. The structure of the geometry is same as the structure
          of the JSON geometry objects returned by the ArcGIS REST API.
         geometry2 - The geometry from which the distance is to be
          measured. The structure of the geometry is same as the structure
          of the JSON geometry objects returned by the ArcGIS REST API.
         distanceUnit - specifies the units for measuring distance between
          the geometry1 and geometry2 geometries.
         geodesic - If geodesic is set to true, then the geodesic distance
          between the geometry1 and geometry2 geometries is returned.
          Geodesic distance is the shortest path between two points along
          the ellipsoid of the earth. If geodesic is set to false or not
          specified, the planar distance is returned. The default value is
          false.
        """
        url = self._url + "/distance"
        params = {
            "f" : "json",
            "sr" : sr,
            "distanceUnit" : distanceUnit,
            "geodesic" : geodesic
        }
        geometry1 = self.__geometryToGeomTemplate(geometry=geometry1)
        geometry2 = self.__geometryToGeomTemplate(geometry=geometry2)
        params['geometry1'] = geometry1
        params['geometry2'] = geometry2
        return self._con.post(path=url, postdata=params, token=self._token)
    #----------------------------------------------------------------------
    def find_transformation(self, inSR, outSR, extentOfInterest=None, numOfResults=1):
        """
        The findTransformations operation is performed on a geometry
        service resource. This operation returns a list of applicable
        geographic transformations you should use when projecting
        geometries from the input spatial reference to the output spatial
        reference. The transformations are in JSON format and are returned
        in order of most applicable to least applicable. Recall that a
        geographic transformation is not needed when the input and output
        spatial references have the same underlying geographic coordinate
        systems. In this case, findTransformations returns an empty list.
        Every returned geographic transformation is a forward
        transformation meaning that it can be used as-is to project from
        the input spatial reference to the output spatial reference. In the
        case where a predefined transformation needs to be applied in the
        reverse direction, it is returned as a forward composite
        transformation containing one transformation and a transformForward
        element with a value of false.

        Inputs:
           inSR - The well-known ID (WKID) of the spatial reference or a
             spatial reference JSON object for the input geometries
           outSR - The well-known ID (WKID) of the spatial reference or a
             spatial reference JSON object for the input geometries
           extentOfInterest -  The bounding box of the area of interest
             specified as a JSON envelope. If provided, the extent of
             interest is used to return the most applicable geographic
             transformations for the area. If a spatial reference is not
             included in the JSON envelope, the inSR is used for the
             envelope.
           numOfResults - The number of geographic transformations to
             return. The default value is 1. If numOfResults has a value of
             -1, all applicable transformations are returned.
        """
        params = {
            "f" : "json",
            "inSR" : inSR,
            "outSR" : outSR
        }
        url = self._url + "/findTransformations"
        if isinstance(numOfResults, int):
            params['numOfResults'] = numOfResults
        if isinstance(extentOfInterest, Envelope):
            params['extentOfInterest'] = extentOfInterest
        return self._con.post(path=url, postdata=params, token=self._token)
    #----------------------------------------------------------------------
    def from_geo_coordinate_string(self, sr, strings,
                                conversionType, conversionMode=None):
        """
        The from_geo_coordinate_string operation is performed on a geometry
        service resource. The operation converts an array of well-known
        strings into xy-coordinates based on the conversion type and
        spatial reference supplied by the user. An optional conversion mode
        parameter is available for some conversion types.

        Inputs:
         sr - The well-known ID of the spatial reference or a spatial
          reference json object.
         strings - An array of strings formatted as specified by
          conversionType.
          Syntax: [<string1>,...,<stringN>]
          Example: ["01N AA 66021 00000","11S NT 00000 62155",
                    "31U BT 94071 65288"]
         conversionType - The conversion type of the input strings.
          Valid conversion types are:
           MGRS - Military Grid Reference System
           USNG - United States National Grid
           UTM - Universal Transverse Mercator
           GeoRef - World Geographic Reference System
           GARS - Global Area Reference System
           DMS - Degree Minute Second
           DDM - Degree Decimal Minute
           DD - Decimal Degree
         conversionMode - Conversion options for MGRS, UTM and GARS
          conversion types.
          Conversion options for MGRS and UTM conversion types.
          Valid conversion modes for MGRS are:
           mgrsDefault - Default. Uses the spheroid from the given spatial
            reference.
           mgrsNewStyle - Treats all spheroids as new, like WGS 1984. The
            180 degree longitude falls into Zone 60.
           mgrsOldStyle - Treats all spheroids as old, like Bessel 1841.
            The 180 degree longitude falls into Zone 60.
           mgrsNewWith180InZone01 - Same as mgrsNewStyle except the 180
            degree longitude falls into Zone 01.
           mgrsOldWith180InZone01 - Same as mgrsOldStyle except the 180
            degree longitude falls into Zone 01.
          Valid conversion modes for UTM are:
           utmDefault - Default. No options.
           utmNorthSouth - Uses north/south latitude indicators instead of
            zone numbers. Non-standard. Default is recommended
        """
        url = self._url + "/fromGeoCoordinateString"
        params = {
            "f" : "json",
            "sr" : sr,
            "strings" : strings,
            "conversionType" : conversionType
        }
        if not conversionMode is None:
            params['conversionMode'] = conversionMode
        return self._con.post(path=url, postdata=params, token=self._token)
    #----------------------------------------------------------------------
    def generalize(self,
                   sr,
                   geometries,
                   maxDeviation,
                   deviationUnit):
        """
        The generalize operation is performed on a geometry service
        resource. The generalize operation simplifies the input geometries
        using the Douglas-Peucker algorithm with a specified maximum
        deviation distance. The output geometries will contain a subset of
        the original input vertices.

        Inputs:
         sr - The well-known ID or a spatial reference JSON object for the
          input geometries.
         geometries - The array of geometries to be generalized.
         maxDeviation - maxDeviation sets the maximum allowable offset,
          which will determine the degree of simplification. This value
          limits the distance the output geometry can differ from the input
          geometry.
         deviationUnit - A unit for maximum deviation. If a unit is not
          specified, the units are derived from sr.
        """
        url = self._url + "/generalize"
        params = {
            "f" : "json",
            "sr" : sr,
            "deviationUnit" : deviationUnit,
            "maxDeviation": maxDeviation
        }
        params['geometries'] = self.__geometryListToGeomTemplate(geometries=geometries)
        results =  self._con.post(path=url, postdata=params, token=self._token)
        if 'error' in results:
            return results
        return self._process_results(results)
    #----------------------------------------------------------------------
    def intersect(self,
                  sr,
                  geometries,
                  geometry
                  ):
        """
        The intersect operation is performed on a geometry service
        resource. This operation constructs the set-theoretic intersection
        between an array of geometries and another geometry. The dimension
        of each resultant geometry is the minimum dimension of the input
        geometry in the geometries array and the other geometry specified
        by the geometry parameter.

        Inputs:
         sr - The well-known ID or a spatial reference JSON object for the
          input geometries.
         geometries - An array of points, multipoints, polylines, or
          polygons. The structure of each geometry in the array is the same
          as the structure of the JSON geometry objects returned by the
          ArcGIS REST API.
         geometry - A single geometry of any type with a dimension equal to
          or greater than the elements of geometries.
        """
        url = self._url + "/intersect"
        params = {
            "f" : "json",
            "sr" : sr,
            "geometries" : self.__geometryListToGeomTemplate(geometries=geometries),
            "geometry" : self.__geometryToGeomTemplate(geometry=geometry)
        }
        results =  self._con.post(path=url, postdata=params, token=self._token)
        if 'error' in results:
            return results
        return self._process_results(results)
    #----------------------------------------------------------------------
    def label_points(self,
                    sr,
                    polygons,
                    ):
        """
        The label_points operation is performed on a geometry service
        resource. The labelPoints operation calculates an interior point
        for each polygon specified in the input array. These interior
        points can be used by clients for labeling the polygons.

        Inputs:
         sr - The well-known ID of the spatial reference or a spatial
          reference JSON object for the input polygons.
         polygons - The array of polygons whose label points are to be
          computed. The spatial reference of the polygons is specified by
          sr.
        """
        url = self._url + "/labelPoints"
        params = {
            "f" : "json",
            "sr" : sr,
            "polygons": self.__geomToStringArray(geometries=polygons,
                                                 returnType="list")
        }
        results =  self._con.post(path=url, postdata=params, token=self._token)
        if 'error' in results:
            return results
        return results
    #----------------------------------------------------------------------
    def lengths(self,
                sr,
                polylines,
                lengthUnit,
                calculationType
                ):
        """
        The lengths operation is performed on a geometry service resource.
        This operation calculates the 2D Euclidean or geodesic lengths of
        each polyline specified in the input array.

        Inputs:
         sr - The well-known ID of the spatial reference or a spatial
          reference JSON object for the input polylines.
         polylines - The array of polylines whose lengths are to be
          computed.
         lengthUnit - The unit in which lengths of polylines will be
          calculated. If calculationType is planar, then lengthUnit can be
          any esriUnits constant. If calculationType is planar and
          lengthUnit is not specified, then the units are derived from sr.
          If calculationType is not planar, then lengthUnit must be a
          linear esriUnits constant such as esriSRUnit_Meter or
          esriSRUnit_SurveyMile. If calculationType is not planar and
          lengthUnit is not specified, then the units are meters.
         calculationType - calculationType defines the length calculation
          for the geometry. The type can be one of the following values:
            planar - Planar measurements use 2D Euclidean distance to
             calculate length. This type should only be used if the length
             needs to be calculated in the given spatial reference.
             Otherwise, use preserveShape.
            geodesic - Use this type if you want to calculate a length
             using only the vertices of the polygon and define the lines
             between the vertices as geodesic segments independent of the
             actual shape of the polyline. A geodesic segment is the
             shortest path between two points on an earth ellipsoid.
            preserveShape - This type calculates the length of the geometry
             on the surface of the earth ellipsoid. The shape of the
             geometry in its coordinate system is preserved.
        """
        allowedCalcTypes = ['planar', 'geodesic', 'preserveShape']
        if calculationType not in allowedCalcTypes:
            raise AttributeError("Invalid calculation Type")
        url = self._url + "/lengths"
        params = {
            "f" : "json",
            "sr" : sr,
            "polylines": self.__geomToStringArray(geometries=polylines,
                                                 returnType="list"),
            "lengthUnit" : lengthUnit,
            "calculationType" : calculationType
        }
        res = self._con.post(path=url, postdata=params, token=self._token)
        if res is not None and 'lengths' in res:
            return res['lengths']
        else:
            return res
    #----------------------------------------------------------------------
    def offset(self,
               geometries,
               offsetDistance,
               offsetUnit,
               offsetHow="esriGeometryOffsetRounded",
               bevelRatio=10,
               simplifyResult=False,
               sr=None,
               ):
        """
        The offset operation is performed on a geometry service resource.
        This operation constructs geometries that are offset from the
        given input geometries. If the offset parameter is positive, the
        constructed offset will be on the right side of the geometry. Left
        side offsets are constructed with negative parameters. Tracing the
        geometry from its first vertex to the last will give you a
        direction along the geometry. It is to the right and left
        perspective of this direction that the positive and negative
        parameters will dictate where the offset is constructed. In these
        terms, it is simple to infer where the offset of even horizontal
        geometries will be constructed.

        Inputs:
         geometries -  The array of geometries to be offset.
         offsetDistance - Specifies the distance for constructing an offset
          based on the input geometries. If the offsetDistance parameter is
          positive, the constructed offset will be on the right side of the
          curve. Left-side offsets are constructed with negative values.
         offsetUnit - A unit for offset distance. If a unit is not
          specified, the units are derived from sr.
         offsetHow - The offsetHow parameter determines how outer corners
          between segments are handled. The three options are as follows:
           esriGeometryOffsetRounded - Rounds the corner between extended
            offsets.
           esriGeometryOffsetBevelled - Squares off the corner after a
            given ratio distance.
           esriGeometryOffsetMitered - Attempts to allow extended offsets
            to naturally intersect, but if that intersection occurs too far
            from the corner, the corner is eventually bevelled off at a
            fixed distance.
         bevelRatio - bevelRatio is multiplied by the offset distance, and
          the result determines how far a mitered offset intersection can
          be located before it is bevelled. When mitered is specified,
          bevelRatio is ignored and 10 is used internally. When bevelled is
          specified, 1.1 will be used if bevelRatio is not specified.
          bevelRatio is ignored for rounded offset.
         simplifyResult - if simplifyResult is set to true, then self
          intersecting loops will be removed from the result offset
          geometries. The default is false.
         sr - The well-known ID or a spatial reference JSON object for the
          input geometries.
        """
        allowedHow = ["esriGeometryOffsetRounded",
                      "esriGeometryOffsetBevelled",
                      "esriGeometryOffsetMitered"]
        if offsetHow not in allowedHow:
            raise AttributeError("Invalid Offset How value")
        url = self._url + "/offset"
        params = {
            "f" : "json",
            "sr" : sr,
            "geometries": self.__geometryListToGeomTemplate(geometries=geometries),
            "offsetDistance": offsetDistance,
            "offsetUnit" : offsetUnit,
            "offsetHow" : offsetHow,
            "bevelRatio" : bevelRatio,
            "simplifyResult" : json.dumps(simplifyResult)
        }
        results =  self._con.post(path=url, postdata=params, token=self._token)
        if 'error' in results:
            return results
        return self._process_results(results)
    #----------------------------------------------------------------------
    def project(self,
                geometries,
                inSR,
                outSR,
                transformation="",
                transformFoward=False):
        """
        The project operation is performed on a geometry service resource.
        This operation projects an array of input geometries from the input
        spatial reference to the output spatial reference.

        Inputs:
         geometries - The array of geometries to be projected.
         inSR - The well-known ID (WKID) of the spatial reference or a
          spatial reference JSON object for the input geometries.
         outSR - The well-known ID (WKID) of the spatial reference or a
          spatial reference JSON object for the input geometries.
         transformation - The WKID or a JSON object specifying the
          geographic transformation (also known as datum transformation) to
          be applied to the projected geometries. Note that a
          transformation is needed only if the output spatial reference
          contains a different geographic coordinate system than the input
          spatial reference.
         transformForward - A Boolean value indicating whether or not to
          transform forward. The forward or reverse direction of
          transformation is implied in the name of the transformation. If
          transformation is specified, a value for the transformForward
          parameter must also be specified. The default value is false.
        """
        url = self._url + "/project"
        params = {
            "f" : "json",
            "inSR" : inSR,
            "geometries": self.__geometryListToGeomTemplate(geometries=geometries),
            "outSR" : outSR,
            "transformation" : transformation,
            "transformFoward": transformFoward
        }
        results =  self._con.post(path=url, postdata=params, token=self._token)
        if 'error' in results:
            return results
        return self._process_results(results)
    #----------------------------------------------------------------------
    def relation(self,
                 geometries1,
                 geometries2,
                 sr,
                 relation="esriGeometryRelationIntersection",
                 relationParam=""):
        """
        The relation operation is performed on a geometry service resource.
        This operation determines the pairs of geometries from the input
        geometry arrays that participate in the specified spatial relation.
        Both arrays are assumed to be in the spatial reference specified by
        sr, which is a required parameter. Geometry types cannot be mixed
        within an array. The relations are evaluated in 2D. In other words,
        z coordinates are not used.

        Inputs:
         geometries1 - The first array of geometries used to compute the
          relations.
         geometries2 -The second array of geometries used to compute the
         relations.
         sr - The well-known ID of the spatial reference or a spatial
          reference JSON object for the input geometries.
         relation - The spatial relationship to be tested between the two
          input geometry arrays.
          Values: esriGeometryRelationCross | esriGeometryRelationDisjoint |
          esriGeometryRelationIn | esriGeometryRelationInteriorIntersection |
          esriGeometryRelationIntersection | esriGeometryRelationLineCoincidence |
          esriGeometryRelationLineTouch | esriGeometryRelationOverlap |
          esriGeometryRelationPointTouch | esriGeometryRelationTouch |
          esriGeometryRelationWithin | esriGeometryRelationRelation
         relationParam - The Shape Comparison Language string to be
          evaluated.
        """
        relationType = [
            "esriGeometryRelationCross",
            "esriGeometryRelationDisjoint",
            "esriGeometryRelationIn",
            "esriGeometryRelationInteriorIntersection",
            "esriGeometryRelationIntersection",
            "esriGeometryRelationLineCoincidence",
            "esriGeometryRelationLineTouch",
            "esriGeometryRelationOverlap",
            "esriGeometryRelationPointTouch",
            "esriGeometryRelationTouch",
            "esriGeometryRelationWithin",
            "esriGeometryRelationRelation"
        ]
        if relation not in relationType:
            raise AttributeError("Invalid relation type")
        url = self._url + "/relation"
        params = {
            "f" : "json",
            "sr" : sr,
            "geometries1": self.__geometryListToGeomTemplate(geometries=geometries1),
            "geometries2": self.__geometryListToGeomTemplate(geometries=geometries2),
            "relation" : relation,
            "relationParam" : relationParam
        }
        return self._con.post(path=url, postdata=params, token=self._token)
    #----------------------------------------------------------------------
    def reshape(self,
                sr,
                target,
                reshaper
                ):
        """
        The reshape operation is performed on a geometry service resource.
        It reshapes a polyline or polygon feature by constructing a
        polyline over the feature. The feature takes the shape of the
        reshaper polyline from the first place the reshaper intersects the
        feature to the last.

        Input:
         sr - The well-known ID of the spatial reference or a spatial
          reference JSON object for the input geometries.
         target -  The polyline or polygon to be reshaped.
         reshaper - The single-part polyline that does the reshaping.
        """
        url = self._url + "/reshape"
        params = {
            "f" : "json",
            "sr" : sr,
            "target" : self.__geometryToGeomTemplate(geometry=target)
        }
        if isinstance(reshaper, Polyline):
            params["reshaper"] = reshaper
        elif isinstance(reshaper, dict):
            params['reshaper'] = reshaper
        else:
            raise AttributeError("Invalid reshaper object, must be Polyline")
        results =  self._con.post(path=url, postdata=params, token=self._token)
        if 'error' in results:
            return results
        return self._process_results(results)
    #----------------------------------------------------------------------
    def simplify(self,
                 sr,
                 geometries
                 ):
        """
        The simplify operation is performed on a geometry service resource.
        Simplify permanently alters the input geometry so that the geometry
        becomes topologically consistent. This resource applies the ArcGIS
        simplify operation to each geometry in the input array.

        Inputs:
        sr - The well-known ID of the spatial reference or a spatial
          reference JSON object for the input geometries.
        geometries - The array of geometries to be simplified.
        """
        url = self._url + "/simplify"
        params = {
            "f" : "json",
            "sr" : sr,
            "geometries" : self.__geometryListToGeomTemplate(geometries=geometries)
        }
        results =  self._con.post(path=url, postdata=params, token=self._token)
        if 'error' in results:
            return results
        return self._process_results(results)
    #----------------------------------------------------------------------
    def to_geo_coordinate_string(self,
                              sr,
                              coordinates,
                              conversionType,
                              conversionMode="mgrsDefault",
                              numOfDigits=None,
                              rounding=True,
                              addSpaces=True
                              ):
        """
        The toGeoCoordinateString operation is performed on a geometry
        service resource. The operation converts an array of
        xy-coordinates into well-known strings based on the conversion type
        and spatial reference supplied by the user. Optional parameters are
        available for some conversion types. Note that if an optional
        parameter is not applicable for a particular conversion type, but a
        value is supplied for that parameter, the value will be ignored.

        Inputs:
          sr -  The well-known ID of the spatial reference or a spatial
           reference json object.
          coordinates - An array of xy-coordinates in JSON format to be
           converted. Syntax: [[x1,y2],...[xN,yN]]
          conversionType - The conversion type of the input strings.
           Allowed Values:
            MGRS - Military Grid Reference System
            USNG - United States National Grid
            UTM - Universal Transverse Mercator
            GeoRef - World Geographic Reference System
            GARS - Global Area Reference System
            DMS - Degree Minute Second
            DDM - Degree Decimal Minute
            DD - Decimal Degree
          conversionMode - Conversion options for MGRS and UTM conversion
           types.
           Valid conversion modes for MGRS are:
            mgrsDefault - Default. Uses the spheroid from the given spatial
             reference.
            mgrsNewStyle - Treats all spheroids as new, like WGS 1984. The
             180 degree longitude falls into Zone 60.
            mgrsOldStyle - Treats all spheroids as old, like Bessel 1841.
             The 180 degree longitude falls into Zone 60.
            mgrsNewWith180InZone01 - Same as mgrsNewStyle except the 180
             degree longitude falls into Zone 01.
            mgrsOldWith180InZone01 - Same as mgrsOldStyle except the 180
             degree longitude falls into Zone 01.
           Valid conversion modes for UTM are:
            utmDefault - Default. No options.
            utmNorthSouth - Uses north/south latitude indicators instead of
             zone numbers. Non-standard. Default is recommended.
          numOfDigits - The number of digits to output for each of the
           numerical portions in the string. The default value for
           numOfDigits varies depending on conversionType.
          rounding - If true, then numeric portions of the string are
           rounded to the nearest whole magnitude as specified by
           numOfDigits. Otherwise, numeric portions of the string are
           truncated. The rounding parameter applies only to conversion
           types MGRS, USNG and GeoRef. The default value is true.
          addSpaces - If true, then spaces are added between components of
           the string. The addSpaces parameter applies only to conversion
           types MGRS, USNG and UTM. The default value for MGRS is false,
           while the default value for both USNG and UTM is true.
        """
        params = {
            "f": "json",
            "sr" : sr,
            "coordinates" : coordinates,
            "conversionType": conversionType
        }
        url = self._url + "/toGeoCoordinateString"
        if not conversionMode is None:
            params['conversionMode'] = conversionMode
        if isinstance(numOfDigits, int):
            params['numOfDigits'] = numOfDigits
        if isinstance(rounding, int):
            params['rounding'] = rounding
        if isinstance(addSpaces, bool):
            params['addSpaces'] = addSpaces
        return self._con.post(path=url, postdata=params, token=self._token)
    #----------------------------------------------------------------------
    def trim_extend(self,
                   sr,
                   polylines,
                   trimExtendTo,
                   extendHow=0):
        """
        The trim_extend operation is performed on a geometry service
        resource. This operation trims or extends each polyline specified
        in the input array, using the user-specified guide polylines. When
        trimming features, the part to the left of the oriented cutting
        line is preserved in the output, and the other part is discarded.
        An empty polyline is added to the output array if the corresponding
        input polyline is neither cut nor extended.

        Inputs:
         sr - The well-known ID of the spatial reference or a spatial
           reference json object.
         polylines - An array of polylines to be trimmed or extended.
         trimExtendTo - A polyline that is used as a guide for trimming or
          extending input polylines.
         extendHow - A flag that is used along with the trimExtend
          operation.
          0 - By default, an extension considers both ends of a path. The
           old ends remain, and new points are added to the extended ends.
           The new points have attributes that are extrapolated from
           adjacent existing segments.
          1 - If an extension is performed at an end, relocate the end
           point to the new position instead of leaving the old point and
           adding a new point at the new position.
          2 - If an extension is performed at an end, do not extrapolate
           the end-segment's attributes for the new point. Instead, make
           its attributes the same as the current end. Incompatible with
           esriNoAttributes.
          4 - If an extension is performed at an end, do not extrapolate
           the end-segment's attributes for the new point. Instead, make
           its attributes empty. Incompatible with esriKeepAttributes.
          8 - Do not extend the 'from' end of any path.
          16 - Do not extend the 'to' end of any path.
        """
        allowedHow = [0,1,2,4,8,16]
        if extendHow not in allowedHow:
            raise AttributeError("Invalid extend How value.")
        url = self._url + "/trimExtend"
        params = {
            "f" : "json",
            "sr" : sr,
            "polylines" : self.__geomToStringArray(geometries=polylines, returnType="list"),
            "extendHow": extendHow,
            "trimExtendTo" : trimExtendTo
        }
        results =  self._con.post(path=url, postdata=params, token=self._token)
        if 'error' in results:
            return results
        return self._process_results(results)
    #----------------------------------------------------------------------
    def union(self,
              sr,
              geometries):
        """
        The union operation is performed on a geometry service resource.
        This operation constructs the set-theoretic union of the geometries
        in the input array. All inputs must be of the same type.

        Inputs:
        sr - The well-known ID of the spatial reference or a spatial
         reference json object.
        geometries - The array of geometries to be unioned.
        """
        url = self._url + "/union"
        params = {
            "f" : "json",
            "sr" : sr,
            "geometries" : self.__geometryListToGeomTemplate(geometries=geometries)
        }
        results =  self._con.post(path=url, postdata=params, token=self._token)
        if 'error' in results:
            return results
        return self._process_results(results)


class _Tools(object):
    """
    Collection of GIS tools. This class holds references to the helper services and tools available
    in the GIS. This class is not created by users directly.
    An instance of this class, called 'tools', is available as a property of the GIS object.
    Users access the GIS tools, such as the geocoders through
    the gis.tools object
    """
    # spatial analysis tools, geoanalytics, rasteranalysis tools, etc through the gis.tools object
    def __init__(self, gis):
        self._gis = gis
        self._geocoders = None
        self._geometry = None
        self._analysis = None
        self._raster_analysis = None
        self._geoanalytics = None

    @property
    def geocoders(self):
        """the geocoders, if available and configured"""
        if self._geocoders is not None:
            return self._geocoders
        self._geocoders = []
        try:
            geocode_services = self._gis.properties['helperServices']['geocode']
            for geocode_service in geocode_services:
                try:
                    self._geocoders.append(Geocoder(geocode_service['url'], self._gis))
                except RuntimeError as re:
                    _log.warning('Unable to use Geocoder at ' + geocode_service['url'])
                    _log.warning(str(re))
        except KeyError:
            pass
        return self._geocoders

    @property
    def geometry(self):
        """the portal's geometry  tools, if available and configured"""
        if self._geometry is not None:
            return self._geometry
        try:
            svcurl = self._gis.properties['helperServices']['geometry']['url']
            self._geometry = _GeometryService(svcurl, self._gis)
            return self._geometry
        except KeyError:
            return None

    @property
    def rasteranalysis(self):
        """the portal's raster analysis tools, if available and configured"""
        if self._raster_analysis is not None:
            return self._raster_analysis
        try:
            try:
                svcurl = self._gis.properties['helperServices']['rasterAnalytics']['url']
            except:
                print("This GIS does not support raster analysis.")
                return None

            self._raster_analysis = _RasterAnalysisTools(svcurl, self._gis)
            return self._raster_analysis
        except KeyError:
            return None

    @property
    def geoanalytics(self):
        """the portal's bigdata analytics tools, if available and configured"""
        if self._geoanalytics is not None:
            return self._geoanalytics
        try:
            try:
                svcurl = self._gis.properties['helperServices']['geoanalytics']['url']
            except:
                print("This GIS does not support geoanalytics.")
                return None

            self._geoanalytics = _GeoanalyticsTools(svcurl, self._gis)
            return self._geoanalytics
        except KeyError:
            return None

    @property
    def featureanalysis(self):
        """the portal's spatial analysis tools, if available and configured"""
        if self._analysis is not None:
            return self._analysis
        try:
            try:
                svcurl = self._gis.properties['helperServices']['analysis']['url']
            except:
                if self._gis._con.token is None:
                    print("You need to be signed in to use spatial analysis.")
                else:
                    print("This GIS does not support spatial analysis.")
                return None

            self._analysis = _FeatureAnalysisTools(svcurl, self._gis)
            return self._analysis
        except KeyError:
            return None