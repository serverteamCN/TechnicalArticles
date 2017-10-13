from __future__ import print_function
import datetime

import inspect
import logging
import sys
import time
import datetime
import collections

import arcgis
from arcgis.gis import GIS
from arcgis.features import FeatureSet, FeatureCollection
from arcgis.mapping import MapImageLayer
from arcgis.geoprocessing import DataFile, LinearUnit, RasterData
from arcgis.geoprocessing._tool import _camelCase_to_underscore
from arcgis._impl.common._utils import _date_handler

_log = logging.getLogger(__name__)


def _layer_input(input_layer):
    input_param = input_layer

    input_layer_url = ""
    if isinstance(input_layer, arcgis.gis.Item):
        if 'layers' in input_layer:
            input_param = input_layer.layers[0]._lyr_dict
        else:
            raise TypeError("No layers in input layer Item")

    elif isinstance(input_layer, arcgis.features.FeatureLayerCollection):
        input_param = input_layer.layers[0]._lyr_dict

    elif isinstance(input_layer, arcgis.features.FeatureCollection):
        input_param = input_layer.properties

    elif isinstance(input_layer, arcgis.gis.Layer):
        input_param = input_layer._lyr_dict

    elif isinstance(input_layer, dict):
        input_param = input_layer

    elif isinstance(input_layer, str):
        input_param = {"url": input_layer}

    else:
        raise Exception("Invalid format of input layer. url string, layer Item, layer instance or dict supported")

    return input_param

def _feature_input(input_layer):
    
    input_param = input_layer
    
    input_layer_url = ""
    if isinstance(input_layer, arcgis.gis.Item):
        if input_layer.type.lower() == 'feature service':
            input_param =  input_layer.layers[0]._lyr_dict
        elif input_layer.type.lower() == 'big data file share':
            input_param =  input_layer.layers[0]._lyr_dict
        elif input_layer.type.lower() == 'feature collection':
            fcdict = input_layer.get_data()
            fc = FeatureCollection(fcdict['layers'][0])
            input_param =  fc.layer
        else:
            raise TypeError("item type must be feature service or feature collection")

    elif isinstance(input_layer, arcgis.features.FeatureLayerCollection):
        input_param =  input_layer.layers[0]._lyr_dict

    elif isinstance(input_layer, arcgis.features.FeatureCollection):
        input_param =  input_layer.properties

    elif isinstance(input_layer, arcgis.gis.Layer):
        input_param = input_layer._lyr_dict

    elif isinstance(input_layer, dict):
        input_param =  input_layer

    elif isinstance(input_layer, str):
        input_param =  {"url": input_layer }

    else:
        raise Exception("Invalid format of input layer. url string, feature service Item, feature service instance or dict supported")

    return input_param


def _analysis_job(gptool, task, params):
    """ Submits an Analysis job and returns the job URL for monitoring the job
        status in addition to the json response data for the submitted job."""

    # Unpack the Analysis job parameters as a dictionary and add token and
    # formatting parameters to the dictionary. The dictionary is used in the
    # HTTP POST request. Headers are also added as a dictionary to be included
    # with the POST.
    #
    # print("Submitting analysis job...")

    task_url = "{}/{}".format(gptool.url, task)
    submit_url = "{}/submitJob".format(task_url)

    params["f"] = "json"

    resp = gptool._con.post(submit_url, params, token=gptool._token)
    # print(resp)
    return task_url, resp

def _analysis_job_status(gptool, task_url, job_info):
    """ Tracks the status of the submitted Analysis job."""

    if "jobId" in job_info:
        # Get the id of the Analysis job to track the status.
        #
        job_id = job_info.get("jobId")
        job_url = "{}/jobs/{}".format(task_url, job_id)
        params = {"f": "json"}
        job_response = gptool._con.post(job_url, params, token=gptool._token)

        # Query and report the Analysis job status.
        #
        num_messages = 0
        if "jobStatus" in job_response:
            while not job_response.get("jobStatus") == "esriJobSucceeded":
                time.sleep(1)

                job_response = gptool._con.post(job_url, params, token=gptool._token)
                # print(job_response)
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


def _analysis_job_results(gptool, task_url, job_info):
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

                    params = {"f": "json"}
                    param_result = gptool._con.post(result_url, params, token=gptool._token)

                    job_value = param_result.get("value")
                    result_values[key] = job_value
            return result_values
        else:
            raise Exception("Unable to get analysis job results.")
    else:
        raise Exception("Unable to get analysis job results.")


def _execute_gp_tool(gis, task_name, params, param_db, return_values, use_async, url, webtool=False):
    if gis is None:
        gis = arcgis.env.active_gis

    gp_params = {"f": "json"}

    # ---------------------in---------------------#
    for param_name, param_value in params.items():
        #print(param_name + " = " + str(param_value))
        if param_name in param_db:
            py_type, gp_param_name = param_db[param_name]
            if param_value is None:
                param_value = ''
            gp_params[gp_param_name] = param_value
            if py_type == FeatureSet:
                if webtool:
                    gp_params[gp_param_name] = _layer_input(param_value)
                    
                else:
                    if type(param_value) == FeatureSet:
                        gp_params[gp_param_name] = param_value.to_dict()

                    elif type(param_value) == str:

                        try:
                            klass = py_type
                            gp_params[gp_param_name] = klass.from_str(param_value)

                        except:
                            pass

            
            elif py_type in [LinearUnit, DataFile, RasterData]:
                if type(param_value) in [LinearUnit, DataFile, RasterData]:
                    gp_params[gp_param_name] = param_value.to_dict()

                elif type(param_value) == str:

                    try:
                        klass = py_type
                        gp_params[gp_param_name] = klass.from_str(param_value)

                    except:
                        pass

                elif isinstance(param_value, arcgis.gis.Layer):
                    gp_params[gp_param_name] = param_value._lyr_dict

            elif py_type == datetime.datetime:
                gp_params[gp_param_name] = _date_handler(param_value)
    # --------------------------------------------#

    _set_env_params(gp_params, params)

    # for param_name, param_value in gp_params.items():
    #     print(param_name + " = " + str(param_value))

    gptool = arcgis.gis._GISResource(url, gis)

    if use_async:
        task_url = "{}/{}".format(url, task_name)
        submit_url = "{}/submitJob".format(task_url)

        job_info = gptool._con.post(submit_url, gp_params, token=gptool._token)
        job_info = _analysis_job_status(gptool, task_url, job_info)
        resp = _analysis_job_results(gptool, task_url, job_info)

        # ---------------------async-out---------------------#
        output_dict = {}
        for retParamName in resp.keys():
            output_val = resp[retParamName]
            try:
                ret_param_name, ret_val = _get_output_value(gptool, output_val, param_db, retParamName)
                output_dict[ret_param_name] = ret_val
            except KeyError:
                pass # cannot handle unexpected output as return tuple will change

        # tools with output map service - add another output:
        # result_layer = '' #***self.properties.resultMapServerName
        if gptool.properties.resultMapServerName != '':
            job_id = job_info.get("jobId")
            result_layer_url = url.replace('/GPServer', '/MapServer') + '/jobs/' + job_id

            output_dict['result_layer'] = MapImageLayer(result_layer_url, gptool._gis)

        num_returns = len(resp)
        return _return_output(num_returns, output_dict, return_values)

    else: # synchronous
        exec_url = url + "/" + task_name + "/execute"
        resp = gptool._con.post(exec_url, gp_params, token=gptool._token)

        output_dict = {}

        for result in resp['results']:
            retParamName = result['paramName']

            output_val = result['value']
            try:
                ret_param_name, ret_val = _get_output_value(gptool, output_val, param_db, retParamName)
                output_dict[ret_param_name] = ret_val
            except KeyError:
                pass  # cannot handle unexpected output as return tuple will change

        num_returns = len(resp['results'])
        return _return_output(num_returns, output_dict, return_values)


def _set_env_params(gp_params, params):
    # copy environment variables if set
    if 'env:outSR' not in params and arcgis.env.out_spatial_reference is not None:
        gp_params['env:outSR'] = arcgis.env.out_spatial_reference
    if 'env:processSR' not in params and arcgis.env.process_spatial_reference is not None:
        gp_params['env:processSR'] = arcgis.env.process_spatial_reference
    if 'returnZ' not in params and arcgis.env.return_z is not False:
        gp_params['returnZ'] = True
    if 'returnM' not in params and arcgis.env.return_m is not False:
        gp_params['returnM'] = True


def _return_output(num_returns, output_dict, return_values):
    if num_returns == 1:
        return output_dict[return_values[0]['name']]
    else:
        ret_names = []
        for return_value in return_values:
            ret_names.append(return_value['name'])
        # ret_names = output_dict.keys() # CANT USE - the order matters
        NamedTuple = collections.namedtuple('ToolOutput', ret_names)
        tool_output = NamedTuple(**output_dict)
        return tool_output


def _get_output_value(gptool, output_val, param_db, retParamName):
    ret_param_name = _camelCase_to_underscore(retParamName)


    ret_type, _ = param_db[ret_param_name]

    ret_val = None
    if ret_type in [FeatureSet, LinearUnit, DataFile, RasterData]:
        jsondict = output_val
        if 'mapImage' in jsondict:  # http://resources.esri.com/help/9.3/arcgisserver/apis/rest/gpresult.html#mapimage
            ret_val = jsondict
        elif ret_type == FeatureSet and 'url' in jsondict:
            ret_val = arcgis.features.FeatureLayer(jsondict['url'], gptool._gis)
        else:
            result = ret_type.from_dict(jsondict)
            result._con = gptool._con
            result._token = gptool._token
            ret_val = result
    else:
        ret_val = output_val
    return ret_param_name, ret_val
