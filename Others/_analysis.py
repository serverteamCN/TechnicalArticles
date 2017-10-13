import logging as _logging
import arcgis
from datetime import datetime
from arcgis.features import FeatureSet
from arcgis.mapping import MapImageLayer
from arcgis.geoprocessing import DataFile, LinearUnit, RasterData
from arcgis.geoprocessing._support import _execute_gp_tool

_log = _logging.getLogger(__name__)

_use_async = True


def aggregate_points(point_layer: str = None,
                     polygon_layer: str = None,
                     keep_boundaries_with_no_points: bool = True,
                     summary_fields: str = """[]""",
                     group_by_field: str = None,
                     minority_majority: bool = False,
                     percent_points: bool = False,
                     output_name: str = None,
                     context: str = None,
                     gis=None) -> tuple:
    """


Aggregate points task allows you to aggregate or count the total number of points that are distributed within specified areas or boundaries (polygons). You can also summarize Sum, Mean, Min, Max and Standard deviation calculations for attributes of the point layer to understand the general characteristics of aggregated points.

Parameters:

   point_layer: pointLayer (str). Required parameter.  Point layer to be aggregated

   polygon_layer: polygonLayer (str). Required parameter.  Polygon layer to which the points should be aggregated.

   keep_boundaries_with_no_points: keepBoundariesWithNoPoints (bool). Optional parameter.  Specify whether the polygons without any points should be returned in the output.

   summary_fields: summaryFields (str). Optional parameter.  A list of field names and summary type. Example [“fieldName1 summaryType1”,”fieldName2 summaryType2”].

   group_by_field: groupByField (str). Optional parameter.  A field name from PointLayer based on which the points will be grouped.

   minority_majority: minorityMajority (bool). Optional parameter.  This boolean parameter is applicable only when a groupByField is specified. If true, the minority (least dominant) or the majority (most dominant) attribute values within each group, within each boundary will be calculated.

   percent_points: percentPoints (bool). Optional parameter.  This boolean parameter is applicable only when a groupByField is specified. If set to true, the percentage count of points for each unique groupByField value is calculated.

   output_name: outputName (str). Optional parameter.  Additional properties such as output feature service name.

   context: context (str). Optional parameter.  Additional settings such as processing extent and output spatial reference.

gis: Optional, the GIS on which this tool runs. If not specified, the active GIS is used.


Returns the following as a named tuple:
   aggregated_layer - aggregatedLayer as a str
   group_summary - groupSummary as a str

See http://analysis6.arcgis.com:80/arcgis/rest/directories/arcgisoutput/tasks_GPServer/tasks/AggregatePoints.htm for additional help.
    """
    kwargs = locals()

    param_db = {
        "point_layer": (str, "pointLayer"),
        "polygon_layer": (str, "polygonLayer"),
        "keep_boundaries_with_no_points": (bool, "keepBoundariesWithNoPoints"),
        "summary_fields": (str, "summaryFields"),
        "group_by_field": (str, "groupByField"),
        "minority_majority": (bool, "minorityMajority"),
        "percent_points": (bool, "percentPoints"),
        "output_name": (str, "outputName"),
        "context": (str, "context"),
        "aggregated_layer": (str, "aggregatedLayer"),
        "group_summary": (str, "groupSummary"),
    }
    return_values = [
        {"name": "aggregated_layer", "display_name": "aggregatedLayer", "type": str},
        {"name": "group_summary", "display_name": "groupSummary", "type": str},
    ]

    if gis is None:
        gis = arcgis.env.active_gis
    url = gis.properties.helperServices.analysis.url

    return _execute_gp_tool(gis, "AggregatePoints", kwargs, param_db, return_values, _use_async, url)


def find_hot_spots(analysis_layer: str = None,
                   analysis_field: str = None,
                   divided_by_field: str = None,
                   bounding_polygon_layer: str = None,
                   aggregation_polygon_layer: str = None,
                   output_name: str = None,
                   context: str = None,
                   gis=None) -> tuple:
    """


The “Find Hot Spots” task finds statistically significant clusters of incident points, weighted points, or weighted polygons. For incident data, the analysis field (weight) is obtained by aggregation. Output is a hot spot map.

Parameters:

   analysis_layer: analysisLayer (str). Required parameter.  The point or polygon feature layer for which hot spots will be calculated.

   analysis_field: analysisField (str). Optional parameter.  The numeric field in the AnalysisLayer that will be analyzed.

   divided_by_field: dividedByField (str). Optional parameter.

   bounding_polygon_layer: boundingPolygonLayer (str). Optional parameter.  When the analysis layer is points and no AnalysisField is specified, you can provide polygons features that define where incidents could have occurred.

   aggregation_polygon_layer: aggregationPolygonLayer (str). Optional parameter.  When the AnalysisLayer contains points and no AnalysisField is specified, you can provide polygon features into which the points will be aggregated and analyzed, such as administrative units.

   output_name: outputName (str). Optional parameter.  Additional properties such as output feature service name.

   context: context (str). Optional parameter.  Additional settings such as processing extent and output spatial reference.

gis: Optional, the GIS on which this tool runs. If not specified, the active GIS is used.


Returns the following as a named tuple:
   hot_spots_result_layer - hotSpotsResultLayer as a str
   process_info - processInfo as a str

See http://analysis6.arcgis.com:80/arcgis/rest/directories/arcgisoutput/tasks_GPServer/tasks/FindHotSpots.htm for additional help.
    """
    kwargs = locals()

    param_db = {
        "analysis_layer": (str, "analysisLayer"),
        "analysis_field": (str, "analysisField"),
        "divided_by_field": (str, "dividedByField"),
        "bounding_polygon_layer": (str, "boundingPolygonLayer"),
        "aggregation_polygon_layer": (str, "aggregationPolygonLayer"),
        "output_name": (str, "outputName"),
        "context": (str, "context"),
        "hot_spots_result_layer": (str, "hotSpotsResultLayer"),
        "process_info": (str, "processInfo"),
    }
    return_values = [
        {"name": "hot_spots_result_layer", "display_name": "hotSpotsResultLayer", "type": str},
        {"name": "process_info", "display_name": "processInfo", "type": str},
    ]

    if gis is None:
        gis = arcgis.env.active_gis
    url = gis.properties.helperServices.analysis.url

    return _execute_gp_tool(gis, "FindHotSpots", kwargs, param_db, return_values, _use_async, url)


def create_buffers(input_layer: str = None,
                   distances: str = """[]""",
                   field: str = None,
                   units: str = """Meters""",
                   dissolve_type: str = """None""",
                   ring_type: str = """Disks""",
                   side_type: str = """Full""",
                   end_type: str = """Round""",
                   output_name: str = None,
                   context: str = None,
                   gis=None) -> str:
    """


Creates buffer polygon(s) around input features.

Parameters:

   input_layer: inputLayer (str). Required parameter.  The input to be buffered.

   distances: distances (str). Optional parameter.  The distance(s) that will be buffered.

   field: field (str). Optional parameter.  Buffers will be created using field values.

   units: units (str). Optional parameter.  The linear unit to be used with the distance value(s).
      Choice list:['Feet', 'Kilometers', 'Meters', 'Miles', 'NauticalMiles', 'Yards']

   dissolve_type: dissolveType (str). Optional parameter.  Specifies the dissolve to be performed to remove buffer overlap.
      Choice list:['None', 'Dissolve', 'Split']

   ring_type: ringType (str). Optional parameter.  The ring type.
      Choice list:['Disks', 'Rings']

   side_type: sideType (str). Optional parameter.  The side(s) of the input that will be buffered.
      Choice list:['Full', 'Left', 'Right', 'Outside']

   end_type: endType (str). Optional parameter.  The shape of the buffer at the end of buffered line features.
      Choice list:['Round', 'Flat']

   output_name: outputName (str). Optional parameter.  Additional properties such as output feature service name.

   context: context (str). Optional parameter.  Additional settings such as processing extent and output spatial reference.

gis: Optional, the GIS on which this tool runs. If not specified, the active GIS is used.


Returns:
   buffer_layer - bufferLayer as a str

See http://analysis6.arcgis.com:80/arcgis/rest/directories/arcgisoutput/tasks_GPServer/tasks/CreateBuffers.htm for additional help.
    """
    kwargs = locals()

    param_db = {
        "input_layer": (str, "inputLayer"),
        "distances": (str, "distances"),
        "field": (str, "field"),
        "units": (str, "units"),
        "dissolve_type": (str, "dissolveType"),
        "ring_type": (str, "ringType"),
        "side_type": (str, "sideType"),
        "end_type": (str, "endType"),
        "output_name": (str, "outputName"),
        "context": (str, "context"),
        "buffer_layer": (str, "bufferLayer"),
    }
    return_values = [
        {"name": "buffer_layer", "display_name": "bufferLayer", "type": str},
    ]

    if gis is None:
        gis = arcgis.env.active_gis
    url = gis.properties.helperServices.analysis.url

    return _execute_gp_tool(gis, "CreateBuffers", kwargs, param_db, return_values, _use_async, url)


def create_drive_time_areas(input_layer: str = None,
                            break_values: str = """[5, 10, 15]""",
                            break_units: str = """Minutes""",
                            travel_mode: str = """Driving""",
                            overlap_policy: str = """Overlap""",
                            time_of_day: datetime = None,
                            time_zone_for_time_of_day: str = """GeoLocal""",
                            output_name: str = None,
                            context: str = None,
                            gis=None) -> str:
    """




Parameters:

   input_layer: inputLayer (str). Required parameter.

   break_values: breakValues (str). Optional parameter.

   break_units: breakUnits (str). Optional parameter.
      Choice list:['Minutes', 'Seconds', 'Hours', 'Miles', 'Kilometers', 'Meters', 'Feet', 'Yards']

   travel_mode: travelMode (str). Optional parameter.

   overlap_policy: overlapPolicy (str). Optional parameter.
      Choice list:['Overlap', 'Dissolve', 'Split']

   time_of_day: timeOfDay (datetime). Optional parameter.

   time_zone_for_time_of_day: timeZoneForTimeOfDay (str). Optional parameter.
      Choice list:['UTC', 'GeoLocal']

   output_name: outputName (str). Optional parameter.  Additional properties such as output feature service name.

   context: context (str). Optional parameter.  Additional settings such as processing extent and output spatial reference.

gis: Optional, the GIS on which this tool runs. If not specified, the active GIS is used.


Returns:
   drive_time_areas_layer - driveTimeAreasLayer as a str

See http://analysis6.arcgis.com:80/arcgis/rest/directories/arcgisoutput/tasks_GPServer/tasks/CreateDriveTimeAreas.htm for additional help.
    """
    kwargs = locals()

    param_db = {
        "input_layer": (str, "inputLayer"),
        "break_values": (str, "breakValues"),
        "break_units": (str, "breakUnits"),
        "travel_mode": (str, "travelMode"),
        "overlap_policy": (str, "overlapPolicy"),
        "time_of_day": (datetime, "timeOfDay"),
        "time_zone_for_time_of_day": (str, "timeZoneForTimeOfDay"),
        "output_name": (str, "outputName"),
        "context": (str, "context"),
        "drive_time_areas_layer": (str, "driveTimeAreasLayer"),
    }
    return_values = [
        {"name": "drive_time_areas_layer", "display_name": "driveTimeAreasLayer", "type": str},
    ]

    if gis is None:
        gis = arcgis.env.active_gis
    url = gis.properties.helperServices.analysis.url

    return _execute_gp_tool(gis, "CreateDriveTimeAreas", kwargs, param_db, return_values, _use_async, url)


def dissolve_boundaries(input_layer: str = None,
                        dissolve_fields: str = """[]""",
                        summary_fields: str = """[]""",
                        output_name: str = None,
                        context: str = None,
                        gis=None) -> str:
    """


Dissolve features based on specified fields.

Parameters:

   input_layer: inputLayer (str). Required parameter.  The layer containing polygon features that will be dissolved.

   dissolve_fields: dissolveFields (str). Optional parameter.  One or more fields from the input that control which polygons are merged. If no fields are supplied, all polygons that overlap or shared a common border will be dissolved into one polygon.

   summary_fields: summaryFields (str). Optional parameter.  A list of field names and statistical types that will be used to summarize the output. Supported statistics include: Sum, Mean, Min, Max, and Stddev.

   output_name: outputName (str). Optional parameter.  Additional properties such as output feature service name.

   context: context (str). Optional parameter.  Additional settings such as processing extent and output spatial reference.

gis: Optional, the GIS on which this tool runs. If not specified, the active GIS is used.


Returns:
   dissolved_layer - dissolvedLayer as a str

See http://analysis6.arcgis.com:80/arcgis/rest/directories/arcgisoutput/tasks_GPServer/tasks/DissolveBoundaries.htm for additional help.
    """
    kwargs = locals()

    param_db = {
        "input_layer": (str, "inputLayer"),
        "dissolve_fields": (str, "dissolveFields"),
        "summary_fields": (str, "summaryFields"),
        "output_name": (str, "outputName"),
        "context": (str, "context"),
        "dissolved_layer": (str, "dissolvedLayer"),
    }
    return_values = [
        {"name": "dissolved_layer", "display_name": "dissolvedLayer", "type": str},
    ]

    if gis is None:
        gis = arcgis.env.active_gis
    url = gis.properties.helperServices.analysis.url

    return _execute_gp_tool(gis, "DissolveBoundaries", kwargs, param_db, return_values, _use_async, url)


def merge_layers(input_layer: str = None,
                 merge_layer: str = None,
                 merging_attributes: str = """[]""",
                 output_name: str = None,
                 context: str = None,
                 gis=None) -> str:
    """


Combines two inputs of the same feature data type into a new output.

Parameters:

   input_layer: inputLayer (str). Required parameter.   The point, line, or polygon  features to merge with the mergeLayer.

   merge_layer: mergeLayer (str). Required parameter.  The point, line or polygon features to merge with inputLayer.  mergeLayer must contain the same feature type (point, line, or polygon) as the inputLayer.

   merging_attributes: mergingAttributes (str). Optional parameter.  An array of values that describe how fields from the mergeLayer are to be modified.  By default all fields from both inputs will be carried across to the output.

   output_name: outputName (str). Optional parameter.  Additional properties such as output feature service name.

   context: context (str). Optional parameter.  Additional settings such as processing extent and output spatial reference.

gis: Optional, the GIS on which this tool runs. If not specified, the active GIS is used.


Returns:
   merged_layer - mergedLayer as a str

See http://analysis6.arcgis.com:80/arcgis/rest/directories/arcgisoutput/tasks_GPServer/tasks/MergeLayers.htm for additional help.
    """
    kwargs = locals()

    param_db = {
        "input_layer": (str, "inputLayer"),
        "merge_layer": (str, "mergeLayer"),
        "merging_attributes": (str, "mergingAttributes"),
        "output_name": (str, "outputName"),
        "context": (str, "context"),
        "merged_layer": (str, "mergedLayer"),
    }
    return_values = [
        {"name": "merged_layer", "display_name": "mergedLayer", "type": str},
    ]

    if gis is None:
        gis = arcgis.env.active_gis
    url = gis.properties.helperServices.analysis.url

    return _execute_gp_tool(gis, "MergeLayers", kwargs, param_db, return_values, _use_async, url)


def summarize_within(sum_within_layer: str = None,
                     summary_layer: str = None,
                     sum_shape: bool = True,
                     shape_units: str = None,
                     summary_fields: str = """[]""",
                     group_by_field: str = None,
                     minority_majority: bool = False,
                     percent_shape: bool = False,
                     output_name: str = None,
                     context: str = None,
                     gis=None) -> tuple:
    """


The SummarizeWithin task helps you to summarize and find statistics on the point, line, or polygon features (or portions of these features) that are within the boundaries of polygons in another layer. For example:Given a layer of watershed boundaries and a layer of land-use boundaries by land-use type, calculate total acreage of land-use type for each watershed.Given a layer of parcels in a county and a layer of city boundaries, summarize the average value of vacant parcels within each city boundary.Given a layer of counties and a layer of roads, summarize the total mileage of roads by road type within each county.

Parameters:

   sum_within_layer: sumWithinLayer (str). Required parameter.  A polygon feature layer or featurecollection. Features, or portions of features, in the summaryLayer (below) that fall within the boundaries of these polygons will be summarized.

   summary_layer: summaryLayer (str). Required parameter.  Point, line, or polygon features that will be summarized for each polygon in the sumWithinLayer.

   sum_shape: sumShape (bool). Optional parameter.  A boolean value that instructs the task to calculate count of points, length of lines or areas of polygons of the summaryLayer within each polygon in sumWithinLayer.

   shape_units: shapeUnits (str). Optional parameter.  Specify units to summarize the length or areas when sumShape is set to true. Units is not required to summarize points.
      Choice list:['Acres', 'Hectares', 'SquareMeters', 'SquareKilometers', 'SquareFeet', 'SquareYards', 'SquareMiles', 'Meters', 'Kilometers', 'Feet', 'Yards', 'Miles']

   summary_fields: summaryFields (str). Optional parameter.  A list of field names and statistical summary type that you wish to calculate for all features in the  summaryLayer that are within each polygon in the sumWithinLayer . Eg: ["fieldname1 summary", "fieldname2 summary"]

   group_by_field: groupByField (str). Optional parameter.  Specify a field from the summaryLayer features to calculate statistics separately for each unique attribute value.

   minority_majority: minorityMajority (bool). Optional parameter.  This boolean parameter is applicable only when a groupByField is specified. If true, the minority (least dominant) or the majority (most dominant) attribute values within each group, within each boundary will be calculated.

   percent_shape: percentShape (bool). Optional parameter.  This boolean parameter is applicable only when a groupByField is specified. If set to true, the percentage of shape (eg. length for lines) for each unique groupByField value is calculated.

   output_name: outputName (str). Optional parameter.  Additional properties such as output feature service name.

   context: context (str). Optional parameter.  Additional settings such as processing extent and output spatial reference.

gis: Optional, the GIS on which this tool runs. If not specified, the active GIS is used.


Returns the following as a named tuple:
   result_layer - resultLayer as a str
   group_by_summary - groupBySummary as a str

See http://analysis6.arcgis.com:80/arcgis/rest/directories/arcgisoutput/tasks_GPServer/tasks/SummarizeWithin.htm for additional help.
    """
    kwargs = locals()

    param_db = {
        "sum_within_layer": (str, "sumWithinLayer"),
        "summary_layer": (str, "summaryLayer"),
        "sum_shape": (bool, "sumShape"),
        "shape_units": (str, "shapeUnits"),
        "summary_fields": (str, "summaryFields"),
        "group_by_field": (str, "groupByField"),
        "minority_majority": (bool, "minorityMajority"),
        "percent_shape": (bool, "percentShape"),
        "output_name": (str, "outputName"),
        "context": (str, "context"),
        "result_layer": (str, "resultLayer"),
        "group_by_summary": (str, "groupBySummary"),
    }
    return_values = [
        {"name": "result_layer", "display_name": "resultLayer", "type": str},
        {"name": "group_by_summary", "display_name": "groupBySummary", "type": str},
    ]

    if gis is None:
        gis = arcgis.env.active_gis
    url = gis.properties.helperServices.analysis.url

    return _execute_gp_tool(gis, "SummarizeWithin", kwargs, param_db, return_values, _use_async, url)


def enrich_layer(input_layer: str = None,
                 data_collections: str = """[]""",
                 analysis_variables: str = """[]""",
                 country: str = None,
                 buffer_type: str = None,
                 distance: float = None,
                 units: str = None,
                 return_boundaries: bool = False,
                 output_name: str = None,
                 context: str = None,
                 gis=None) -> str:
    """


The Enrich Layer task enriches your data by getting facts about the people, places, and businesses that surround your data locations. For example: What kind of people live here? What do people like to do in this area? What are their habits and lifestyles? What kind of businesses are there in this area?The result will be a new layer of input features that includes all demographic and geographic information from given data collections.

Parameters:

   input_layer: inputLayer (str). Required parameter.  Feature layer to enrich with new data

   data_collections: dataCollections (str). Optional parameter.  Data collections you wish to add to your features.

   analysis_variables: analysisVariables (str). Optional parameter.  A subset of specific variables instead of dataCollections.

   country: country (str). Optional parameter.  The two character country code that specifies the country of the input features. Eg. US (United States),  FR (France), GB (United Kingdom) etc.

   buffer_type: bufferType (str). Optional parameter.  Area to be created around the point or line features for enrichment. Default is 1 Mile straight-line buffer radius.

   distance: distance (float). Optional parameter.  A double value that defines the straight-line distance or time (when drivingTime is used).

   units: units (str). Optional parameter.  The unit (eg. Miles, Minutes) to be used with the distance value(s) specified in the distance parameter to calculate the area.
      Choice list:['Feet', 'Yards', 'Miles', 'Meters', 'Kilometers', 'Seconds', 'Minutes', 'Hours']

   return_boundaries: returnBoundaries (bool). Optional parameter.  Applicable, only for point and line  input features. If true, will return a result layer of areas. The resulting areas are defined by the specified bufferType. For example, if using a StraightLine of 5 miles, your result will contain areas with a 5 mile radius around the input features and requested enrichment variables. If false, the resulting layer will return the same features as the input layer with geoenrichment variables.

   output_name: outputName (str). Optional parameter.  Additional properties such as output feature service name.

   context: context (str). Optional parameter.  Additional settings such as processing extent and output spatial reference.

gis: Optional, the GIS on which this tool runs. If not specified, the active GIS is used.


Returns:
   enriched_layer - enrichedLayer as a str

See http://analysis6.arcgis.com:80/arcgis/rest/directories/arcgisoutput/tasks_GPServer/tasks/EnrichLayer.htm for additional help.
    """
    kwargs = locals()

    param_db = {
        "input_layer": (str, "inputLayer"),
        "data_collections": (str, "dataCollections"),
        "analysis_variables": (str, "analysisVariables"),
        "country": (str, "country"),
        "buffer_type": (str, "bufferType"),
        "distance": (float, "distance"),
        "units": (str, "units"),
        "return_boundaries": (bool, "returnBoundaries"),
        "output_name": (str, "outputName"),
        "context": (str, "context"),
        "enriched_layer": (str, "enrichedLayer"),
    }
    return_values = [
        {"name": "enriched_layer", "display_name": "enrichedLayer", "type": str},
    ]

    if gis is None:
        gis = arcgis.env.active_gis
    url = gis.properties.helperServices.analysis.url

    return _execute_gp_tool(gis, "EnrichLayer", kwargs, param_db, return_values, _use_async, url)


def overlay_layers(input_layer: str = None,
                   overlay_layer: str = None,
                   overlay_type: str = """Intersect""",
                   snap_to_input: bool = False,
                   output_type: str = """Input""",
                   tolerance: float = None,
                   output_name: str = None,
                   context: str = None,
                   gis=None) -> str:
    """


Overlays the input layer with the overlay layer. Overlay operations supported are Intersect, Union, and Erase.

Parameters:

   input_layer: inputLayer (str). Required parameter.  The input analysis layer.

   overlay_layer: overlayLayer (str). Required parameter.  The layer to be overlaid with the analysis layer.

   overlay_type: overlayType (str). Optional parameter.  The overlay type (INTERSECT, UNION, or ERASE) defines how the analysis layer and the overlay layer are combined.
      Choice list:['Intersect', 'Union', 'Erase']

   snap_to_input: snapToInput (bool). Optional parameter.  When the distance between features is less than the tolerance, the features in the overlay layer will snap to the features in the input layer.

   output_type: outputType (str). Optional parameter.  The type of intersection (INPUT, LINE, POINT).
      Choice list:['Input', 'Point', 'Line']

   tolerance: tolerance (float). Optional parameter.  The minimum distance separating all feature coordinates (nodes and vertices) as well as the distance a coordinate can move in X or Y (or both).

   output_name: outputName (str). Optional parameter.  Additional properties such as output feature service name.

   context: context (str). Optional parameter.  Additional settings such as processing extent and output spatial reference.

gis: Optional, the GIS on which this tool runs. If not specified, the active GIS is used.


Returns:
   output_layer - outputLayer as a str

See http://analysis6.arcgis.com:80/arcgis/rest/directories/arcgisoutput/tasks_GPServer/tasks/OverlayLayers.htm for additional help.
    """
    kwargs = locals()

    param_db = {
        "input_layer": (str, "inputLayer"),
        "overlay_layer": (str, "overlayLayer"),
        "overlay_type": (str, "overlayType"),
        "snap_to_input": (bool, "snapToInput"),
        "output_type": (str, "outputType"),
        "tolerance": (float, "tolerance"),
        "output_name": (str, "outputName"),
        "context": (str, "context"),
        "output_layer": (str, "outputLayer"),
    }
    return_values = [
        {"name": "output_layer", "display_name": "outputLayer", "type": str},
    ]

    if gis is None:
        gis = arcgis.env.active_gis
    url = gis.properties.helperServices.analysis.url

    return _execute_gp_tool(gis, "OverlayLayers", kwargs, param_db, return_values, _use_async, url)


def extract_data(input_layers: str = """[]""",
                 extent: str = None,
                 clip: bool = False,
                 data_format: str = None,
                 output_name: str = None,
                 context: str = None,
                 gis=None) -> str:
    """


Select and download data for a specified area of interest. Layers that you select will be added to a zip file or layer package.

Parameters:

   input_layers: inputLayers (str). Required parameter.  The layers from which you can extract features.

   extent: extent (str). Optional parameter.  The area that defines which features will be included in the output zip file or layer package.

   clip: clip (bool). Optional parameter.  Select features that intersect the extent or clip features within the extent.

   data_format: dataFormat (str). Optional parameter.  Format of the data that will be extracted and downloaded.  Layer packages will always include file geodatabases.&lt;/p&gt;
      Choice list:['FileGeodatabase', 'ShapeFile', 'KML', 'CSV']

   output_name: outputName (str). Optional parameter.  Additional properties such as output feature service name.

   context: context (str). Optional parameter.  Additional settings such as processing extent and output spatial reference.

gis: Optional, the GIS on which this tool runs. If not specified, the active GIS is used.


Returns:
   content_id - contentID as a str

See http://analysis6.arcgis.com:80/arcgis/rest/directories/arcgisoutput/tasks_GPServer/tasks/ExtractData.htm for additional help.
    """
    kwargs = locals()

    param_db = {
        "input_layers": (str, "inputLayers"),
        "extent": (str, "extent"),
        "clip": (bool, "clip"),
        "data_format": (str, "dataFormat"),
        "output_name": (str, "outputName"),
        "context": (str, "context"),
        "content_id": (str, "contentID"),
    }
    return_values = [
        {"name": "content_id", "display_name": "contentID", "type": str},
    ]

    if gis is None:
        gis = arcgis.env.active_gis
    url = gis.properties.helperServices.analysis.url

    return _execute_gp_tool(gis, "ExtractData", kwargs, param_db, return_values, _use_async, url)


def find_existing_locations(input_layers: str = """[]""",
                            expressions: str = None,
                            output_name: str = None,
                            context: str = None,
                            gis=None) -> str:
    """


The Find Existing Locations task selects features in the input layer that meet a query you specify. A query is made up of one or more expressions. There are two types of expressions: attribute and spatial. An example of an attribute expression is that a parcel must be vacant, which is an attribute of the Parcels layer (where STATUS = 'VACANT'). An example of a spatial expression is that the parcel must also be within a certain distance of a river (Parcels within a distance of 0.75 Miles from Rivers).

Parameters:

   input_layers: inputLayers (str). Required parameter.  A list of layers that will be used in the expressions parameter.

   expressions: expressions (str). Required parameter.  Specify a list of expressions. Please refer documentation at http://developers.arcgis.com for more information on creating expressions.

   output_name: outputName (str). Optional parameter.  Additional properties such as output feature service name.

   context: context (str). Optional parameter.  Additional settings such as processing extent and output spatial reference.

gis: Optional, the GIS on which this tool runs. If not specified, the active GIS is used.


Returns:
   result_layer - resultLayer as a str

See http://analysis6.arcgis.com:80/arcgis/rest/directories/arcgisoutput/tasks_GPServer/tasks/FindExistingLocations.htm for additional help.
    """
    kwargs = locals()

    param_db = {
        "input_layers": (str, "inputLayers"),
        "expressions": (str, "expressions"),
        "output_name": (str, "outputName"),
        "context": (str, "context"),
        "result_layer": (str, "resultLayer"),
    }
    return_values = [
        {"name": "result_layer", "display_name": "resultLayer", "type": str},
    ]

    if gis is None:
        gis = arcgis.env.active_gis
    url = gis.properties.helperServices.analysis.url

    return _execute_gp_tool(gis, "FindExistingLocations", kwargs, param_db, return_values, _use_async, url)


def derive_new_locations(input_layers: str = """[]""",
                         expressions: str = None,
                         output_name: str = None,
                         context: str = None,
                         gis=None) -> str:
    """


The Derive New Locations task derives new features from the input layers that meet a query you specify. A query is made up of one or more expressions. There are two types of expressions: attribute and spatial. An example of an attribute expression is that a parcel must be vacant, which is an attribute of the Parcels layer (where STATUS = 'VACANT'). An example of a spatial expression is that the parcel must also be within a certain distance of a river (Parcels within a distance of 0.75 Miles from Rivers).The Derive New Locations task is very similar to the Find Existing Locations task, the main difference is that the result of Derive New Locations can contain partial features.In both tasks, the attribute expression  where and the spatial relationships within and contains return the same result. This is because these relationships return entire features.When intersects or withinDistance is used, Derive New Locations creates new features in the result. For example, when intersecting a parcel feature and a flood zone area that partially overlap each other, Find Existing Locations will return the entire parcel whereas Derive New Locations will return just the portion of the parcel that is within the flood zone.

Parameters:

   input_layers: inputLayers (str). Required parameter.  A list of layers that will be used in the expressions parameter.

   expressions: expressions (str). Required parameter.  Specify a list of expressions. Please refer documentation at http://developers.arcgis.com for more information on expressions.

   output_name: outputName (str). Optional parameter.  Additional properties such as output feature service name.

   context: context (str). Optional parameter.  Additional settings such as processing extent and output spatial reference.

gis: Optional, the GIS on which this tool runs. If not specified, the active GIS is used.


Returns:
   result_layer - resultLayer as a str

See http://analysis6.arcgis.com:80/arcgis/rest/directories/arcgisoutput/tasks_GPServer/tasks/DeriveNewLocations.htm for additional help.
    """
    kwargs = locals()

    param_db = {
        "input_layers": (str, "inputLayers"),
        "expressions": (str, "expressions"),
        "output_name": (str, "outputName"),
        "context": (str, "context"),
        "result_layer": (str, "resultLayer"),
    }
    return_values = [
        {"name": "result_layer", "display_name": "resultLayer", "type": str},
    ]

    if gis is None:
        gis = arcgis.env.active_gis
    url = gis.properties.helperServices.analysis.url

    return _execute_gp_tool(gis, "DeriveNewLocations", kwargs, param_db, return_values, _use_async, url)


def field_calculator(input_layer: str = None,
                     expressions: str = None,
                     output_name: str = None,
                     context: str = None,
                     gis=None) -> str:
    """


Calculates existing fields or creates and calculates new fields.

Parameters:

   input_layer: inputLayer (str). Required parameter.

   expressions: expressions (str). Required parameter.

   output_name: outputName (str). Optional parameter.

   context: context (str). Optional parameter.

gis: Optional, the GIS on which this tool runs. If not specified, the active GIS is used.


Returns:
   result_layer - resultLayer as a str

See http://analysis6.arcgis.com:80/arcgis/rest/directories/arcgisoutput/tasks_GPServer/tasks/FieldCalculator.htm for additional help.
    """
    kwargs = locals()

    param_db = {
        "input_layer": (str, "inputLayer"),
        "expressions": (str, "expressions"),
        "output_name": (str, "outputName"),
        "context": (str, "context"),
        "result_layer": (str, "resultLayer"),
    }
    return_values = [
        {"name": "result_layer", "display_name": "resultLayer", "type": str},
    ]

    if gis is None:
        gis = arcgis.env.active_gis
    url = gis.properties.helperServices.analysis.url

    return _execute_gp_tool(gis, "FieldCalculator", kwargs, param_db, return_values, _use_async, url)


def interpolate_points(input_layer: str = None,
                       field: str = None,
                       interpolate_option: str = """5""",
                       output_prediction_error: bool = False,
                       classification_type: str = """GeometricInterval""",
                       num_classes: int = 10,
                       class_breaks: str = """[]""",
                       bounding_polygon_layer: str = None,
                       predict_at_point_layer: str = None,
                       output_name: str = None,
                       context: str = None,
                       gis=None) -> tuple:
    """


The Interpolate Points task allows you to predict values at new locations based on measurements from a collection of points. The task takes point data with values at each point and returns areas classified by predicted values.

Parameters:

   input_layer: inputLayer (str). Required parameter.  The point layer whose features will be interpolated.

   field: field (str). Required parameter.  Name of the numeric field containing the values you wish to interpolate.

   interpolate_option: interpolateOption (str). Optional parameter.  Integer value declaring your preference for speed versus accuracy, from 1 (fastest) to 9 (most accurate). More accurate predictions take longer to calculate.
      Choice list:['1', '5', '9']

   output_prediction_error: outputPredictionError (bool). Optional parameter.  If True, a polygon layer of standard errors for the interpolation predictions will be returned in the predictionError output parameter.

   classification_type: classificationType (str). Optional parameter.  Determines how predicted values will be classified into areas.
      Choice list:['EqualArea', 'EqualInterval', 'GeometricInterval', 'Manual']

   num_classes: numClasses (int). Optional parameter.  This value is used to divide the range of interpolated values into distinct classes. The range of values in each class is determined by the classificationType parameter. Each class defines the boundaries of the result polygons.

   class_breaks: classBreaks (str). Optional parameter.  If classificationType is Manual, supply desired class break values separated by spaces. These values define the upper limit of each class, so the number of classes will equal the number of entered values. Areas will not be created for any locations with predicted values above the largest entered break value. You must enter at least two values and no more than 32.

   bounding_polygon_layer: boundingPolygonLayer (str). Optional parameter.  A layer specifying the polygon(s) where you want values to be interpolated.

   predict_at_point_layer: predictAtPointLayer (str). Optional parameter.  An optional layer specifying point locations to calculate prediction values. This allows you to make predictions at specific locations of interest.

   output_name: outputName (str). Optional parameter.  Additional properties such as output feature service name.

   context: context (str). Optional parameter.  Additional settings such as processing extent and output spatial reference.

gis: Optional, the GIS on which this tool runs. If not specified, the active GIS is used.


Returns the following as a named tuple:
   result_layer - resultLayer as a str
   prediction_error - predictionError as a str
   predicted_point_layer - predictedPointLayer as a str

See http://analysis6.arcgis.com:80/arcgis/rest/directories/arcgisoutput/tasks_GPServer/tasks/InterpolatePoints.htm for additional help.
    """
    kwargs = locals()

    param_db = {
        "input_layer": (str, "inputLayer"),
        "field": (str, "field"),
        "interpolate_option": (str, "interpolateOption"),
        "output_prediction_error": (bool, "outputPredictionError"),
        "classification_type": (str, "classificationType"),
        "num_classes": (int, "numClasses"),
        "class_breaks": (str, "classBreaks"),
        "bounding_polygon_layer": (str, "boundingPolygonLayer"),
        "predict_at_point_layer": (str, "predictAtPointLayer"),
        "output_name": (str, "outputName"),
        "context": (str, "context"),
        "result_layer": (str, "resultLayer"),
        "prediction_error": (str, "predictionError"),
        "predicted_point_layer": (str, "predictedPointLayer"),
    }
    return_values = [
        {"name": "result_layer", "display_name": "resultLayer", "type": str},
        {"name": "prediction_error", "display_name": "predictionError", "type": str},
        {"name": "predicted_point_layer", "display_name": "predictedPointLayer", "type": str},
    ]

    if gis is None:
        gis = arcgis.env.active_gis
    url = gis.properties.helperServices.analysis.url

    return _execute_gp_tool(gis, "InterpolatePoints", kwargs, param_db, return_values, _use_async, url)


def calculate_density(input_layer: str = None,
                      field: str = None,
                      cell_size: float = None,
                      cell_size_units: str = """Meters""",
                      radius: float = None,
                      radius_units: str = None,
                      bounding_polygon_layer: str = None,
                      area_units: str = None,
                      classification_type: str = """EqualInterval""",
                      num_classes: int = 10,
                      output_name: str = None,
                      context: str = None,
                      gis=None) -> str:
    """


The Calculate Density task creates a density map from point or line features by spreading known quantities of some phenomenon (represented as attributes of the points or lines) across the map. The result is a layer of areas classified from least dense to most dense.

Parameters:

   input_layer: inputLayer (str). Required parameter.  The point or line features from which to calculate density.

   field: field (str). Optional parameter.  A numeric field name specifying the number of incidents at each location. If not specified, each location will be assumed to represent a single count.

   cell_size: cellSize (float). Optional parameter.  This value is used to create a mesh of points where density values are calculated. The default is approximately 1/1000th of the smaller of the width and height of the analysis extent as defined in the context parameter.

   cell_size_units: cellSizeUnits (str). Optional parameter.  The units of the cellSize value
      Choice list:['Meters', 'Kilometers', 'Feet', 'Miles']

   radius: radius (float). Optional parameter.  A distance specifying how far to search to find point or line features when calculating density values.

   radius_units: radiusUnits (str). Optional parameter.  The units of the radius parameter.
      Choice list:['Meters', 'Kilometers', 'Feet', 'Miles']

   bounding_polygon_layer: boundingPolygonLayer (str). Optional parameter.  A layer specifying the polygon(s) where you want densities to be calculated.

   area_units: areaUnits (str). Optional parameter.  The units of the calculated density values.
      Choice list:['SquareKilometers', 'SquareMiles']

   classification_type: classificationType (str). Optional parameter.  Determines how density values will be classified into polygons.
      Choice list:['EqualArea', 'EqualInterval', 'GeometricInterval', 'NaturalBreaks', 'StandardDeviation']

   num_classes: numClasses (int). Optional parameter.  This value is used to divide the range of predicted values into distinct classes. The range of values in each class is determined by the classificationType parameter.

   output_name: outputName (str). Optional parameter.  Additional properties such as output feature service name.

   context: context (str). Optional parameter.  Additional settings such as processing extent and output spatial reference.

gis: Optional, the GIS on which this tool runs. If not specified, the active GIS is used.


Returns:
   result_layer - resultLayer as a str

See http://analysis6.arcgis.com:80/arcgis/rest/directories/arcgisoutput/tasks_GPServer/tasks/CalculateDensity.htm for additional help.
    """
    kwargs = locals()

    param_db = {
        "input_layer": (str, "inputLayer"),
        "field": (str, "field"),
        "cell_size": (float, "cellSize"),
        "cell_size_units": (str, "cellSizeUnits"),
        "radius": (float, "radius"),
        "radius_units": (str, "radiusUnits"),
        "bounding_polygon_layer": (str, "boundingPolygonLayer"),
        "area_units": (str, "areaUnits"),
        "classification_type": (str, "classificationType"),
        "num_classes": (int, "numClasses"),
        "output_name": (str, "outputName"),
        "context": (str, "context"),
        "result_layer": (str, "resultLayer"),
    }
    return_values = [
        {"name": "result_layer", "display_name": "resultLayer", "type": str},
    ]

    if gis is None:
        gis = arcgis.env.active_gis
    url = gis.properties.helperServices.analysis.url

    return _execute_gp_tool(gis, "CalculateDensity", kwargs, param_db, return_values, _use_async, url)


def summarize_nearby(sum_nearby_layer: str = None,
                     summary_layer: str = None,
                     near_type: str = """StraightLine""",
                     distances: str = """[]""",
                     units: str = """Meters""",
                     time_of_day: datetime = None,
                     time_zone_for_time_of_day: str = """GeoLocal""",
                     return_boundaries: bool = True,
                     sum_shape: bool = True,
                     shape_units: str = None,
                     summary_fields: str = """[]""",
                     group_by_field: str = None,
                     minority_majority: bool = False,
                     percent_shape: bool = False,
                     output_name: str = None,
                     context: str = None,
                     gis=None) -> tuple:
    """


The SummarizeNearby task finds features that are within a specified distance of features in the input layer. Distance can be measured as a straight-line distance, a drive-time distance (for example, within 10 minutes), or a drive distance (within 5 kilometers). Statistics are then calculated for the nearby features. For example:Calculate the total population within five minutes of driving time of a proposed new store location.Calculate the number of freeway access ramps within a one-mile driving distance of a proposed new store location to use as a measure of store accessibility.

Parameters:

   sum_nearby_layer: sumNearbyLayer (str). Required parameter.  Point, line, or polygon features from which distances will be measured to features in the summarizeLayer.

   summary_layer: summaryLayer (str). Required parameter.  Point, line, or polygon features. Features in this layer that are within the specified distance to features in the sumNearbyLayer will be summarized.

   near_type: nearType (str). Optional parameter.  Defines what kind of distance measurement you want to use to create areas around the nearbyLayer features.

   distances: distances (str). Required parameter.  An array of double values that defines the search distance for creating areas mentioned above

   units: units (str). Optional parameter.  The linear unit for distances parameter above. Eg. Miles, Kilometers, Minutes Seconds etc
      Choice list:['Meters', 'Kilometers', 'Feet', 'Yards', 'Miles', 'Seconds', 'Minutes', 'Hours']

   time_of_day: timeOfDay (datetime). Optional parameter.  For timeOfDay, set the time and day according to the number of milliseconds elapsed since the Unix epoc (January 1, 1970 UTC). When specified and if relevant for the nearType parameter, the traffic conditions during the time of the day will be considered.

   time_zone_for_time_of_day: timeZoneForTimeOfDay (str). Optional parameter.  Determines if the value specified for timeOfDay is specified in UTC or in a time zone that is local to the location of the origins.
      Choice list:['UTC', 'GeoLocal']

   return_boundaries: returnBoundaries (bool). Optional parameter.  If true, will return a result layer of areas that contain the requested summary information.  The resulting areas are defined by the specified nearType.  For example, if using a StraightLine of 5 miles, your result will contain areas with a 5 mile radius around the input features and specified summary information.If false, the resulting layer will return the same features as the input analysis layer with requested summary information.

   sum_shape: sumShape (bool). Optional parameter.  A boolean value that instructs the task to calculate count of points, length of lines or areas of polygons of the summaryLayer within each polygon in sumWithinLayer.

   shape_units: shapeUnits (str). Optional parameter.  Specify units to summarize the length or areas when sumShape is set to true. Units is not required to summarize points.
      Choice list:['Meters', 'Kilometers', 'Feet', 'Yards', 'Miles', 'Acres', 'Hectares', 'SquareMeters', 'SquareKilometers', 'SquareFeet', 'SquareYards', 'SquareMiles']

   summary_fields: summaryFields (str). Optional parameter.  A list of field names and statistical summary type that you wish to calculate for all features in the summaryLayer that are within each polygon in the sumWithinLayer . Eg: ["fieldname1 summary", "fieldname2 summary"]

   group_by_field: groupByField (str). Optional parameter.  Specify a field from the summaryLayer features to calculate statistics separately for each unique value of the field.

   minority_majority: minorityMajority (bool). Optional parameter.  This boolean parameter is applicable only when a groupByField is specified. If true, the minority (least dominant) or the majority (most dominant) attribute values within each group, within each boundary will be calculated.

   percent_shape: percentShape (bool). Optional parameter.  This boolean parameter is applicable only when a groupByField is specified. If set to true, the percentage of shape (eg. length for lines) for each unique groupByField value is calculated.

   output_name: outputName (str). Optional parameter.  Additional properties such as output feature service name.

   context: context (str). Optional parameter.  Additional settings such as processing extent and output spatial reference.

gis: Optional, the GIS on which this tool runs. If not specified, the active GIS is used.


Returns the following as a named tuple:
   result_layer - resultLayer as a str
   group_by_summary - groupBySummary as a str

See http://analysis6.arcgis.com:80/arcgis/rest/directories/arcgisoutput/tasks_GPServer/tasks/SummarizeNearby.htm for additional help.
    """
    kwargs = locals()

    param_db = {
        "sum_nearby_layer": (str, "sumNearbyLayer"),
        "summary_layer": (str, "summaryLayer"),
        "near_type": (str, "nearType"),
        "distances": (str, "distances"),
        "units": (str, "units"),
        "time_of_day": (datetime, "timeOfDay"),
        "time_zone_for_time_of_day": (str, "timeZoneForTimeOfDay"),
        "return_boundaries": (bool, "returnBoundaries"),
        "sum_shape": (bool, "sumShape"),
        "shape_units": (str, "shapeUnits"),
        "summary_fields": (str, "summaryFields"),
        "group_by_field": (str, "groupByField"),
        "minority_majority": (bool, "minorityMajority"),
        "percent_shape": (bool, "percentShape"),
        "output_name": (str, "outputName"),
        "context": (str, "context"),
        "result_layer": (str, "resultLayer"),
        "group_by_summary": (str, "groupBySummary"),
    }
    return_values = [
        {"name": "result_layer", "display_name": "resultLayer", "type": str},
        {"name": "group_by_summary", "display_name": "groupBySummary", "type": str},
    ]

    if gis is None:
        gis = arcgis.env.active_gis
    url = gis.properties.helperServices.analysis.url

    return _execute_gp_tool(gis, "SummarizeNearby", kwargs, param_db, return_values, _use_async, url)


def create_viewshed(input_layer: str = None,
                    dem_resolution: str = """Finest""",
                    maximum_distance: float = None,
                    max_distance_units: str = """Meters""",
                    observer_height: float = None,
                    observer_height_units: str = """Meters""",
                    target_height: float = None,
                    target_height_units: str = """Meters""",
                    generalize: bool = True,
                    output_name: str = None,
                    context: str = None,
                    gis=None) -> str:
    """




Parameters:

   input_layer: inputLayer (str). Required parameter.

   dem_resolution: demResolution (str). Optional parameter.
      Choice list:['Finest', '10m', '30m', '90m']

   maximum_distance: maximumDistance (float). Optional parameter.

   max_distance_units: maxDistanceUnits (str). Optional parameter.
      Choice list:['Meters', 'Kilometers', 'Feet', 'Yards', 'Miles']

   observer_height: observerHeight (float). Optional parameter.

   observer_height_units: observerHeightUnits (str). Optional parameter.
      Choice list:['Meters', 'Kilometers', 'Feet', 'Yards', 'Miles']

   target_height: targetHeight (float). Optional parameter.

   target_height_units: targetHeightUnits (str). Optional parameter.
      Choice list:['Meters', 'Kilometers', 'Feet', 'Yards', 'Miles']

   generalize: generalize (bool). Optional parameter.

   output_name: outputName (str). Optional parameter.

   context: context (str). Optional parameter.

gis: Optional, the GIS on which this tool runs. If not specified, the active GIS is used.


Returns:
   viewshed_layer - viewshedLayer as a str

See http://analysis6.arcgis.com:80/arcgis/rest/directories/arcgisoutput/tasks_GPServer/tasks/CreateViewshed.htm for additional help.
    """
    kwargs = locals()

    param_db = {
        "input_layer": (str, "inputLayer"),
        "dem_resolution": (str, "demResolution"),
        "maximum_distance": (float, "maximumDistance"),
        "max_distance_units": (str, "maxDistanceUnits"),
        "observer_height": (float, "observerHeight"),
        "observer_height_units": (str, "observerHeightUnits"),
        "target_height": (float, "targetHeight"),
        "target_height_units": (str, "targetHeightUnits"),
        "generalize": (bool, "generalize"),
        "output_name": (str, "outputName"),
        "context": (str, "context"),
        "viewshed_layer": (str, "viewshedLayer"),
    }
    return_values = [
        {"name": "viewshed_layer", "display_name": "viewshedLayer", "type": str},
    ]

    if gis is None:
        gis = arcgis.env.active_gis
    url = gis.properties.helperServices.analysis.url

    return _execute_gp_tool(gis, "CreateViewshed", kwargs, param_db, return_values, _use_async, url)


def find_similar_locations(input_layer: str = None,
                           search_layer: str = None,
                           analysis_fields: str = """[]""",
                           input_query: str = None,
                           number_of_results: int = 0,
                           output_name: str = None,
                           context: str = None,
                           gis=None) -> tuple:
    """




Parameters:

   input_layer: inputLayer (str). Required parameter.

   search_layer: searchLayer (str). Required parameter.

   analysis_fields: analysisFields (str). Required parameter.

   input_query: inputQuery (str). Optional parameter.

   number_of_results: numberOfResults (int). Optional parameter.

   output_name: outputName (str). Optional parameter.

   context: context (str). Optional parameter.

gis: Optional, the GIS on which this tool runs. If not specified, the active GIS is used.


Returns the following as a named tuple:
   similar_result_layer - similarResultLayer as a str
   process_info - processInfo as a str

See http://analysis6.arcgis.com:80/arcgis/rest/directories/arcgisoutput/tasks_GPServer/tasks/FindSimilarLocations.htm for additional help.
    """
    kwargs = locals()

    param_db = {
        "input_layer": (str, "inputLayer"),
        "search_layer": (str, "searchLayer"),
        "analysis_fields": (str, "analysisFields"),
        "input_query": (str, "inputQuery"),
        "number_of_results": (int, "numberOfResults"),
        "output_name": (str, "outputName"),
        "context": (str, "context"),
        "similar_result_layer": (str, "similarResultLayer"),
        "process_info": (str, "processInfo"),
    }
    return_values = [
        {"name": "similar_result_layer", "display_name": "similarResultLayer", "type": str},
        {"name": "process_info", "display_name": "processInfo", "type": str},
    ]

    if gis is None:
        gis = arcgis.env.active_gis
    url = gis.properties.helperServices.analysis.url

    return _execute_gp_tool(gis, "FindSimilarLocations", kwargs, param_db, return_values, _use_async, url)


def create_watersheds(input_layer: str = None,
                      search_distance: float = None,
                      search_units: str = """Meters""",
                      source_database: str = """FINEST""",
                      generalize: bool = True,
                      output_name: str = None,
                      context: str = None,
                      gis=None) -> tuple:
    """




Parameters:

   input_layer: inputLayer (str). Required parameter.

   search_distance: searchDistance (float). Optional parameter.

   search_units: searchUnits (str). Optional parameter.
      Choice list:['Meters', 'Kilometers', 'Feet', 'Yards', 'Miles']

   source_database: sourceDatabase (str). Optional parameter.
      Choice list:['FINEST', '30m', '90m']

   generalize: generalize (bool). Optional parameter.

   output_name: outputName (str). Optional parameter.

   context: context (str). Optional parameter.

gis: Optional, the GIS on which this tool runs. If not specified, the active GIS is used.


Returns the following as a named tuple:
   snap_pour_pts_layer - snapPourPtsLayer as a str
   watershed_layer - watershedLayer as a str

See http://analysis6.arcgis.com:80/arcgis/rest/directories/arcgisoutput/tasks_GPServer/tasks/CreateWatersheds.htm for additional help.
    """
    kwargs = locals()

    param_db = {
        "input_layer": (str, "inputLayer"),
        "search_distance": (float, "searchDistance"),
        "search_units": (str, "searchUnits"),
        "source_database": (str, "sourceDatabase"),
        "generalize": (bool, "generalize"),
        "output_name": (str, "outputName"),
        "context": (str, "context"),
        "snap_pour_pts_layer": (str, "snapPourPtsLayer"),
        "watershed_layer": (str, "watershedLayer"),
    }
    return_values = [
        {"name": "snap_pour_pts_layer", "display_name": "snapPourPtsLayer", "type": str},
        {"name": "watershed_layer", "display_name": "watershedLayer", "type": str},
    ]

    if gis is None:
        gis = arcgis.env.active_gis
    url = gis.properties.helperServices.analysis.url

    return _execute_gp_tool(gis, "CreateWatersheds", kwargs, param_db, return_values, _use_async, url)


def find_nearest(analysis_layer: str = None,
                 near_layer: str = None,
                 measurement_type: str = """StraightLine""",
                 max_count: int = 100,
                 search_cutoff: float = 2147483647,
                 search_cutoff_units: str = None,
                 time_of_day: datetime = None,
                 time_zone_for_time_of_day: str = """GeoLocal""",
                 output_name: str = None,
                 context: str = None,
                 gis=None) -> tuple:
    """


Measures the straight-line distance, driving distance, or driving time from features in the analysis layer to features in the near layer, and copies the nearest features in the near layer to a new layer. Returns a layer containing the nearest features and a line layer that links the start locations to their nearest locations.

Parameters:

   analysis_layer: analysisLayer (str). Required parameter.  For each feature in this layer, the task finds the nearest features from the nearLayer.

   near_layer: nearLayer (str). Required parameter.  The features from which the nearest locations are found.

   measurement_type: measurementType (str). Required parameter.  The nearest locations can be determined by measuring straight-line distance, driving distance, or driving time

   max_count: maxCount (int). Optional parameter.  The maximum number of near locations to find for each feature in analysisLayer.

   search_cutoff: searchCutoff (float). Optional parameter.  Limits the search range to this value

   search_cutoff_units: searchCutoffUnits (str). Optional parameter.  The units for the value specified as searchCutoff
      Choice list:['Miles', 'Yards', 'Feet', 'Meters', 'Kilometers', 'NauticalMiles']

   time_of_day: timeOfDay (datetime). Optional parameter.  When measurementType is DrivingTime, this value specifies the time of day to be used for driving time calculations based on traffic.

   time_zone_for_time_of_day: timeZoneForTimeOfDay (str). Optional parameter.
      Choice list:['UTC', 'GeoLocal']

   output_name: outputName (str). Optional parameter.  Additional properties such as output feature service name

   context: context (str). Optional parameter.  Additional settings such as processing extent and output spatial reference

gis: Optional, the GIS on which this tool runs. If not specified, the active GIS is used.


Returns the following as a named tuple:
   nearest_layer - nearestLayer as a str
   connecting_lines_layer - connectingLinesLayer as a str

See http://analysis6.arcgis.com:80/arcgis/rest/directories/arcgisoutput/tasks_GPServer/tasks/FindNearest.htm for additional help.
    """
    kwargs = locals()

    param_db = {
        "analysis_layer": (str, "analysisLayer"),
        "near_layer": (str, "nearLayer"),
        "measurement_type": (str, "measurementType"),
        "max_count": (int, "maxCount"),
        "search_cutoff": (float, "searchCutoff"),
        "search_cutoff_units": (str, "searchCutoffUnits"),
        "time_of_day": (datetime, "timeOfDay"),
        "time_zone_for_time_of_day": (str, "timeZoneForTimeOfDay"),
        "output_name": (str, "outputName"),
        "context": (str, "context"),
        "nearest_layer": (str, "nearestLayer"),
        "connecting_lines_layer": (str, "connectingLinesLayer"),
    }
    return_values = [
        {"name": "nearest_layer", "display_name": "nearestLayer", "type": str},
        {"name": "connecting_lines_layer", "display_name": "connectingLinesLayer", "type": str},
    ]

    if gis is None:
        gis = arcgis.env.active_gis
    url = gis.properties.helperServices.analysis.url

    return _execute_gp_tool(gis, "FindNearest", kwargs, param_db, return_values, _use_async, url)


def plan_routes(stops_layer: str = None,
                route_count: int = None,
                max_stops_per_route: int = None,
                route_start_time: datetime = None,
                start_layer: str = None,
                start_layer_route_id_field: str = None,
                return_to_start: bool = True,
                end_layer: str = None,
                end_layer_route_id_field: str = None,
                travel_mode: str = """Driving""",
                stop_service_time: float = 0,
                max_route_time: float = 525600,
                output_name: str = None,
                context: str = None,
                gis=None) -> tuple:
    """




Parameters:

   stops_layer: stopsLayer (str). Required parameter.

   route_count: routeCount (int). Required parameter.

   max_stops_per_route: maxStopsPerRoute (int). Required parameter.

   route_start_time: routeStartTime (datetime). Required parameter.

   start_layer: startLayer (str). Required parameter.

   start_layer_route_id_field: startLayerRouteIDField (str). Optional parameter.

   return_to_start: returnToStart (bool). Optional parameter.

   end_layer: endLayer (str). Optional parameter.

   end_layer_route_id_field: endLayerRouteIDField (str). Optional parameter.

   travel_mode: travelMode (str). Optional parameter.

   stop_service_time: stopServiceTime (float). Optional parameter.

   max_route_time: maxRouteTime (float). Optional parameter.

   output_name: outputName (str). Optional parameter.

   context: context (str). Optional parameter.

gis: Optional, the GIS on which this tool runs. If not specified, the active GIS is used.


Returns the following as a named tuple:
   routes_layer - routesLayer as a str
   assigned_stops_layer - assignedStopsLayer as a str
   unassigned_stops_layer - unassignedStopsLayer as a str

See http://analysis6.arcgis.com:80/arcgis/rest/directories/arcgisoutput/tasks_GPServer/tasks/PlanRoutes.htm for additional help.
    """
    kwargs = locals()

    param_db = {
        "stops_layer": (str, "stopsLayer"),
        "route_count": (int, "routeCount"),
        "max_stops_per_route": (int, "maxStopsPerRoute"),
        "route_start_time": (datetime, "routeStartTime"),
        "start_layer": (str, "startLayer"),
        "start_layer_route_id_field": (str, "startLayerRouteIDField"),
        "return_to_start": (bool, "returnToStart"),
        "end_layer": (str, "endLayer"),
        "end_layer_route_id_field": (str, "endLayerRouteIDField"),
        "travel_mode": (str, "travelMode"),
        "stop_service_time": (float, "stopServiceTime"),
        "max_route_time": (float, "maxRouteTime"),
        "output_name": (str, "outputName"),
        "context": (str, "context"),
        "routes_layer": (str, "routesLayer"),
        "assigned_stops_layer": (str, "assignedStopsLayer"),
        "unassigned_stops_layer": (str, "unassignedStopsLayer"),
    }
    return_values = [
        {"name": "routes_layer", "display_name": "routesLayer", "type": str},
        {"name": "assigned_stops_layer", "display_name": "assignedStopsLayer", "type": str},
        {"name": "unassigned_stops_layer", "display_name": "unassignedStopsLayer", "type": str},
    ]

    if gis is None:
        gis = arcgis.env.active_gis
    url = gis.properties.helperServices.analysis.url

    return _execute_gp_tool(gis, "PlanRoutes", kwargs, param_db, return_values, _use_async, url)


def trace_downstream(input_layer: str = None,
                     split_distance: float = None,
                     split_units: str = """Kilometers""",
                     max_distance: float = None,
                     max_distance_units: str = """Kilometers""",
                     bounding_polygon_layer: str = None,
                     source_database: str = None,
                     generalize: bool = True,
                     output_name: str = None,
                     context: str = None,
                     gis=None) -> str:
    """




Parameters:

   input_layer: inputLayer (str). Required parameter.

   split_distance: splitDistance (float). Optional parameter.

   split_units: splitUnits (str). Optional parameter.
      Choice list:['Meters', 'Kilometers', 'Feet', 'Yards', 'Miles']

   max_distance: maxDistance (float). Optional parameter.

   max_distance_units: maxDistanceUnits (str). Optional parameter.
      Choice list:['Meters', 'Kilometers', 'Feet', 'Yards', 'Miles']

   bounding_polygon_layer: boundingPolygonLayer (str). Optional parameter.

   source_database: sourceDatabase (str). Optional parameter.

   generalize: generalize (bool). Optional parameter.

   output_name: outputName (str). Optional parameter.

   context: context (str). Optional parameter.

gis: Optional, the GIS on which this tool runs. If not specified, the active GIS is used.


Returns:
   trace_layer - traceLayer as a str

See http://analysis6.arcgis.com:80/arcgis/rest/directories/arcgisoutput/tasks_GPServer/tasks/TraceDownstream.htm for additional help.
    """
    kwargs = locals()

    param_db = {
        "input_layer": (str, "inputLayer"),
        "split_distance": (float, "splitDistance"),
        "split_units": (str, "splitUnits"),
        "max_distance": (float, "maxDistance"),
        "max_distance_units": (str, "maxDistanceUnits"),
        "bounding_polygon_layer": (str, "boundingPolygonLayer"),
        "source_database": (str, "sourceDatabase"),
        "generalize": (bool, "generalize"),
        "output_name": (str, "outputName"),
        "context": (str, "context"),
        "trace_layer": (str, "traceLayer"),
    }
    return_values = [
        {"name": "trace_layer", "display_name": "traceLayer", "type": str},
    ]

    if gis is None:
        gis = arcgis.env.active_gis
    url = gis.properties.helperServices.analysis.url

    return _execute_gp_tool(gis, "TraceDownstream", kwargs, param_db, return_values, _use_async, url)


def connect_origins_to_destinations(origins_layer: str = None,
                                    destinations_layer: str = None,
                                    measurement_type: str = """DrivingTime""",
                                    origins_layer_route_id_field: str = None,
                                    destinations_layer_route_id_field: str = None,
                                    time_of_day: datetime = None,
                                    time_zone_for_time_of_day: str = """GeoLocal""",
                                    output_name: str = None,
                                    context: str = None,
                                    gis=None) -> tuple:
    """


Calculates routes between pairs of points.

Parameters:

   origins_layer: originsLayer (str). Required parameter.  The routes start from points in the origins layer.

   destinations_layer: destinationsLayer (str). Required parameter.  The routes end at points in the destinations layer.

   measurement_type: measurementType (str). Required parameter.  The routes can be determined by measuring travel distance or travel time along street network using different travel modes or by measuring straight line distance.

   origins_layer_route_id_field: originsLayerRouteIDField (str). Optional parameter.  The field in the origins layer containing the IDs that are used to match an origin with a destination.

   destinations_layer_route_id_field: destinationsLayerRouteIDField (str). Optional parameter.  The field in the destinations layer containing the IDs that are used to match an origin with a destination.

   time_of_day: timeOfDay (datetime). Optional parameter.  When measurementType is DrivingTime, this value specifies the time of day to be used for driving time calculations based on traffic. WalkingTime and TruckingTime measurementType do not support calculations based on traffic.

   time_zone_for_time_of_day: timeZoneForTimeOfDay (str). Optional parameter.  Determines if the value specified for timeOfDay is specified in UTC or in a time zone that is local to the location of the origins.
      Choice list:['GeoLocal', 'UTC']

   output_name: outputName (str). Optional parameter.  Additional properties such as output feature service name.

   context: context (str). Optional parameter.  Additional settings such as processing extent and output spatial reference.

gis: Optional, the GIS on which this tool runs. If not specified, the active GIS is used.


Returns the following as a named tuple:
   routes_layer - routesLayer as a str
   unassigned_origins_layer - unassignedOriginsLayer as a str
   unassigned_destinations_layer - unassignedDestinationsLayer as a str

See http://analysis6.arcgis.com:80/arcgis/rest/directories/arcgisoutput/tasks_GPServer/tasks/ConnectOriginsToDestinations.htm for additional help.
    """
    kwargs = locals()

    param_db = {
        "origins_layer": (str, "originsLayer"),
        "destinations_layer": (str, "destinationsLayer"),
        "measurement_type": (str, "measurementType"),
        "origins_layer_route_id_field": (str, "originsLayerRouteIDField"),
        "destinations_layer_route_id_field": (str, "destinationsLayerRouteIDField"),
        "time_of_day": (datetime, "timeOfDay"),
        "time_zone_for_time_of_day": (str, "timeZoneForTimeOfDay"),
        "output_name": (str, "outputName"),
        "context": (str, "context"),
        "routes_layer": (str, "routesLayer"),
        "unassigned_origins_layer": (str, "unassignedOriginsLayer"),
        "unassigned_destinations_layer": (str, "unassignedDestinationsLayer"),
    }
    return_values = [
        {"name": "routes_layer", "display_name": "routesLayer", "type": str},
        {"name": "unassigned_origins_layer", "display_name": "unassignedOriginsLayer", "type": str},
        {"name": "unassigned_destinations_layer", "display_name": "unassignedDestinationsLayer", "type": str},
    ]

    if gis is None:
        gis = arcgis.env.active_gis
    url = gis.properties.helperServices.analysis.url

    return _execute_gp_tool(gis, "ConnectOriginsToDestinations", kwargs, param_db, return_values, _use_async, url)



def choose_best_facilities(goal: str = """Allocate""",
                           demand_locations_layer: str = None,
                           demand: float = 1,
                           demand_field: str = None,
                           max_travel_range: float = 2147483647,
                           max_travel_range_field: str = None,
                           max_travel_range_units: str = """Minutes""",
                           travel_mode: str = None,
                           time_of_day: datetime = None,
                           time_zone_for_time_of_day: str = """GeoLocal""",
                           travel_direction: str = """FacilityToDemand""",
                           required_facilities_layer: str = None,
                           required_facilities_capacity: float = 2147483647,
                           required_facilities_capacity_field: str = None,
                           candidate_facilities_layer: str = None,
                           candidate_count: int = 1,
                           candidate_facilities_capacity: float = 2147483647,
                           candidate_facilities_capacity_field: str = None,
                           percent_demand_coverage: float = 100,
                           output_name: str = None,
                           context: str = None,
                           gis=None) -> tuple:
    """


This tool chooses the best locations for facilities by allocating locations that have demand for these facilities in a way that satisfies a given goal.

Parameters:

   goal: goal (str). Required parameter.  Specify the goal that must be satisfied when allocating demand locations to facilities.
      Choice list:['Allocate', 'MinimizeImpedance', 'MaximizeCoverage', 'MaximizeCapacitatedCoverage', 'PercentCoverage']

   demand_locations_layer: demandLocationsLayer (str). Required parameter.  A point layer specifying the locations that have demand for facilities

   demand: demand (float). Optional parameter.  The amount of demand available at every demand locations.

   demand_field: demandField (str). Optional parameter.  The field on the demandLocationsLayer representing the amount of demand available at each demand location.

   max_travel_range: maxTravelRange (float). Optional parameter.  Specify the maximum travel time or distance allowed between a demand location and the facility it is allocated to

   max_travel_range_field: maxTravelRangeField (str). Optional parameter.  The field on the demandLocationsLayer specifying the maximum travel time or distance allowed between a demand location and the facility it is allocated to. This parameter takes precedence when maxTravelRange parameter is also specified

   max_travel_range_units: maxTravelRangeUnits (str). Optional parameter.  The units for the maximum travel time or distance allowed between a demand location and the facility it is allocated to.
      Choice list:['Seconds', 'Minutes', 'Hours', 'Days', 'Meters', 'Kilometers', 'Feet', 'Yards', 'Miles']

   travel_mode: travelMode (str). Optional parameter.  Specify the mode of transportation for the analysis

   time_of_day: timeOfDay (datetime). Optional parameter.  Specify whether travel times should consider traffic conditions

   time_zone_for_time_of_day: timeZoneForTimeOfDay (str). Optional parameter.  Specify the time zone or zones for the timeOfDay parameter.
      Choice list:['GeoLocal', 'UTC']

   travel_direction: travelDirection (str). Optional parameter.  Specify whether to measure travel times or distances from facilities to demand locations or from demand locations to facilities.
      Choice list:['FacilityToDemand', 'DemandToFacility']

   required_facilities_layer: requiredFacilitiesLayer (str). Optional parameter.  A point layer specifying one or more locations that act as facilities by providing some kind of service. Facilities specified by this parameter are required to be part of the output solution and will be used before any facilities from the candidatesFacilitiesLayer when allocating demand locations.

   required_facilities_capacity: requiredFacilitiesCapacity (float). Optional parameter.  Specify how much demand every facility in the requiredFacilitiesLayer is capable of supplying.

   required_facilities_capacity_field: requiredFacilitiesCapacityField (str). Optional parameter.  A field on the requiredFacilitiesLayer representing how much demand each facility in the requiredFacilitiesLayer is capable of supplying. This parameter takes precedence when requiredFacilitiesCapacity parameter is also specified.

   candidate_facilities_layer: candidateFacilitiesLayer (str). Optional parameter.  A point layer specifying one or more locations that act as facilities by providing some kind of service. Facilities specified by this parameter are not required to be part of the output solution and will be used only after all the facilities from the candidatesFacilitiesLayer have been used when allocating demand locations.

   candidate_count: candidateCount (int). Optional parameter.  Specify the number of facilities to choose when allocating demand locations. If requiredFacilitiesLayer is specified, the number of facilities to choose should be equal to or greater than the count of locations in the requiredFacilitiesLayer.

   candidate_facilities_capacity: candidateFacilitiesCapacity (float). Optional parameter.  Specify how much demand every facility in the candidateFacilitiesLayer is capable of supplying.

   candidate_facilities_capacity_field: candidateFacilitiesCapacityField (str). Optional parameter.  A field on the candidateFacilitiesLayer representing how much demand each facility in the candidatesFacilitiesLayer is capable of supplying. This parameter takes precedence when candidateFacilitiesCapacity parameter is also specified.

   percent_demand_coverage: percentDemandCoverage (float). Optional parameter.  Specify the percentage of the total demand that you want the chosen and required facilities to capture.

   output_name: outputName (str). Optional parameter.  If provided, the task will create a feature service of the results. You define the name of the service. If outputName is not supplied, the task will return a feature collection.

   context: context (str). Optional parameter.  Context contains additional settings that affect task execution such as the extent of inputs.

gis: Optional, the GIS on which this tool runs. If not specified, the active GIS is used.


Returns the following as a named tuple:
   allocated_demand_locations_layer - allocatedDemandLocationsLayer as a str
   allocation_lines_layer - allocationLinesLayer as a str
   assigned_facilities_layer - assignedFacilitiesLayer as a str

See http://analysis6.arcgis.com:80/arcgis/rest/directories/arcgisoutput/tasks_GPServer/tasks/ChooseBestFacilities.htm for additional help.
    """
    kwargs = locals()

    param_db = {
        "goal": (str, "goal"),
        "demand_locations_layer": (str, "demandLocationsLayer"),
        "demand": (float, "demand"),
        "demand_field": (str, "demandField"),
        "max_travel_range": (float, "maxTravelRange"),
        "max_travel_range_field": (str, "maxTravelRangeField"),
        "max_travel_range_units": (str, "maxTravelRangeUnits"),
        "travel_mode": (str, "travelMode"),
        "time_of_day": (datetime, "timeOfDay"),
        "time_zone_for_time_of_day": (str, "timeZoneForTimeOfDay"),
        "travel_direction": (str, "travelDirection"),
        "required_facilities_layer": (str, "requiredFacilitiesLayer"),
        "required_facilities_capacity": (float, "requiredFacilitiesCapacity"),
        "required_facilities_capacity_field": (str, "requiredFacilitiesCapacityField"),
        "candidate_facilities_layer": (str, "candidateFacilitiesLayer"),
        "candidate_count": (int, "candidateCount"),
        "candidate_facilities_capacity": (float, "candidateFacilitiesCapacity"),
        "candidate_facilities_capacity_field": (str, "candidateFacilitiesCapacityField"),
        "percent_demand_coverage": (float, "percentDemandCoverage"),
        "output_name": (str, "outputName"),
        "context": (str, "context"),
        "allocated_demand_locations_layer": (str, "allocatedDemandLocationsLayer"),
        "allocation_lines_layer": (str, "allocationLinesLayer"),
        "assigned_facilities_layer": (str, "assignedFacilitiesLayer"),
    }
    return_values = [
        {"name": "allocated_demand_locations_layer", "display_name": "allocatedDemandLocationsLayer", "type": str},
        {"name": "allocation_lines_layer", "display_name": "allocationLinesLayer", "type": str},
        {"name": "assigned_facilities_layer", "display_name": "assignedFacilitiesLayer", "type": str},
    ]

    if gis is None:
        gis = arcgis.env.active_gis
    url = gis.properties.helperServices.analysis.url

    return _execute_gp_tool(gis, "ChooseBestFacilities", kwargs, param_db, return_values, _use_async, url)

