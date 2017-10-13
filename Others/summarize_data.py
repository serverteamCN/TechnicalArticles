"""
These functions calculate total counts, lengths, areas, and basic descriptive statistics of features and their attributes
within areas or near other features.

aggregate_points calculates statistics about points that fall within specified areas.
summarize_nearby calculates statistics for features and their attributes that are within a specified distance.
summarize_within calculates statistics for area features and attributes that overlap each other.
"""
import arcgis as _arcgis
from arcgis._impl.common._utils import _date_handler

def aggregate_points(
                     point_layer,
                     polygon_layer,
                     keep_boundaries_with_no_points=True,
                     summary_fields=[],
                     group_by_field=None,
                     minority_majority=False,
                     percent_points=False,
                     output_name=None,
                     context=None,
                     gis=None):
    """
    Aggregate points task allows you to aggregate or count the total number of points that are distributed within
    specified areas or boundaries (polygons). You can also summarize Sum, Mean, Min, Max and Standard deviation
    calculations for attributes of the point layer to understand the general characteristics of aggregated points.

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
        This boolean parameter is applicable only when a groupByField is specified. If true, the minority
        (least dominant) or the majority (most dominant) attribute values within each group, within each boundary will
        be calculated.
    percent_points : Optional bool
        This boolean parameter is applicable only when a groupByField is specified. If set to true, the percentage count
        of points for each unique groupByField value is calculated.
    output_name : Optional string
        Additional properties such as output feature service name.
    context : Optional string
        Additional settings such as processing extent and output spatial reference.
    gis :
        Optional, the GIS on which this tool runs. If not specified, the active GIS is used.

    Returns
    -------
    dict with the following keys:
       "aggregated_layer" : layer (FeatureCollection)
       "group_summary" : layer (FeatureCollection)
    """
    gis = _arcgis.env.active_gis if gis is None else gis
    return gis._tools.featureanalysis.aggregate_points(
                     point_layer,
                     polygon_layer,
                     keep_boundaries_with_no_points,
                     summary_fields,
                     group_by_field,
                     minority_majority,
                     percent_points,
                     output_name,
                     context)



def summarize_nearby(sum_nearby_layer,
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
                     context=None,
                     gis=None):
    """
    The SummarizeNearby task finds features that are within a specified distance of features in the input layer.
    Distance can be measured as a straight-line distance, a drive-time distance (for example, within 10 minutes), or a
    drive distance (within 5 kilometers). Statistics are then calculated for the nearby features. For example:Calculate
    the total population within five minutes of driving time of a proposed new store location.Calculate the number of
    freeway access ramps within a one-mile driving distance of a proposed new store location to use as a measure of
    store accessibility.

    Parameters
    ----------
    sum_nearby_layer : Required layer (see Feature Input in documentation)
        Point, line, or polygon features from which distances will be measured to features in the summarizeLayer.
    summary_layer : Required layer (see Feature Input in documentation)
        Point, line, or polygon features. Features in this layer that are within the specified distance to features in
        the sumNearbyLayer will be summarized.
    near_type : Optional string
        Defines what kind of distance measurement you want to use to create areas around the nearbyLayer features.
    distances : Required list of floats
        An array of double values that defines the search distance for creating areas mentioned above
    units : Optional string
        The linear unit for distances parameter above. Eg. Miles, Kilometers, Minutes Seconds etc
    time_of_day : Optional datetime.datetime
        For timeOfDay, set the time and day according to the number of milliseconds elapsed since the Unix epoc
        (January 1, 1970 UTC). When specified and if relevant for the nearType parameter, the traffic conditions during
        the time of the day will be considered.
    time_zone_for_time_of_day : Optional string
        Determines if the value specified for timeOfDay is specified in UTC or in a time zone that is local to the
        location of the origins.
    return_boundaries : Optional bool
        If true, will return a result layer of areas that contain the requested summary information.  The resulting
        areas are defined by the specified nearType.  For example, if using a StraightLine of 5 miles, your result will
        contain areas with a 5 mile radius around the input features and specified summary information.If false, the
        resulting layer will return the same features as the input analysis layer with requested summary information.
    sum_shape : Optional bool
        A boolean value that instructs the task to calculate count of points, length of lines or areas of polygons of
        the summaryLayer within each polygon in sumWithinLayer.
    shape_units : Optional string
        Specify units to summarize the length or areas when sumShape is set to true. Units is not required to summarize
        points.
    summary_fields : Optional list of strings
        A list of field names and statistical summary type that you wish to calculate for all features in the
        summaryLayer that are within each polygon in the sumWithinLayer . Eg: ["fieldname1 summary",
        "fieldname2 summary"]
    group_by_field : Optional string
        Specify a field from the summaryLayer features to calculate statistics separately for each unique value of the
        field.
    minority_majority : Optional bool
        This boolean parameter is applicable only when a groupByField is specified. If true, the minority
        (least dominant) or the majority (most dominant) attribute values within each group, within each boundary will
        be calculated.
    percent_shape : Optional bool
        This boolean parameter is applicable only when a groupByField is specified. If set to true, the percentage of
        shape (eg. length for lines) for each unique groupByField value is calculated.
    output_name : Optional string
        Additional properties such as output feature service name.
    context : Optional string
        Additional settings such as processing extent and output spatial reference.
    gis :
        Optional, the GIS on which this tool runs. If not specified, the active GIS is used.

    Returns
    -------
    dict with the following keys:
       "result_layer" : layer (FeatureCollection)
       "group_by_summary" : layer (FeatureCollection)
    """
    gis = _arcgis.env.active_gis if gis is None else gis
    return gis._tools.featureanalysis.summarize_nearby(
                     sum_nearby_layer,
                     summary_layer,
                     near_type,
                     distances,
                     units,
                     _date_handler(time_of_day),
                     time_zone_for_time_of_day,
                     return_boundaries,
                     sum_shape,
                     shape_units,
                     summary_fields,
                     group_by_field,
                     minority_majority,
                     percent_shape,
                     output_name,
                     context)


def summarize_within(sum_within_layer,
                     summary_layer,
                     sum_shape=True,
                     shape_units=None,
                     summary_fields=[],
                     group_by_field=None,
                     minority_majority=False,
                     percent_shape=False,
                     output_name=None,
                     context=None,
                     gis=None):
    """
    The SummarizeWithin task helps you to summarize and find statistics on the point, line, or polygon features (or
    portions of these features) that are within the boundaries of polygons in another layer. For example:Given a layer
    of watershed boundaries and a layer of land-use boundaries by land-use type, calculate total acreage of land-use
    type for each watershed.Given a layer of parcels in a county and a layer of city boundaries, summarize the average
    value of vacant parcels within each city boundary.Given a layer of counties and a layer of roads, summarize the
    total mileage of roads by road type within each county.

    Parameters
    ----------
    sum_within_layer : Required layer (see Feature Input in documentation)
        A polygon feature layer or featurecollection. Features, or portions of features, in the summaryLayer (below)
        that fall within the boundaries of these polygons will be summarized.
    summary_layer : Required layer (see Feature Input in documentation)
        Point, line, or polygon features that will be summarized for each polygon in the sumWithinLayer.
    sum_shape : Optional bool
        A boolean value that instructs the task to calculate count of points, length of lines or areas of polygons of
        the summaryLayer within each polygon in sumWithinLayer.
    shape_units : Optional string
        Specify units to summarize the length or areas when sumShape is set to true. Units is not required to summarize
        points.
    summary_fields : Optional list of strings
        A list of field names and statistical summary type that you wish to calculate for all features in the
        summaryLayer that are within each polygon in the sumWithinLayer. Eg:["fieldname1 summary", "fieldname2 summary"]
    group_by_field : Optional string
        Specify a field from the summaryLayer features to calculate statistics separately for each unique attribute
        value.
    minority_majority : Optional bool
        This boolean parameter is applicable only when a groupByField is specified. If true, the minority
        (least dominant) or the majority (most dominant) attribute values within each group, within each boundary will
        be calculated.
    percent_shape : Optional bool
        This boolean parameter is applicable only when a groupByField is specified. If set to true, the percentage of
        shape (eg. length for lines) for each unique groupByField value is calculated.
    output_name : Optional string
        Additional properties such as output feature service name.
    context : Optional string
        Additional settings such as processing extent and output spatial reference.
    gis :
        Optional, the GIS on which this tool runs. If not specified, the active GIS is used.

    Returns
    -------
    dict with the following keys:
       "result_layer" : layer (FeatureCollection)
       "group_by_summary" : layer (FeatureCollection)
    """
    gis = _arcgis.env.active_gis if gis is None else gis
    return gis._tools.featureanalysis.summarize_within(
                     sum_within_layer,
                     summary_layer,
                     sum_shape,
                     shape_units,
                     summary_fields,
                     group_by_field,
                     minority_majority,
                     percent_shape,
                     output_name,
                     context)


def join_features(target_layer,
                  join_layer,
                  spatial_relationship = None,
                  spatial_relationship_distance = None,
                  spatial_relationship_distance_units = None,
                  attribute_relationship = None,
                  join_operation = """JoinOneToOne""",
                  summary_fields = None,
                  output_name = None,
                  context = None,
                  gis=None):
    """
    Parameters:

       target_layer: targetLayer (str). Required parameter.

       join_layer: joinLayer (str). Required parameter.

       spatial_relationship: spatialRelationship (str). Optional parameter.
          Choice list:['intersects', 'withindistance', 'completelycontains', 'completelywithin', 'within', 'contains', 'identicalto']

       spatial_relationship_distance: spatialRelationshipDistance (float). Optional parameter.

       spatial_relationship_distance_units: spatialRelationshipDistanceUnits (str). Optional parameter.
          Choice list:['Meters', 'Kilometers', 'Feet', 'Yards', 'Miles', 'NauticalMiles']

       attribute_relationship: attributeRelationship (str). Optional parameter.

       join_operation: joinOperation (str). Optional parameter.
          Choice list:['JoinOneToOne', 'JoinOneToMany']

       summary_fields: summaryFields (str). Optional parameter.

       output_name: outputName (str). Optional parameter.

       context: context (str). Optional parameter.

        gis: Optional, the GIS on which this tool runs. If not specified, the active GIS is used.


    Returns:
       output_layer - outputLayer as a str

    See http://localhost:6080/arcgis/rest/directories/arcgisoutput/tasks_GPServer/tasks/JoinFeatures.htm for additional help.
    """
    gis = _arcgis.env.active_gis if gis is None else gis
    return gis._tools.featureanalysis.join_features(
        target_layer,
        join_layer,
        spatial_relationship,
        spatial_relationship_distance,
        spatial_relationship_distance_units,
        attribute_relationship,
        join_operation,
        summary_fields,
        output_name,
        context)

