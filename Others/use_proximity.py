"""
These functions help you answer one of the most common questions posed in spatial analysis: "What is near what?"

connect_origins_to_destinations measures the travel time or distance between pairs of points.
create_buffers create areas of equal distance from features.
create_drive_time_areas finds areas around locations that can be reached within a time period.
find_nearest identifies those places that are the closest to known locations.
plan_routes determines the best way to route a fleet of vehicles to visit many stops.
"""
import arcgis as _arcgis
from arcgis._impl.common._utils import _date_handler

def connect_origins_to_destinations(
        origins_layer,
        destinations_layer,
        measurement_type="DrivingTime",
        origins_layer_route_id_field=None,
        destinations_layer_route_id_field=None,
        time_of_day=None,
        time_zone_for_time_of_day="GeoLocal",
        output_name=None,
        context=None,
        gis=None):
    """
    Calculates routes between pairs of points.

    Parameters
    ----------
    origins_layer : Required layer (see Feature Input in documentation)
        The routes start from points in the origins layer.
    destinations_layer : Required layer (see Feature Input in documentation)
        The routes end at points in the destinations layer.
    measurement_type : Required string
        The routes can be determined by measuring travel distance or travel time along street network using different
        travel modes or by measuring straight line distance.
    origins_layer_route_id_field : Optional string
        The field in the origins layer containing the IDs that are used to match an origin with a destination.
    destinations_layer_route_id_field : Optional string
        The field in the destinations layer containing the IDs that are used to match an origin with a destination.
    time_of_day : Optional datetime.datetime
        When measurementType is DrivingTime, this value specifies the time of day to be used for driving time
        calculations based on traffic. WalkingTime and TruckingTime measurementType do not support calculations
        based on traffic.
    time_zone_for_time_of_day : Optional string
        Determines if the value specified for timeOfDay is specified in UTC or in a time zone that is local to the
        location of the origins.
    output_name : Optional string
        Additional properties such as output feature service name.
    context : Optional string
        Additional settings such as processing extent and output spatial reference.
    gis :
        Optional, the GIS on which this tool runs. If not specified, the active GIS is used.

    Returns
    -------
    dict with the following keys:
       "routes_layer" : layer (FeatureCollection)
       "unassigned_origins_layer" : layer (FeatureCollection)
       "unassigned_destinations_layer" : layer (FeatureCollection)
    """
    gis = _arcgis.env.active_gis if gis is None else gis
    return gis._tools.featureanalysis.connect_origins_to_destinations(
        origins_layer,
        destinations_layer,
        measurement_type,
        origins_layer_route_id_field,
        destinations_layer_route_id_field,
        _date_handler(time_of_day),
        time_zone_for_time_of_day,
        output_name,
        context)


def create_buffers(
        input_layer,
        distances=[],
        field=None,
        units="Meters",
        dissolve_type="None",
        ring_type="Disks",
        side_type="Full",
        end_type="Round",
        output_name=None,
        context=None,
        gis=None):
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
    gis :
        Optional, the GIS on which this tool runs. If not specified, the active GIS is used.

    Returns
    -------
    buffer_layer : layer (FeatureCollection)
    """
    gis = _arcgis.env.active_gis if gis is None else gis
    return gis._tools.featureanalysis.create_buffers(
        input_layer,
        distances,
        field,
        units,
        dissolve_type,
        ring_type,
        side_type,
        end_type,
        output_name,
        context)


def create_drive_time_areas(
        input_layer,
        break_values=[5, 10, 15],
        break_units="Minutes",
        travel_mode="Driving",
        overlap_policy="Overlap",
        time_of_day=None,
        time_zone_for_time_of_day="GeoLocal",
        output_name=None,
        context=None,
        gis=None):
    """


    Parameters
    ----------
    input_layer : Required layer (see Feature Input in documentation)

    break_values : Optional list of floats

    break_units : Optional string

    travel_mode : Optional string

    overlap_policy : Optional string

    time_of_day : Optional datetime.datetime

    time_zone_for_time_of_day : Optional string

    output_name : Optional string
        Additional properties such as output feature service name.
    context : Optional string
        Additional settings such as processing extent and output spatial reference.
    gis :
        Optional, the GIS on which this tool runs. If not specified, the active GIS is used.

    Returns
    -------
    drive_time_areas_layer : layer (FeatureCollection)
    """
    gis = _arcgis.env.active_gis if gis is None else gis
    return gis._tools.featureanalysis.create_drive_time_areas(
        input_layer,
        break_values,
        break_units,
        travel_mode,
        overlap_policy,
        _date_handler(time_of_day),
        time_zone_for_time_of_day,
        output_name,
        context)


def find_nearest(
        analysis_layer,
        near_layer,
        measurement_type="StraightLine",
        max_count=100,
        search_cutoff=2147483647,
        search_cutoff_units=None,
        time_of_day=None,
        time_zone_for_time_of_day="GeoLocal",
        output_name=None,
        context=None,
        gis=None):
    """
    Measures the straight-line distance, driving distance, or driving time from features in the analysis layer to
    features in the near layer, and copies the nearest features in the near layer to a new layer. Returns a layer
    containing the nearest features and a line layer that links the start locations to their nearest locations.

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
    time_of_day : Optional datetime.datetime
        When measurementType is DrivingTime, this value specifies the time of day to be used for driving time
        calculations based on traffic.
    time_zone_for_time_of_day : Optional string

    output_name : Optional string
        Additional properties such as output feature service name
    context : Optional string
        Additional settings such as processing extent and output spatial reference
    gis :
        Optional, the GIS on which this tool runs. If not specified, the active GIS is used.

    Returns
    -------
    dict with the following keys:
       "nearest_layer" : layer (FeatureCollection)
       "connecting_lines_layer" : layer (FeatureCollection)
    """
    gis = _arcgis.env.active_gis if gis is None else gis
    return gis._tools.featureanalysis.find_nearest(
        analysis_layer,
        near_layer,
        measurement_type,
        max_count,
        search_cutoff,
        search_cutoff_units,
        _date_handler(time_of_day),
        time_zone_for_time_of_day,
        output_name,
        context)


def plan_routes(
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
        context=None,
        gis=None):
    """
    You provide a set of stops and the number of vehicles available to visit the stops, and Plan Routes determines how
    to efficiently assign the stops to the vehicles and route the vehicles to the stops.

    Use this tool to plan work for a mobile team of inspectors, appraisers, in-home support service providers, and
    others; deliver or pick up items from remote locations; or offer transportation services to people.

    Parameters
    ----------

    stops_layer : Required layer (see Feature Input in documentation)

    route_count : Required int

    max_stops_per_route : Required int

    route_start_time : Required datetime.datetime

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

    gis :
        Optional, the GIS on which this tool runs. If not specified, the active GIS is used.


    Returns
    -------
    dict with the following keys:
       "routes_layer" : layer (FeatureCollection)
       "assigned_stops_layer" : layer (FeatureCollection)
       "unassigned_stops_layer" : layer (FeatureCollection)
    """
    gis = _arcgis.env.active_gis if gis is None else gis
    return gis._tools.featureanalysis.plan_routes(
        stops_layer,
        route_count,
        max_stops_per_route,
        _date_handler(route_start_time),
        start_layer,
        start_layer_route_id_field,
        return_to_start,
        end_layer,
        end_layer_route_id_field,
        travel_mode,
        stop_service_time,
        max_route_time,
        output_name,
        context)
