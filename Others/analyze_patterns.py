"""
These functions help you identify, quantify, and visualize spatial patterns in your data.

calculate_density takes known quantities of some phenomenon and spreads these quantities across the map.
find_hot_spots identifies statistically significant clustering in the spatial pattern of your data.
interpolate_points predicts values at new locations based on measurements found in a collection of points.
"""

import arcgis as _arcgis

def calculate_density(
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
        context=None,
        gis=None):
    """
    The calculate_density function creates a density map from point or line features by spreading known quantities of
    some phenomenon (represented as attributes of the points or lines) across the map. The result is a layer of areas
    classified from least dense to most dense.

    Parameters
    ----------
    input_layer : Required layer (see Feature Input in documentation)
        The point or line features from which to calculate density.
    field : Optional string
        A numeric field name specifying the number of incidents at each location. If not specified, each location will
        be assumed to represent a single count.
    cell_size : Optional float
        This value is used to create a mesh of points where density values are calculated. The default is approximately
        1/1000th of the smaller of the width and height of the analysis extent as defined in the context parameter.
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
        This value is used to divide the range of predicted values into distinct classes. The range of values in each
        class is determined by the classificationType parameter.
    output_name : Optional string
        Additional properties such as output feature service name.
    context : Optional string
        Additional settings such as processing extent and output spatial reference.
    gis :
        Optional, the GIS on which this tool runs. If not specified, the active GIS is used.

    Returns
    -------
    result_layer : layer (FeatureCollection)
    """

    gis = _arcgis.env.active_gis if gis is None else gis
    return gis._tools.featureanalysis.calculate_density(
        input_layer,
        field,
        cell_size,
        cell_size_units,
        radius,
        radius_units,
        bounding_polygon_layer,
        area_units,
        classification_type,
        num_classes,
        output_name,
        context)


def find_hot_spots(
        analysis_layer,
        analysis_field=None,
        divided_by_field=None,
        bounding_polygon_layer=None,
        aggregation_polygon_layer=None,
        output_name=None,
        context=None,
        gis=None):
    """
    The Find Hot Spots function finds statistically significant clusters of incident points, weighted points, or
    weighted polygons. For incident data, the analysis field (weight) is obtained by aggregation.
    Output is a hot spot map.

    Parameters
    ----------
    gis : The GIS used for running this analysis
    analysis_layer : Required layer (see Feature Input in documentation)
        The point or polygon feature layer for which hot spots will be calculated.
    analysis_field : Optional string
        The numeric field in the AnalysisLayer that will be analyzed.
    divided_by_field : Optional string

    bounding_polygon_layer : Optional layer (see Feature Input in documentation)
        When the analysis layer is points and no AnalysisField is specified, you can provide polygons features that
        define where incidents could have occurred.
    aggregation_polygon_layer : Optional layer (see Feature Input in documentation)
        When the AnalysisLayer contains points and no AnalysisField is specified, you can provide polygon features into
        which the points will be aggregated and analyzed, such as administrative units.
    output_name : Optional string
        Additional properties such as output feature service name.
    context : Optional string
        Additional settings such as processing extent and output spatial reference.
    gis :
        Optional, the GIS on which this tool runs. If not specified, the active GIS is used.

    Returns
    -------
    dict with the following keys:
       "hot_spots_result_layer" : layer (FeatureCollection)
       "process_info" : list of messages
    """

    gis = _arcgis.env.active_gis if gis is None else gis
    return gis._tools.featureanalysis.find_hot_spots(
        analysis_layer,
        analysis_field,
        divided_by_field,
        bounding_polygon_layer,
        aggregation_polygon_layer,
        output_name,
        context)


def interpolate_points(
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
        context=None,
        gis=None):
    """
    The Interpolate Points function allows you to predict values at new locations based on measurements from a
    collection of points. The function takes point data with values at each point and returns areas classified by
    predicted values.

    Parameters
    ----------
    input_layer : Required layer (see Feature Input in documentation)
        The point layer whose features will be interpolated.
    field : Required string
        Name of the numeric field containing the values you wish to interpolate.
    interpolate_option : Optional string
        Integer value declaring your preference for speed versus accuracy, from 1 (fastest) to 9 (most accurate). More
        accurate predictions take longer to calculate.
    output_prediction_error : Optional bool
        If True, a polygon layer of standard errors for the interpolation predictions will be returned in the
        predictionError output parameter.
    classification_type : Optional string
        Determines how predicted values will be classified into areas.
    num_classes : Optional int
        This value is used to divide the range of interpolated values into distinct classes. The range of values in each
        class is determined by the classificationType parameter. Each class defines the boundaries of the result
        polygons.
    class_breaks : Optional list of floats
        If classificationType is Manual, supply desired class break values separated by spaces. These values define the
        upper limit of each class, so the number of classes will equal the number of entered values. Areas will not be
        created for any locations with predicted values above the largest entered break value. You must enter at least
        two values and no more than 32.
    bounding_polygon_layer : Optional layer (see Feature Input in documentation)
        A layer specifying the polygon(s) where you want values to be interpolated.
    predict_at_point_layer : Optional layer (see Feature Input in documentation)
        An optional layer specifying point locations to calculate prediction values. This allows you to make predictions
        at specific locations of interest.
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
       "prediction_error" : layer (FeatureCollection)
       "predicted_point_layer" : layer (FeatureCollection)
    """

    gis = _arcgis.env.active_gis if gis is None else gis
    return gis._tools.featureanalysis.interpolate_points(
        input_layer,
        field,
        interpolate_option,
        output_prediction_error,
        classification_type,
        num_classes,
        class_breaks,
        bounding_polygon_layer,
        predict_at_point_layer,
        output_name,
        context)
