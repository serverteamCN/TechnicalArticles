"""
These functions are used to identify areas that meet a number of different criteria you specify. These criteria can be based
upon attribute queries (for example, parcels that are vacant) and spatial queries (for example, within 1 kilometer of a
river). The areas that are found can be selected from existing features (such as existing land parcels) or new features
can be created where all the requirements are met.

find_existing_locations searches for existing areas in a layer that meet a series of criteria.
derive_new_locations creates new areas from locations in your study area that meet a series of criteria.
find_similar_locations finds locations most similar to one or more reference locations based on criteria you specify.
choose_best_facilities choose the best locations for facilities by allocating locations that have demand for these
facilities in a way that satisfies a given goal.
create_viewshed creates areas that are visible based on locations you specify.
create_watersheds creates catchment areas based on locations you specify.
trace_downstream determines the flow paths in a downstream direction from the locations you specify
"""
import arcgis as _arcgis

def find_existing_locations(
        input_layers=[],
        expressions=[],
        output_name=None,
        context=None,
        gis=None):
    """
    The Find Existing Locations task selects features in the input layer that meet a query you specify.
    A query is made up of one or more expressions. There are two types of expressions: attribute and spatial.
    An example of an attribute expression is that a parcel must be vacant, which is an attribute of the Parcels layer
    (where STATUS = 'VACANT'). An example of a spatial expression is that the parcel must also be within a certain
    distance of a river (Parcels within a distance of 0.75 Miles from Rivers).

    Parameters
    ----------
    input_layers : Required list of strings
        A list of layers that will be used in the expressions parameter.
    expressions : Required string
        Specify a list of expressions. Please refer documentation at http://developers.arcgis.com for more information
        on creating expressions.
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
    return gis._tools.featureanalysis.find_existing_locations(
        input_layers,
        expressions,
        output_name,
        context)


def derive_new_locations(
        input_layers=[],
        expressions=[],
        output_name=None,
        context=None,
        gis=None):
    """
    The Derive New Locations task derives new features from the input layers that meet a query you specify. A query is
    made up of one or more expressions. There are two types of expressions: attribute and spatial. An example of an
    attribute expression is that a parcel must be vacant, which is an attribute of the Parcels layer
    (where STATUS = 'VACANT'). An example of a spatial expression is that the parcel must also be within a certain
    distance of a river (Parcels within a distance of 0.75 Miles from Rivers).The Derive New Locations task is very
    similar to the Find Existing Locations task, the main difference is that the result of Derive New Locations can
    contain partial features.In both tasks, the attribute expression  where and the spatial relationships within and
    contains return the same result. This is because these relationships return entire features.When intersects or
    withinDistance is used, Derive New Locations creates new features in the result. For example, when intersecting a
    parcel feature and a flood zone area that partially overlap each other, Find Existing Locations will return the
    entire parcel whereas Derive New Locations will return just the portion of the parcel that is within the flood zone.

    Parameters
    ----------
    input_layers : Required list of strings
        A list of layers that will be used in the expressions parameter.
    expressions : Required string
        Specify a list of expressions. Please refer documentation at http://developers.arcgis.com for more information
        on expressions.
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
    return gis._tools.featureanalysis.derive_new_locations(
        input_layers,
        expressions,
        output_name,
        context)


def find_similar_locations(
        input_layer,
        search_layer,
        analysis_fields=[],
        input_query=None,
        number_of_results=0,
        output_name=None,
        context=None,
        gis=None):
    """
    Finds the locations that are most similar to one or more reference locations based on criteria that you specify.

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
    gis = _arcgis.env.active_gis if gis is None else gis
    return gis._tools.featureanalysis.find_similar_locations(
        input_layer,
        search_layer,
        analysis_fields,
        input_query,
        number_of_results,
        output_name,
        context)

"""
def choose_best_facilities():
    '
    Choose the best locations for facilities by allocating locations that have demand for these facilities in a way that
    satisfies a given goal.
    '
    pass #TODO
"""

def create_viewshed(
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
        context=None,
        gis=None):
    """
    Creates areas that are visible based on locations you specify.

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

    gis :
        Optional, the GIS on which this tool runs. If not specified, the active GIS is used.


    Returns
    -------
    viewshed_layer : layer (FeatureCollection)
    """
    gis = _arcgis.env.active_gis if gis is None else gis
    return gis._tools.featureanalysis.create_viewshed(
        input_layer,
        dem_resolution,
        maximum_distance,
        max_distance_units,
        observer_height,
        observer_height_units,
        target_height,
        target_height_units,
        generalize,
        output_name,
        context)


def create_watersheds(
        input_layer,
        search_distance=None,
        search_units="Meters",
        source_database="FINEST",
        generalize=True,
        output_name=None,
        context=None,
        gis=None):
    """
    Creates catchment areas based on locations you specify.

    Parameters
    ----------
    input_layer : Required layer (see Feature Input in documentation)

    search_distance : Optional float

    search_units : Optional string

    source_database : Optional string

    generalize : Optional bool

    output_name : Optional string

    context : Optional string

    gis :
        Optional, the GIS on which this tool runs. If not specified, the active GIS is used.


    Returns
    -------
    dict with the following keys:
       "snap_pour_pts_layer" : layer (FeatureCollection)
       "watershed_layer" : layer (FeatureCollection)
    """
    gis = _arcgis.env.active_gis if gis is None else gis
    return gis._tools.featureanalysis.create_watersheds(
        input_layer,
        search_distance,
        search_units,
        source_database,
        generalize,
        output_name,
        context)


def trace_downstream(
        input_layer,
        split_distance=None,
        split_units="Kilometers",
        max_distance=None,
        max_distance_units="Kilometers",
        bounding_polygon_layer=None,
        source_database=None,
        generalize=True,
        output_name=None,
        context=None,
        gis=None):
    """
    Determine the flow paths in a downstream direction from the locations you specify.

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

    gis :
        Optional, the GIS on which this tool runs. If not specified, the active GIS is used.

    Returns
    -------
    trace_layer : layer (FeatureCollection)
    """
    gis = _arcgis.env.active_gis if gis is None else gis
    return gis._tools.featureanalysis.trace_downstream(
        input_layer,
        split_distance,
        split_units,
        max_distance,
        max_distance_units,
        bounding_polygon_layer,
        source_database,
        generalize,
        output_name,
        context)
