"""
These functions help you explore the character of areas. Detailed demographic data and statistics are returned for your
chosen areas.

enrich_layer retrieves information about the people, places, and businesses in a specific area, or within a selected
travel time or distance from a location.
"""

import arcgis as _arcgis

def enrich_layer(input_layer,
                 data_collections=[],
                 analysis_variables=[],
                 country=None,
                 buffer_type=None,
                 distance=None,
                 units=None,
                 output_name=None,
                 context=None,
                 gis=None):
    """
    The enrich_layer function enriches your data by getting facts about the people, places, and businesses that surround
    your data locations. For example: What kind of people live here? What do people like to do in this area? What are
    their habits and lifestyles? What kind of businesses are there in this area?The result will be a new layer of input
    features that includes all demographic and geographic information from given data collections.

    Parameters
    ----------
    input_layer : Required layer (see Feature Input in documentation)
        Feature layer to enrich with new data
    data_collections : Optional list of strings
        Data collections you wish to add to your features.
    analysis_variables : Optional list of strings
        A subset of specific variables instead of dataCollections.
    country : Optional string
        The two character country code that specifies the country of the input features. Eg. US (United States),
        FR (France), GB (United Kingdom) etc.
    buffer_type : Optional string
        Area to be created around the point or line features for enrichment. Default is 1 Mile straight-line buffer
        radius.
    distance : Optional float
        A double value that defines the straight-line distance or time (when drivingTime is used).
    units : Optional string
        The unit (eg. Miles, Minutes) to be used with the distance value(s) specified in the distance parameter to
        calculate the area.
    output_name : Optional string
        Additional properties such as output feature service name.
    context : Optional string
        Additional settings such as processing extent and output spatial reference.
    gis :
        Optional, the GIS on which this tool runs. If not specified, the active GIS is used.

    Returns
    -------
    enriched_layer : layer (FeatureCollection)
    """

    gis = _arcgis.env.active_gis if gis is None else gis
    return gis._tools.featureanalysis.enrich_layer(
                 input_layer,
                 data_collections,
                 analysis_variables,
                 country,
                 buffer_type,
                 distance,
                 units,
                 output_name,
                 context)