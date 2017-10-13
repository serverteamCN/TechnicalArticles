from __future__ import print_function
import collections
import datetime
import inspect
import logging
import re
import sys
import time
import types
from types import MethodType

import arcgis.env
from arcgis._impl.common._mixins import PropertyMap
from arcgis._impl.common._utils import _date_handler
from arcgis.features import FeatureCollection, FeatureLayerCollection, FeatureSet
from arcgis.geoprocessing import LinearUnit, DataFile, RasterData

from arcgis.gis import Item, _GISResource, Layer
from arcgis.mapping import MapImageLayer

from ._types import LinearUnit, DataFile, RasterData

from ..features import FeatureSet
from ..mapping import MapImageLayer


def _import_code(code, name, verbose=False, add_to_sys_modules=False):
    """
    Import dynamically generated code as a module. code is the
    object containing the code (a string, a file handle or an
    actual compiled code object, same types as accepted by an
    exec statement). The name is the name to give to the module,
    and the final argument says wheter to add it to sys.modules
    or not. If it is added, a subsequent import statement using
    name will return this module. If it is not added to sys.modules
    import will try to load it in the normal fashion.

    import foo

    is equivalent to

    foofile = open("/path/to/foo.py")
    foo = importCode(foofile,"foo",1)

    Returns a newly generated module.
    """
    import sys,imp

    module = imp.new_module(name)

    if verbose:
        print(code)

    exec(code, module.__dict__)
    if add_to_sys_modules:
        sys.modules[name] = module

    return module

_log = logging.getLogger(__name__)

def _camelCase_to_underscore(name):
    """PEP8ify name"""
    if name[0].isdigit():
        name = "execute_" + name
    name = name.replace(" ", "_")
    if '_' in name:
        return name.lower()
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def _call_generator(fnname, spec):
    """Generate GP function based on spec
    """
    varnames = ()
    defaults = ()
    if len(spec)>0:
        varnames, defaults = zip(*spec)

    varnames = ('self', ) + varnames


    def call(self):
        """Method to invoke the Geoprocessing task"""
        #import sys
        kwargs = locals()
        kwargs.pop('self')
        self.__dict__.update(kwargs)

        # args, posargs = self.arguments()

        #print("My args: ")
        #for k, v in kwargs.items():
        #    print(k + " => " + str(v))

        return self._execute(kwargs)

    code = call.__code__
    new_code = types.CodeType(len(spec) + 1,
                              0,
                              len(spec) + 2,
                              code.co_stacksize,
                              code.co_flags,
                              code.co_code,
                              code.co_consts,
                              code.co_names,
                              varnames,
                              code.co_filename,
                              _camelCase_to_underscore(fnname),
                              code.co_firstlineno,
                              code.co_lnotab,
                              code.co_freevars,
                              code.co_cellvars)
    """
     * co_name gives the function name
     * co_argcount is the number of positional arguments (including
    arguments with default values)
     * co_nlocals is the number of local variables used by the function
    (including arguments)
     * co_varnames is a tuple containing the names of the local
    variables (starting with the argument names)
     * co_cellvars is a tuple containing the names of local variables
    that are referenced by nested functions
     * co_freevars is a tuple containing the names of free variables
     * co_code is a string representing the sequence of bytecode
    instructions
     * co_consts is a tuple containing the literals used by the bytecode
     * co_names is a tuple containing the names used by the bytecode
     * co_filename is the filename from which the code was compiled
     * co_firstlineno is the first line number of the function
     * co_lnotab is a string encoding the mapping from byte code offsets
    to line numbers (for details see the source code of the interpreter)
     * co_stacksize is the required stack size (including local
    variables)
     * co_flags is an integer encoding a number of flags for the
    interpreter.
    """
    return types.FunctionType(new_code,
                              {"__builtins__": __builtins__},
                              argdefs=defaults)


def _generate_fn(task, tbx):
    fnname = _camelCase_to_underscore(task)


    taskurl = tbx.url + "/" + task
    taskprops = tbx._con.post(taskurl, {"f": "json"}, token=tbx._token)

    # execution_type = taskprops['executionType']
    #
    # use_async = True
    # if  execution_type == 'esriExecutionTypeSynchronous':
    #     use_async = False

    uses_map_as_result = tbx.properties.resultMapServerName != ''

    helpstring, name_name, name_type, return_values, spec, name_param = _inspect_tool(taskprops, uses_map_as_result)

    src_code = 'def ' + fnname + '('
    num_spaces = len(src_code)

    if len(spec) > 0:
        param_name, param_dval = spec[0]
        param_type = name_type[param_name]

        src_code += _generate_param(name_param, param_dval, param_name, param_type)

        for param_name_dval in spec[1:]: # [ (param_name, param_dval) ]
            param_name, param_dval = param_name_dval
            param_type = name_type[param_name]
            src_code += ',\n' + ' '*num_spaces
            src_code += _generate_param(name_param, param_dval, param_name, param_type)

        src_code += ',\n' \

    src_code += ' '*num_spaces + 'gis=None) -> ' + name_type['return'].__name__ + ':\n'

    src_code += '\n\t"""\n\n' + helpstring + '\n\t"""\n'

    src_code += '\tkwargs = locals()\n\n'
    src_code += '\tparam_db = { '

    for param_name_dval in spec: # [ (param_name, param_dval) ]
        param_name, param_dval = param_name_dval
        param_type = name_type[param_name]
        gp_param_name = name_name[param_name]
        src_code += '\n\t           "' + param_name + '": (' + param_type.__name__ + ', "' + gp_param_name +'"),'

    # also add return params:
    for retval in return_values:
        src_code += '\n\t           "' + retval['name'] + '": (' + retval['type'].__name__ + ', "' + retval['display_name'] +'"),'

    src_code += '\n\t           }'

    src_code += '\n\treturn_values = ['
    for retval in return_values:
        src_code += '\n\t                 {"name":"' + retval['name'] + '", "display_name":"' + \
                                            retval['display_name'] + '", "type":' + retval['type'].__name__ + "},"
    src_code += '\n\t                ]\n\n'

    src_code += '\treturn _execute_gp_tool(gis, "' + task + '", kwargs, param_db, return_values, _use_async, _url)'

    src_code += '\n\n\n'
    return src_code


def _generate_param(name_param, param_dval, param_name, param_type):
    param = name_param[param_name]
    param_rqrd = param['parameterType']
    optional = False
    if (param_rqrd is not None) and param_rqrd == 'esriGPParameterTypeOptional':
        optional = True

    src_code = param_name + ':' + param_type.__name__
    # if optional:
    if param_dval is not None and param_dval != '':
        if param_type == str:
            src_code += '="""' + str(param_dval) + '"""'
        else:
            src_code += '=' + str(param_dval)
    else:
        src_code += '=None'
    return src_code


def _strip_html(text):
    return re.sub("&lt; */? *\w+ */?\ *&gt;", "", text)

def _inspect_tool(taskprops, map_as_result):
    # is map is a result, additional synthetic parameter is added
    spec = []       # [ (param_name, param_dval) ]
    name_type = {}  #
    name_name = {}  # map from camel_case to GPParameterName
    name_param = {}

    return_values = []

    # tools with output map service - add another output:
    if map_as_result:
        return_values.append({"name": "result_layer", "display_name": "Result Layer", "type": MapImageLayer})

    helpstring = ' \n\t\n'
    if 'docstring' in taskprops:
        helpstring += _strip_html(taskprops['docstring'])
    if 'description' in taskprops:
        helpstring += _strip_html(taskprops['description'])

    helpstring = helpstring + "\n\nParameters:"

    task_params = taskprops['parameters']
    for param in task_params:
        param_helpstring, param_name_mapping, param_name_type_mapping, param_spec, param_return_values, param_name_param = _process_parameter(param, map_as_result)
        helpstring += param_helpstring
        name_param.update(param_name_param)
        if param_spec is not None:
            spec.append(param_spec)

        name_name.update(param_name_mapping)
        name_type.update(param_name_type_mapping)

        if param_return_values is not None:
            return_values.append(param_return_values)

    # gis=None
    helpstring += '\n\n\tgis: Optional, the GIS on which this tool runs. If not specified, the active GIS is used.\n'

    if len(return_values) == 1:
        helpstring = helpstring + "\n\nReturns: " # + name_type['return_display_name'] + " (" + name_type['return'].__name__ + ")"
        for retval in return_values:
            helpstring = helpstring + '\n   ' + retval['name'] + ' - ' + retval['display_name'] \
                         + ' as a ' + retval['type'].__name__

    else:
        name_type['return'] = tuple  # for method spec, type hinting
        helpstring = helpstring + "\n\nReturns the following as a named tuple:"
        for retval in return_values:
            helpstring = helpstring + '\n   ' + retval['name'] + ' - ' + retval['display_name'] \
                         + ' as a ' + retval['type'].__name__

    helpstring = helpstring + "\n"

    if 'helpUrl' in taskprops:
        helpstring = helpstring + "\nSee " + taskprops['helpUrl'] + " for additional help."

    return helpstring, name_name, name_type, return_values, spec, name_param


def _process_parameter(param, map_as_result):

    gp_param_name = param['name']
    param_name = _camelCase_to_underscore(gp_param_name)
    param_name_mapping = {param_name : gp_param_name}

    name_param = { param_name : param }
    param_name_type_mapping = {}
    param_spec = None

    helpstring = ""

    #name_name[param_name] = gp_param_name
    param_return_values = None
    param_type = param['dataType']
    param_dval = param['defaultValue']
    param_drtn = param['direction']
    param_rqrd = param['parameterType']
    param_chcs = param.get('choiceList', None)
    py_param_type = get_py_param_type(param_type)
    if param_drtn == 'esriGPParameterDirectionInput':
        param_name_type_mapping[param_name] = py_param_type
        param_spec = (param_name, param_dval)

        helpstring += "\n\n   " + param_name + ": " + param['displayName'] + " (" + py_param_type.__name__ + ")."
        if param_rqrd == 'esriGPParameterTypeOptional':
            helpstring = helpstring + " Optional parameter. "
        #elif param_rqrd == 'esriGPParameterTypeRequired' and param_dval is None:
        else:
            helpstring = helpstring + " Required parameter. "

        if 'description' in param:
            helpstring = helpstring + ' ' + param['description']

        if param_chcs is not None and len(param_chcs) > 0:
            helpstring = helpstring + '\n      Choice list:' + str(param_chcs)

    elif param_drtn == 'esriGPParameterDirectionOutput':

        if map_as_result:  # 6.3.4.7 Map Images as Geoprocessing Results
            if py_param_type in [FeatureSet, RasterData]:
                py_param_type = dict  # map image

        param_name_type_mapping[param_name] = py_param_type
        param_name_type_mapping['return'] = py_param_type
        #param_name_type_mapping['return_name'] = param_name
        #param_name_type_mapping['return_display_name'] = param['displayName']

        param_return_values = {"name": param_name,
                              "display_name": param['displayName'],
                              "type": py_param_type}

    return helpstring, param_name_mapping, param_name_type_mapping, param_spec, param_return_values, name_param


def get_py_param_type(param_type):
    type_mapping = {
        'GPBoolean' : bool,
        'GPDouble': float,
        'GPLong': int,
        'GPString': str,
        'GPDate': datetime.datetime,
        'GPFeatureRecordSetLayer': FeatureSet,
        'GPRecordSet': FeatureSet,
        'GPLinearUnit': LinearUnit,
        'GPDataFile': DataFile,
        'GPRasterData': RasterData,
        'GPRasterLayer': RasterData,
        'GPRasterDataLayer': RasterData,
        'GPMultiValue' : list
    }
    return type_mapping.get(param_type, str)


def import_toolbox(url_or_item, gis=None, verbose=False):
    """
    Imports geoprocessing toolboxes as native Python modules.
    You can call the functions available in the imported module to invoke these tools.


        ================  ========================================================
        **Argument**      **Description**
        ----------------  --------------------------------------------------------
        url_or_item       location of toolbox, can be a geoprocessing server url
                          or Item of type: Geoprocessing Service
        ----------------  --------------------------------------------------------
        gis               optional GIS, the GIS used for running the tool.
                          arcgis.env.active_gis is used if not specified
        ----------------  --------------------------------------------------------
        verbose           optional bool, set to True to print the generated module
        ================  ========================================================

    Returns module with functions for the various tools in the toolbox

    """
    tbx = None
    url = url_or_item
    if isinstance(url_or_item, Item):
        tbx = Toolbox.fromitem(url_or_item)
        url = url_or_item.url
    else:
        url = url_or_item
        if url_or_item.endswith('/GPServer'):
            url = url_or_item
        else:
            idx = url_or_item.index('/GPServer')
            url = url_or_item[0:idx + len('/GPServer')]
        tbx = _AsyncResource(url, gis)

    src_code = """import logging as _logging
import arcgis
from datetime import datetime
from arcgis.features import FeatureSet
from arcgis.mapping import MapImageLayer
from arcgis.geoprocessing import DataFile, LinearUnit, RasterData
from arcgis.geoprocessing._support import _execute_gp_tool

_log = _logging.getLogger(__name__)
    """

    execution_type = tbx.properties.executionType

    use_async = True
    if execution_type == 'esriExecutionTypeSynchronous':
        use_async = False

    src_code += '\n_url = "' + url + '"'
    src_code += '\n_use_async = ' + str(use_async) + '\n\n'

    for task in tbx.properties.tasks:
        fn_src = _generate_fn(task, tbx)
        src_code += fn_src

    return _import_code(src_code, 'name', verbose)
    #print(src_code)


class _AsyncResource(_GISResource):
    def __init__(self, url, gis):
        super(_AsyncResource, self).__init__(url, gis)

    def _refresh(self):
        params = {"f": "json"}
        dictdata = self._con.get(path=self.url, params=params, token=self._con.token) # token=self._token)
        self.properties = PropertyMap(dictdata)

    def _analysis_job(self, task, params):
        """ Submits an Analysis job and returns the job URL for monitoring the job
            status in addition to the json response data for the submitted job."""

        # Unpack the Analysis job parameters as a dictionary and add token and
        # formatting parameters to the dictionary. The dictionary is used in the
        # HTTP POST request. Headers are also added as a dictionary to be included
        # with the POST.
        #
        # print("Submitting analysis job...")

        task_url = "{}/{}".format(self.url, task)
        submit_url = "{}/submitJob".format(task_url)

        params["f"] = "json"

        resp = self._con.post(submit_url, params, token=self._token)
        # print(resp)
        return task_url, resp

    def _analysis_job_status(self, task_url, job_info):
        """ Tracks the status of the submitted Analysis job."""

        if "jobId" in job_info:
            # Get the id of the Analysis job to track the status.
            #
            job_id = job_info.get("jobId")
            job_url = "{}/jobs/{}".format(task_url, job_id)
            params = {"f": "json"}
            job_response = self._con.post(job_url, params, token=self._token)

            # Query and report the Analysis job status.
            #
            num_messages = 0

            if "jobStatus" in job_response:
                while not job_response.get("jobStatus") == "esriJobSucceeded":
                    time.sleep(5)

                    job_response = self._con.post(job_url, params, token=self._token)
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
                                _log.warn(msg['description'])  # ,file = sys.stderr)
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

                        params = {"f": "json"}
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
            "layerDefinition": {
                "currentVersion": 10.11,
                "copyrightText": "",
                "defaultVisibility": True,
                "relationships": [

                ],
                "isDataVersioned": False,
                "supportsRollbackOnFailureParameter": True,
                "supportsStatistics": True,
                "supportsAdvancedQueries": True,
                "geometryType": "esriGeometryPoint",
                "minScale": 0,
                "maxScale": 0,
                "objectIdField": "OBJECTID",
                "templates": [

                ],
                "type": "Feature Layer",
                "displayField": "TITLE",
                "visibilityField": "VISIBLE",
                "name": "startDrawPoint",
                "hasAttachments": False,
                "typeIdField": "TYPEID",
                "capabilities": "Query",
                "allowGeometryUpdates": True,
                "htmlPopupType": "",
                "hasM": False,
                "hasZ": False,
                "globalIdField": "",
                "supportedQueryFormats": "JSON",
                "hasStaticData": False,
                "maxRecordCount": -1,
                "indexes": [

                ],
                "types": [

                ],
                "fields": [
                    {
                        "alias": "OBJECTID",
                        "name": "OBJECTID",
                        "type": "esriFieldTypeOID",
                        "editable": False
                    },
                    {
                        "alias": "Title",
                        "name": "TITLE",
                        "length": 50,
                        "type": "esriFieldTypeString",
                        "editable": True
                    },
                    {
                        "alias": "Visible",
                        "name": "VISIBLE",
                        "type": "esriFieldTypeInteger",
                        "editable": True
                    },
                    {
                        "alias": "Description",
                        "name": "DESCRIPTION",
                        "length": 1073741822,
                        "type": "esriFieldTypeString",
                        "editable": True
                    },
                    {
                        "alias": "Type ID",
                        "name": "TYPEID",
                        "type": "esriFieldTypeInteger",
                        "editable": True
                    }
                ]
            },
            "featureSet": {
                "features": [
                    {
                        "geometry": {
                            "x": 80.27032792000051,
                            "y": 13.085227147000467,
                            "spatialReference": {
                                "wkid": 4326,
                                "latestWkid": 4326
                            }
                        },
                        "attributes": {
                            "description": "blayer desc",
                            "title": "blayer",
                            "OBJECTID": 0,
                            "VISIBLE": 1
                        },
                        "symbol": {
                            "angle": 0,
                            "xoffset": 0,
                            "yoffset": 8.15625,
                            "type": "esriPMS",
                            "url": "https://cdn.arcgis.com/cdn/7674/js/jsapi/esri/dijit/images/Directions/greenPoint.png",
                            "imageData": "iVBORw0KGgoAAAANSUhEUgAAABUAAAAdCAYAAABFRCf7AAAAGXRFWHRTb2Z0d2FyZQBBZG9iZSBJbWFnZVJlYWR5ccllPAAAAyRpVFh0WE1MOmNvbS5hZG9iZS54bXAAAAAAADw/eHBhY2tldCBiZWdpbj0i77u/IiBpZD0iVzVNME1wQ2VoaUh6cmVTek5UY3prYzlkIj8+IDx4OnhtcG1ldGEgeG1sbnM6eD0iYWRvYmU6bnM6bWV0YS8iIHg6eG1wdGs9IkFkb2JlIFhNUCBDb3JlIDUuMC1jMDYxIDY0LjE0MDk0OSwgMjAxMC8xMi8wNy0xMDo1NzowMSAgICAgICAgIj4gPHJkZjpSREYgeG1sbnM6cmRmPSJodHRwOi8vd3d3LnczLm9yZy8xOTk5LzAyLzIyLXJkZi1zeW50YXgtbnMjIj4gPHJkZjpEZXNjcmlwdGlvbiByZGY6YWJvdXQ9IiIgeG1sbnM6eG1wPSJodHRwOi8vbnMuYWRvYmUuY29tL3hhcC8xLjAvIiB4bWxuczp4bXBNTT0iaHR0cDovL25zLmFkb2JlLmNvbS94YXAvMS4wL21tLyIgeG1sbnM6c3RSZWY9Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC9zVHlwZS9SZXNvdXJjZVJlZiMiIHhtcDpDcmVhdG9yVG9vbD0iQWRvYmUgUGhvdG9zaG9wIENTNS4xIE1hY2ludG9zaCIgeG1wTU06SW5zdGFuY2VJRD0ieG1wLmlpZDo4OTI1MkU2ODE0QzUxMUUyQURFMUNDNThGMTA3MjkzMSIgeG1wTU06RG9jdW1lbnRJRD0ieG1wLmRpZDo4OTI1MkU2OTE0QzUxMUUyQURFMUNDNThGMTA3MjkzMSI+IDx4bXBNTTpEZXJpdmVkRnJvbSBzdFJlZjppbnN0YW5jZUlEPSJ4bXAuaWlkOjg5MjUyRTY2MTRDNTExRTJBREUxQ0M1OEYxMDcyOTMxIiBzdFJlZjpkb2N1bWVudElEPSJ4bXAuZGlkOjg5MjUyRTY3MTRDNTExRTJBREUxQ0M1OEYxMDcyOTMxIi8+IDwvcmRmOkRlc2NyaXB0aW9uPiA8L3JkZjpSREY+IDwveDp4bXBtZXRhPiA8P3hwYWNrZXQgZW5kPSJyIj8+iVNkdQAABJlJREFUeNp0VltvG0UUnpkdr72261CnCQWEIA9FqOKlqooARUKCtAUhoA+VoBVRhfgFXKSKJ97goRL8ARCIclGgL0VUkBBAoBaVoggEQQVSAhFS06SJje3Y3t25cc7srL3YjddHs3N85pvvfOfMyJRs83n8o+P7POI9yQibooTeBa68ISbSRv+hifpCGHX2s6dnfrrRWjroOPzB0T0+zZ0q8uDRSrniF/MB8X2fADhR8IRRRDphh7Q6rbgtOucU0Sdnj59Z2hb00PtHD+Zp/p2x6uitO4o7iLYP8DMafjVE2wXUboALm50W2ahtXO3q8MTX02fnh0Affu/IkSAXnL55dLzMPU6kURZMIZQhFtRk2VBKcpQTIQVZ21hrdUX4zDcnPv2kBzr59mP3BLnChfGx8YrHPKIAELSzMPhQk+ydzpOvIYwywjFeK7K+vt6IlZw8/+y5RZ4gm9eCUrGCmkUyBkCV0Sd5UlBtTLIhRWQE9ixwsVwe6dY3X4WwJ+j9bx7a7/v5i6O7qlxisFZJAvBF7Rjty56CWlmszilj6BNgXd+syTCO7uNK62nuezyUkWWASTPHDtOjbgOHkJTOsbXAyJhIC+rlODdROM211gcQKBJxoh+EKAs4AGqybHVfBvdICNIU/IDHYbcJiS6le4wwbW1B9UDXJcg9QBxtbglh1BlAJzjoUxIGQZFRwtAypgnjtH0spDG9MWVs34xrN5uBLnEoTKQUgDLgZ6hliLunBaIDhy4LYhyotptZlphGyLUhfyspxxj3AIpaVqikdgyzoGn7p0xNj71rNamweCscWC0qoQ8YRm3K2OgpeFoc+j9FSUYKB+4OgxIK4RcZUJ6RsUgqCrShxWzza9035aw/lzYGY5P4xFSMR5vMcFpm87opL4HjXsr76dLhC2xYhgx3I0BfoS7RCp+3K/e8vn+Ke2zWK+cYofQG9yMlw1eK1aAni9oSWil9eOmFhXkPnbXZ1eXqwVsirfQU9Vynm75lymLbxvpSP4yqI4iR5uWlFxdOI56Xbro5t3qhOrW7ZmL1EOFwp7k6pRXuWaZgBmuwJSIl1fNXXvrxjRTLy2ZTm1v9YeTBXedNbCYZZ1U4pdt+NGiomuKKEvKp5ZM/f5z9zctc1vju1b9cv5q/M/icBd4+KNztlnGWKfYjAMqm+K7zZ/PYP6d+X3TrafbmR8N71QcrOPMLd5RGdj838WFup393orNLWRki6vFv197661i40m6AKwYLneG79BzDPNhNYFWwnfguGyKgPl32bwseoTnKekVpS9n49vorWwv1JsSVwAJHCHcW2Agsk3rBBZXBihhcn11biTfDixpPik1bEZyj34EVXXzJrUccWwrbZo5+B6ztRpvO1kLjjO5qW3YccZ5JeTAecQxqqV0Q6hM5KVIrNL5a/77yQPUyLbK9qiMv49zFhW6MMnPE0dwxlQ48ckXDNHJOq0C2xByreHtxhPk1sK4DEI5dut7+QWCZCyj9MXKLWmD/gl1Xtfhd6F2CI86dv+XiIrdOpeeCDd0VyW7KGbLptn9p/mrgNsIxwzKN0QO3IvlPgAEA3AQhIZtaN54AAAAASUVORK5CYII=",
                            "contentType": "image/png",
                            "width": 15.75,
                            "height": 21.75
                        }
                    }
                ],
                "geometryType": "esriGeometryPoint"
            },
            "nextObjectId": 1
        }

        input_layer_url = ""
        if isinstance(input_layer, Item):
            if input_layer.type.lower() == 'feature service':
                input_param = {"url": input_layer.layers[0].url}
            elif input_layer.type.lower() == 'feature collection':
                fcdict = input_layer.get_data()
                fc = FeatureCollection(fcdict['layers'][0])
                input_param = fc.layer
            else:
                raise TypeError("item type must be feature service or feature collection")

        elif isinstance(input_layer, FeatureLayerCollection):
            input_layer_url = input_layer.layers[0].url  # ["url"]
            input_param = {"url": input_layer_url}
        elif isinstance(input_layer, FeatureCollection):
            input_param = input_layer.properties
        elif isinstance(input_layer, Layer):
            input_layer_url = input_layer.url
            input_param = {"url": input_layer_url}
        elif isinstance(input_layer, tuple):  # geocoding location, convert to point featureset
            input_param = point_fs
            input_param["featureSet"]["features"][0]["geometry"]["x"] = input_layer[1]
            input_param["featureSet"]["features"][0]["geometry"]["y"] = input_layer[0]
        elif isinstance(input_layer, dict):  # could add support for geometry one day using geometry -> featureset
            input_param = input_layer
            """
            res = gis.analysis.trace_downstream({"layerDefinition":
                {
                    "geometryType":"esriGeometryPoint",
                    "fields":[{"alias":"OBJECTID","name":"OBJECTID","type":"esriFieldTypeOID","editable":False},
                              {"alias":"Title","name":"TITLE","length":50,"type":"esriFieldTypeString","editable":True},
                              {"alias":"Visible","name":"VISIBLE","type":"esriFieldTypeInteger","editable":True},
                              {"alias":"Description","name":"DESCRIPTION","length":1073741822,"type":"esriFieldTypeString","editable":True},
                              {"alias":"Type ID","name":"TYPEID","type":"esriFieldTypeInteger","editable":True}]
                },
                "featureSet":{
                    "features":[
                        {
                            "geometry":{
                                "x":8913583.679975435,
                                "y":1460497.641278398,
                                "spatialReference":{"wkid":102100,"latestWkid":3857}
                            },
                            "attributes":{"description":"blayer desc","title":"blayer","OBJECTID":0,"VISIBLE":1},

                        }
                    ],
                    "geometryType":"esriGeometryPoint"
                },
                "nextObjectId":1
            })
            """
        elif isinstance(input_layer, str):
            input_layer_url = input_layer
            input_param = {"url": input_layer_url}
        else:
            raise Exception(
                "Invalid format of input layer. url string, feature service Item, feature service instance or dict supported")

        return input_param

    def _raster_input(self, input_raster):
        if isinstance(input_raster, Item):
            if input_raster.type.lower() == 'image service':
                input_param = {"itemId": input_raster.itemid}
            else:
                raise TypeError("item type must be image service")
        elif isinstance(input_raster, str):
            input_param = {"url": input_raster}
        elif isinstance(input_raster, dict):
            input_param = input_raster
        else:
            raise Exception("Invalid format of input raster. image service Item or image service url, cloud raster uri "
                            "or shared data path supported")

        return input_param


class Toolbox(_AsyncResource):
    "A collection of geoprocessing tools."

    def __init__(self, url, gis=None):
        """
        Constructs a Geoprocessing toolbox
        """
        super(Toolbox, self).__init__(url, gis)
        try:
            from .._impl._server._service._adminfactory import AdminServiceGen
            self.service = AdminServiceGen(service=self, gis=gis)
        except: pass

        self._taskurls = {}
        self._param_names = {} # mapping from fn to name-map (camel_case (PEP8ified) parameter name to GP_Param_Name)
        self._method_params = {}
        self._return_values = {}

        for task in self.properties.tasks:
            fnname = _camelCase_to_underscore(task)
            # print("Function: " + fnname)

            taskurl = self.url + "/" + task

            self._taskurls[fnname] = taskurl + "/execute"

            taskprops = self._con.post(taskurl, {"f":"json"}, token=self._token)
            execution_type = taskprops['executionType']
            task_params = taskprops['parameters']

            helpstring = '\n'
            if 'docstring' in taskprops:
                docstring = taskprops['docstring']
                text_docstring = re.sub("&lt; */? *\w+ */?\ *&gt;", "", docstring)
                helpstring = helpstring + ". " + text_docstring

            if 'description' in taskprops:
                description = taskprops['description']
                text_description = re.sub("&lt; */? *\w+ */?\ *&gt;", "", description)
                helpstring += ' \n \n' + text_description

            helpstring = helpstring + "\n\nParameters:"

            spec = []
            name_type = {}
            name_name = {} # map from camel_case to GPParameterName
            name_type[fnname] = task
            return_values = []

            # tools with output map service - add another output:
            if self.properties.resultMapServerName != '':
                return_values.append({"name": "result_layer", "display_name": "Result Layer", "type": MapImageLayer})

            for param in task_params:

                gp_param_name = param['name']

                param_name = _camelCase_to_underscore(gp_param_name)

                name_name[param_name] = gp_param_name

                param_type = param['dataType']
                param_dval = param['defaultValue']
                param_drtn = param['direction']

                param_rqrd = param['parameterType']

                param_choices = param.get('choiceList', None)

                py_param_type_ = param_type
                if param_type == 'GPBoolean':
                    py_param_type_ = bool
                elif param_type == 'GPDouble':
                    py_param_type_ = float
                elif param_type == 'GPLong':
                    py_param_type_ = int
                elif param_type == 'GPString':
                    py_param_type_ = str
                elif param_type == 'GPDate':
                    py_param_type_ = datetime.date
                elif param_type == 'GPFeatureRecordSetLayer':
                    py_param_type_ = FeatureSet
                elif param_type == 'GPRecordSet':
                    py_param_type_ = FeatureSet
                elif param_type == 'GPLinearUnit':
                    py_param_type_ = LinearUnit
                elif param_type == 'GPDataFile':
                    py_param_type_ = DataFile
                elif param_type in ['GPRasterData', 'GPRasterLayer', 'GPRasterDataLayer']:
                    py_param_type_ = RasterData
                elif param_type.startswith('GPMultiValue'):
                    py_param_type_ = list
                else:
                    py_param_type_ = str

                if param_drtn == 'esriGPParameterDirectionInput':
                    name_type[param_name] = py_param_type_
                    # print("\n   " + param_name + " : " + str(py_param_type_))
                    #if param_dval is not None and param_dval != '':
                    #    print(" = " + str(param_dval))
                    #if param_rqrd is not None and param_rqrd == 'esriGPParameterTypeOptional':
                    #    print(" = None")
                    param_spec = ( param_name , param_dval )
                    spec.append(param_spec)

                    helpstring = helpstring + "\n\n   " + param_name + ": " + param['displayName']  + " (" + py_param_type_.__name__ + ")."
                    if param_rqrd == 'esriGPParameterTypeOptional':
                        helpstring = helpstring + " Optional parameter. "
                    elif param_rqrd == 'esriGPParameterTypeRequired' and param_dval is None:
                        helpstring = helpstring + " Required parameter. "

                    if 'description' in param:
                        helpstring = helpstring + ' ' + param['description']

                    if param_choices is not None and len(param_choices) > 0:
                        helpstring = helpstring + '\n      Choice list:' + str(param_choices)

                elif param_drtn == 'esriGPParameterDirectionOutput':

                    if self.properties.resultMapServerName != '': # 6.3.4.7 Map Images as Geoprocessing Results
                        if py_param_type_ in [FeatureSet, RasterData]:
                            py_param_type_ = dict # map image

                    name_type[param_name] = py_param_type_
                    name_type['return'] = py_param_type_
                    name_type['return_name'] = param_name
                    name_type['return_display_name'] = param['displayName']

                    return_values.append({"name": param_name,
                                          "display_name": param['displayName'],
                                          "type": py_param_type_})



            if len(return_values) == 1:
                helpstring = helpstring + "\n\nReturns: " + name_type['return_display_name'] + " (" + name_type['return'].__name__ + ")"
            else:
                name_type['return'] = tuple # for method spec, type hinting
                helpstring = helpstring + "\n\nReturns the following as a named tuple:"
                for retval in return_values:
                    helpstring = helpstring + '\n   ' + retval['name'] + ' - ' + retval['display_name'] + ' as a ' + retval['type'].__name__

            helpstring = helpstring + "\n"

            if 'helpUrl' in taskprops:
                helpstring = helpstring + "\nSee " + taskprops['helpUrl'] + " for additional help."

            generatedfn = _call_generator(task, spec)
            generatedfn.__annotations__ = name_type
            generatedfn.__doc__ = helpstring

            setattr(self, fnname, types.MethodType(generatedfn, self))

            self._method_params[fnname] = name_type
            self._param_names[fnname] = name_name
            self._return_values[fnname] = return_values

        # http://www.arcgis.com/home/item.html?id=383c2039b89d43baa0010c3bf243b144
        # http://sampleserver1.arcgisonline.com/ArcGIS/rest/Services/Specialty/ESRI_Currents_World/GPServer

    def __str__(self):
         return '<Toolbox url:' + self.url + '>'

    def _execute(self, params):
        caller_fnname = inspect.stack()[1][3]

        # print("Will call " + url +  " with these parameters:")

        name_type = self._method_params[caller_fnname]
        name_name = self._param_names[caller_fnname]
        return_values = self._return_values[caller_fnname]

        task_name = name_type[caller_fnname]
        url = self.url + "/" + task_name + "/execute"

        #---------------------in---------------------#

        for key, value in params.items():
            # print(k + " = " + str(v))
            if key in name_type:
                py_type = name_type[key]

                if py_type in [FeatureSet, LinearUnit, DataFile, RasterData]:
                    if type(value) in [FeatureSet, LinearUnit, DataFile, RasterData]:
                        params[key] = value.to_dict()
                    elif type(value) == str:
                        try:
                            klass = py_type # type[value]
                            params[key] = klass.from_str(value)
                        except:
                            pass
                elif py_type == datetime.datetime:
                    params[key] = _date_handler(value)
        #--------------------------------------------#

        params.update({ "f" : "json" })

        gp_params = {}

        for param_name, param_value in params.items():
            gp_param_name = name_name.get(param_name, param_name)
            gp_params[gp_param_name] = param_value

        # copy environment variables if set
        if 'env:outSR' not in params and arcgis.env.out_spatial_reference is not None:
            gp_params['env:outSR'] = arcgis.env.out_spatial_reference

        if 'env:processSR' not in params and arcgis.env.process_spatial_reference is not None:
            gp_params['env:processSR'] = arcgis.env.process_spatial_reference

        if 'returnZ' not in params and arcgis.env.return_z is not False:
            gp_params['returnZ'] = True

        if 'returnM' not in params and arcgis.env.return_m is not False:
            gp_params['returnM'] = True

        resp = None

        if self.properties.executionType == 'esriExecutionTypeSynchronous':
            resp = self._con.post(url, gp_params, token=self._token)

            output_dict = {}

            for result in resp['results']:
                retParamName = result['paramName']
                ret_param_name = _camelCase_to_underscore(retParamName)
                ret_type = name_type[ret_param_name]
                ret_val = None
                if ret_type in [FeatureSet, LinearUnit, DataFile, RasterData]:
                    jsondict = result['value']
                    if 'mapImage' in jsondict: # http://resources.esri.com/help/9.3/arcgisserver/apis/rest/gpresult.html#mapimage
                        ret_val = jsondict
                    else:
                        result_obj = ret_type.from_dict(jsondict)
                        result_obj._con = self._con
                        result_obj._token = self._token
                        ret_val = result_obj
                else:
                    ret_val = result['value']

                output_dict[ret_param_name] = ret_val

            num_returns = len(resp['results'])
            if num_returns == 1:
                return output_dict[name_type['return_name']]
            else:
                ret_names = []
                for return_value in return_values:
                    ret_names.append(return_value['name'])

                NamedTuple = collections.namedtuple('ToolOutput', ret_names)
                tool_output = NamedTuple(**output_dict) #TODO: preserve ordering
                return tool_output

        else:
            task_url = "{}/{}".format(self.url, task_name)
            submit_url = "{}/submitJob".format(task_url)

            # arams["f"] = "json"

            job_info = self._con.post(submit_url, gp_params, token=self._token)

            job_info = super()._analysis_job_status(task_url, job_info)
            resp = super()._analysis_job_results(task_url, job_info)
            # print('***'+str(resp))

            output_dict = {}
            for retParamName in resp.keys():
                ret_param_name = _camelCase_to_underscore(retParamName)
                ret_type = name_type[ret_param_name]
                ret_val = None
                if ret_type in [FeatureSet, LinearUnit, DataFile, RasterData]:
                    jsondict = resp[retParamName]
                    if 'mapImage' in jsondict:
                        ret_val = jsondict
                    else:
                        result = ret_type.from_dict(jsondict)
                        result._con = self._con
                        result._token = self._token
                        ret_val =  result
                else:
                    ret_val = resp[retParamName]

                output_dict[ret_param_name] = ret_val

            # tools with output map service - add another output:
            result_layer = self.properties.resultMapServerName
            if result_layer != '':
                job_id = job_info.get("jobId")
                result_layer_url = self.url.replace('/GPServer', '/MapServer') + '/jobs/' + job_id

                output_dict['result_layer'] = MapImageLayer(result_layer_url, self._gis)

            num_returns = len(resp)
            if num_returns == 1:
                return output_dict[name_type['return_name']] # *** output_dict[return_values[0]['name']]
            else:
                ret_names = []
                for return_value in return_values:
                    ret_names.append(return_value['name'])

                NamedTuple = collections.namedtuple('ToolOutput', ret_names)
                tool_output = NamedTuple(**output_dict) #TODO: preserve ordering
                return tool_output
                #return collections.namedtuple('GeoprocessingResults', output_dict.keys())(**output_dict)



    # def execute(self, task, input,
    #             outSR=None,
    #             processSR=None,
    #             returnZ=False,
    #             returnM=False):
    #
    #     # http://sampleserver1.arcgisonline.com/ArcGIS/rest/services/Specialty/ESRI_Currents_World/GPServer/MessageInABottle/execute? Input_Point={"features":[{"geometry":{"x":0,"y":0}}]}& Days=50
    #     url = self.url + "/" + task + "/execute"
    #     params = {
    #         "f" : "json",
    #     }
    #
    #     if outSR is not None:
    #         params['outSR'] = outSR
    #     if processSR is not None:
    #         params['processSR'] = processSR
    #     if returnZ:
    #         params['returnZ'] = "true"
    #     if returnM:
    #         params['returnM'] = "true"
    #
    #     for k, v in input.items():
    #         params[k] = v
    #
    #     resp = self.item._portal.con.post(url, params)
    #     return resp

    @property
    def tools(self):
        """List of tools in this toolbox"""
        return [x for x, y in self.__dict__.items() if type(y) == MethodType]