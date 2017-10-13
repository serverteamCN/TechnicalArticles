"""
These functions help you use elevation analysis
"""

import logging as _logging
import arcgis
from datetime import datetime
from arcgis.features import FeatureSet
from arcgis.mapping import MapImageLayer
from arcgis.geoprocessing import DataFile, LinearUnit, RasterData
from arcgis.geoprocessing._support import _execute_gp_tool

_log = _logging.getLogger(__name__)

_use_async = True


def profile(input_line_features: FeatureSet = {'exceededTransferLimit': False,
                                               'spatialReference': {'latestWkid': 3857, 'wkid': 102100},
                                               'geometryType': 'esriGeometryPolyline',
                                               'fields': [{'name': 'OID', 'type': 'esriFieldTypeOID', 'alias': 'OID'},
                                                          {'name': 'Shape_Length', 'type': 'esriFieldTypeDouble',
                                                           'alias': 'Shape_Length'}], 'displayFieldName': '',
                                               'features': []},
            profile_id_field: str = None,
            dem_resolution: str = None,
            maximum_sample_distance: float = None,
            maximum_sample_distance_units: str = """Meters""",
            gis=None) -> FeatureSet:
    """


Returns elevation profiles for the input line features.

Parameters:

   input_line_features: Input Line Features (FeatureSet). Required parameter.  The line features that will be profiled over the surface inputs.

   profile_id_field: Profile ID Field (str). Optional parameter.  A unique identifier to tie profiles to their corresponding input line features.

   dem_resolution: DEM Resolution (str). Optional parameter.  The approximate spatial resolution (cell size) of the source elevation data used for the calculation. The default is 90m.The resolution keyword is an approximation of the spatial resolution of the digital elevation model. Many elevation sources are distributed with units of arc seconds, the keyword is an approximation in meters for easier understanding.FINEST — The finest units available for the extent are used.10m — the elevation source resolution is 1/3 arc second, or approximately 10 meters.30m — the elevation source resolution is 1 arc second, or approximately 30 meters.90m — the elevation source resolution is 3 arc second, or approximately 90 meters.1000m — the elevation source resolution is 30 arc seconds, or approximately 1000 meters.
      Choice list:[' ', 'FINEST', '1000m', '10m', '30m', '90m']

   maximum_sample_distance: Maximum Sample Distance (float). Optional parameter.  The maximum sample distance along the line to sample elevation values.

   maximum_sample_distance_units: Maximum Sample Distance Units (str). Optional parameter.  The units for the Maximum Sample Distance parameter.The default is meters.Meters — The units are meters. This is the default.Kilometers — The units are kilometers.Feet — The units are feet.Yards — The units are yards.Miles — The units are miles.
      Choice list:['Meters', 'Kilometers', 'Feet', 'Yards', 'Miles']

gis: Optional, the GIS on which this tool runs. If not specified, the active GIS is used.


Returns:
   output_profile - Output Profile as a FeatureSet

See http://ec2-35-161-157-22.us-west-2.compute.amazonaws.com:6080/arcgis/rest/directories/arcgisoutput/Tools/Elevation_GPServer/Tools_Elevation/Profile.htm for additional help.
    """
    kwargs = locals()

    param_db = {
        "input_line_features": (FeatureSet, "InputLineFeatures"),
        "profile_id_field": (str, "ProfileIDField"),
        "dem_resolution": (str, "DEMResolution"),
        "maximum_sample_distance": (float, "MaximumSampleDistance"),
        "maximum_sample_distance_units": (str, "MaximumSampleDistanceUnits"),
        "output_profile": (FeatureSet, "Output Profile"),
    }
    return_values = [
        {"name": "output_profile", "display_name": "Output Profile", "type": FeatureSet},
    ]

    if gis is None:
        gis = arcgis.env.active_gis

    url = gis.properties.helperServices.elevation.url

    return _execute_gp_tool(gis, "Profile", kwargs, param_db, return_values, _use_async, url)


def viewshed(input_points: FeatureSet = {'exceededTransferLimit': False,
                                         'spatialReference': {'latestWkid': 3857, 'wkid': 102100},
                                         'geometryType': 'esriGeometryPoint',
                                         'fields': [{'name': 'OID', 'type': 'esriFieldTypeOID', 'alias': 'OID'},
                                                    {'name': 'offseta', 'type': 'esriFieldTypeDouble',
                                                     'alias': 'offseta'},
                                                    {'name': 'offsetb', 'type': 'esriFieldTypeDouble',
                                                     'alias': 'offsetb'}], 'displayFieldName': '', 'features': []},
             maximum_distance: float = None,
             maximum_distance_units: str = """Meters""",
             dem_resolution: str = None,
             observer_height: float = None,
             observer_height_units: str = """Meters""",
             surface_offset: float = None,
             surface_offset_units: str = """Meters""",
             generalize_viewshed_polygons: bool = True,
             gis=None) -> FeatureSet:
    """


Returns polygons of visible areas for a given set of input observation points.

Parameters:

   input_points: Input Point Features (FeatureSet). Required parameter.  The point features to use as the observer locations.

   maximum_distance: Maximum Distance (float). Optional parameter.  The maximum distance to calculate the viewshed.

   maximum_distance_units: Maximum Distance Units (str). Optional parameter.  The units for the Maximum Distance parameter. The default is meters.Meters — The units are meters. This is the default.Kilometers — The units are kilometers.Feet — The units are feet.Yards — The units are yards.Miles — The units are miles.
      Choice list:['Meters', 'Kilometers', 'Feet', 'Yards', 'Miles']

   dem_resolution: DEM Resolution (str). Optional parameter.  The approximate spatial resolution (cell size) of the source elevation data used for the calculation. The default is 90m.The resolution keyword is an approximation of the spatial resolution of the digital elevation model. Many elevation sources are distributed with units of arc seconds, the keyword is an approximation in meters for easier understanding.FINEST — The finest units available for the extent are used.10m — the elevation source resolution is 1/3 arc second, or approximately 10 meters.30m — the elevation source resolution is 1 arc second, or approximately 30 meters.90m — the elevation source resolution is 3 arc second, or approximately 90 meters.
      Choice list:[' ', 'FINEST', '10m', '30m', '90m']

   observer_height: Observer Height (float). Optional parameter.  The height above the surface of the observer. The default value of 1.75 meters is an average height of a person. If you are looking from an elevated location such as an observation tower or a tall building, use that height instead.

   observer_height_units: Observer Height Units (str). Optional parameter.  The units for the Observer Height parameter. The default is meters.Meters — The units are meters. This is the default.Kilometers — The units are kilometers.Feet — The units are feet.Yards — The units are yards.Miles — The units are miles.
      Choice list:['Meters', 'Kilometers', 'Feet', 'Yards', 'Miles']

   surface_offset: Surface Offset (float). Optional parameter.  The height above the surface of the object you are trying to see. The default value is 0. If you are trying to see buildings or wind turbines use their height here.

   surface_offset_units: Surface Offset Units (str). Optional parameter.  The units for the Surface Offset parameter. The default is meters.Meters — The units are meters. This is the default.Kilometers — The units are kilometers.Feet — The units are feet.Yards —The units are yards.Miles — The units are miles.
      Choice list:['Meters', 'Kilometers', 'Feet', 'Yards', 'Miles']

   generalize_viewshed_polygons: Generalize Viewshed Polygons (bool). Optional parameter.  Determine if the viewshed polygons are to be generalized or not.The viewshed calculation is based upon a raster elevation model which creates a result with stair-stepped edges. To create a more pleasing appearance and improve performance, the default behavior is to generalize the polygons. This generalization will not change the accuracy of the result for any location more than one half of the DEM's resolution.Checked — Generalizes the results. This is the default.Unchecked — No generalization of the output polygons will occur.

gis: Optional, the GIS on which this tool runs. If not specified, the active GIS is used.


Returns:
   output_viewshed - Output Viewshed as a FeatureSet

See http://ec2-35-161-157-22.us-west-2.compute.amazonaws.com:6080/arcgis/rest/directories/arcgisoutput/Tools/Elevation_GPServer/Tools_Elevation/Viewshed.htm for additional help.
    """
    kwargs = locals()

    param_db = {
        "input_points": (FeatureSet, "InputPoints"),
        "maximum_distance": (float, "MaximumDistance"),
        "maximum_distance_units": (str, "MaximumDistanceUnits"),
        "dem_resolution": (str, "DEMResolution"),
        "observer_height": (float, "ObserverHeight"),
        "observer_height_units": (str, "ObserverHeightUnits"),
        "surface_offset": (float, "SurfaceOffset"),
        "surface_offset_units": (str, "SurfaceOffsetUnits"),
        "generalize_viewshed_polygons": (bool, "GeneralizeViewshedPolygons"),
        "output_viewshed": (FeatureSet, "Output Viewshed"),
    }
    return_values = [
        {"name": "output_viewshed", "display_name": "Output Viewshed", "type": FeatureSet},
    ]

    if gis is None:
        gis = arcgis.env.active_gis

    url = gis.properties.helperServices.elevation.url

    return _execute_gp_tool(gis, "Viewshed", kwargs, param_db, return_values, _use_async, url)


def summarize_elevation(input_features: FeatureSet = {},
                        feature_id_field: str = None,
                        dem_resolution: str = None,
                        include_slope_aspect: bool = False,
                        gis=None) -> FeatureSet:
    """


Calculates summary statistics of elevation for each input feature.

Parameters:

   input_features: Input Features (FeatureSet). Required parameter.  Input point, line, or area features to summarize the elevation for.

   feature_id_field: Feature ID Field (str). Optional parameter.  The Unique ID field to use for the input features.

   dem_resolution: DEM Resolution (str). Optional parameter.  The approximate spatial resolution (cell size) of the source elevation data used for the calculation. The default is 90m.The resolution keyword is an approximation of the spatial resolution of the digital elevation model. Many elevation sources are distributed with units of arc seconds, the keyword is an approximation in meters for easier understanding.FINEST — The finest units available for the extent are used.10m — the elevation source resolution is 1/3 arc second, or approximately 10 meters.30m — the elevation source resolution is 1 arc second, or approximately 30 meters.90m — the elevation source resolution is 3 arc second, or approximately 90 meters.
      Choice list:[' ', 'FINEST', '10m', '30m', '90m']

   include_slope_aspect: Include Slope and Aspect (bool). Optional parameter.  Determines if slope and aspect for the input feature(s) will be included in the output.Checked — Slope and aspect values will be included in the output.Unchecked — Only the elevation values will be included in the output.

gis: Optional, the GIS on which this tool runs. If not specified, the active GIS is used.


Returns:
   output_summary - Output Summary as a FeatureSet

See http://ec2-35-161-157-22.us-west-2.compute.amazonaws.com:6080/arcgis/rest/directories/arcgisoutput/Tools/Elevation_GPServer/Tools_Elevation/SummarizeElevation.htm for additional help.
    """
    kwargs = locals()

    param_db = {
        "input_features": (FeatureSet, "InputFeatures"),
        "feature_id_field": (str, "FeatureIDField"),
        "dem_resolution": (str, "DEMResolution"),
        "include_slope_aspect": (bool, "IncludeSlopeAspect"),
        "output_summary": (FeatureSet, "Output Summary"),
    }
    return_values = [
        {"name": "output_summary", "display_name": "Output Summary", "type": FeatureSet},
    ]

    if gis is None:
        gis = arcgis.env.active_gis

    url = gis.properties.helperServices.elevation.url

    return _execute_gp_tool(gis, "SummarizeElevation", kwargs, param_db, return_values, _use_async, url)


