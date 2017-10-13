"""
In the GIS, entities located in space with a set of properties can be represented as features. This module has the types
to represent features and collection of features.
"""
import copy
import json
import os
import re
import tempfile
import uuid

from arcgis._impl.common._mixins import PropertyMap
from arcgis._impl.common._spatial import json_to_featureclass
from arcgis._impl.common._utils import _date_handler
from arcgis.geometry import BaseGeometry, Point, MultiPoint, Polyline, Polygon, Geometry, SpatialReference
from arcgis.gis import Layer

try:
    import arcpy
    HASARCPY = True
except ImportError:
    HASARCPY = False

class Feature(object):
    """ Entities located in space with a set of properties can be represented as features. """
    _geom = None
    _json = None
    _dict = None
    _geom_type = None
    _attributes = None
    _wkid = None

    # ----------------------------------------------------------------------
    def __init__(self, geometry=None, attributes=None):
        """Constructor"""
        self._dict = {

        }
        if geometry is not None:
            self._dict["geometry"] = geometry
        if attributes is not None:
            self._dict["attributes"] = attributes

    # ----------------------------------------------------------------------
    def set_value(self, field_name, value):
        """ sets an attribute value for a given field name """
        if field_name in self.fields:
            if value is not None:
                self._dict['attributes'][field_name] = value
                self._json = json.dumps(self._dict, default=_date_handler)
            else:
                pass
        elif field_name.upper() in ['SHAPE', 'SHAPE@', "GEOMETRY"]:
            if isinstance(value, BaseGeometry):
                if isinstance(value, Point):
                    self._dict['geometry'] = {
                        "x": value['x'],
                        "y": value['y']
                    }
                elif isinstance(value, MultiPoint):
                    self._dict['geometry'] = {
                        "points": value['points']
                    }
                elif isinstance(value, Polyline):
                    self._dict['geometry'] = {
                        "paths": value['paths']
                    }
                elif isinstance(value, Polygon):
                    self._dict['geometry'] = {
                        "rings": value['rings']
                    }
                else:
                    return False
                self._json = json.dumps(self._dict, default=_date_handler)
        else:
            return False
        return True

    # ----------------------------------------------------------------------
    def get_value(self, field_name):
        """ returns a value for a given field name """
        if field_name in self.fields:
            return self._dict['attributes'][field_name]
        elif field_name.upper() in ['SHAPE', 'SHAPE@', "GEOMETRY"]:
            return self._dict['geometry']
        return None

    # ----------------------------------------------------------------------
    @property
    def as_dict(self):
        """returns the feature as a dictionary"""
        return self._dict

    # ----------------------------------------------------------------------
    @property
    def as_row(self):
        """ converts a feature to a list for insertion into an insert cursor
            Output:
               [row items], [field names]
               returns a list of fields and the row object
        """
        fields = self.fields
        row = [""] * len(fields)
        for key, val in self._attributes.items():
            row[fields.index(key)] = val
            del val
            del key
        if self.geometry is not None:
            row.append(self.geometry)
            fields.append("SHAPE@")
        return row, fields

    # ----------------------------------------------------------------------
    @property
    def geometry(self):
        """returns the feature geometry"""
        if self._geom is None:
            if 'geometry' in self._dict.keys():
                self._geom = self._dict['geometry']
            else:
                return None
        return self._geom

    @geometry.setter
    def geometry(self, value):
        """gets/sets a feature's geometry"""
        self._geom = value
        self._dict['geometry'] = value

    # ----------------------------------------------------------------------
    @property
    def attributes(self):
        """returns the feature attributes"""
        if self._attributes is None and 'attributes' in self._dict:
            self._attributes = self._dict['attributes']
        return self._attributes

    @attributes.setter
    def attributes(self, value):
        """gets/sets a feature's attributes"""
        self._attributes = value
        self._dict['attributes'] = value

    # ----------------------------------------------------------------------
    @property
    def fields(self):
        """ returns a list of feature fields """
        if 'attributes' in self._dict:
            self._attributes = self._dict['attributes']
            return list(self._attributes.keys())
        else:
            return []

    # ----------------------------------------------------------------------
    @property
    def geometry_type(self):
        """ returns the feature's geometry type """
        if self._geom_type is None:
            if self.geometry is not None:
                self._geom_type = self.geometry.type
            else:
                self._geom_type = "Table"
        return self._geom_type

    # ----------------------------------------------------------------------
    @classmethod
    def from_json(cls, json_str):
        """returns a feature from a JSON string"""
        feature = json.loads(json_str)
        geom = feature['geometry'] if 'geometry' in feature else None
        attribs = feature['attributes'] if 'attributes' in feature else None
        return cls(geom, attribs)

    # ----------------------------------------------------------------------
    @classmethod
    def from_dict(cls, feature):
        """returns a feature from a dict"""
        geom = feature['geometry'] if 'geometry' in feature else None
        attribs = feature['attributes'] if 'attributes' in feature else None
        return cls(geom, attribs)
    # ----------------------------------------------------------------------
    def __str__(self):
        """"""
        return json.dumps(self.as_dict, default=_date_handler)

    __repr__ = __str__


class FeatureSet(object):
    """
    A set of features with information about their fields, field aliases, geometry type, spatial reference etc.

    FeatureSets are commonly used as input/output with several Geoprocessing
    Tools, and can be the obtained through the query() methods of feature layers.
    A FeatureSet can be combined with a layer definition to compose a FeatureCollection.

    FeatureSet contains Feature objects, including the values for the
    fields requested by the user. For layers, if you request geometry
    information, the geometry of each feature is also returned in the
    FeatureSet. For tables, the FeatureSet does not include geometries.

    If a Spatial Reference is not specified at the FeatureSet level, the
    FeatureSet will assume the SpatialReference of its first feature. If
    the SpatialReference of the first feature is also not specified, the
    spatial reference will be UnknownCoordinateSystem.
    """
    _fields = None
    _features = None
    _has_z = None
    _has_m = None
    _geometry_type = None
    _spatial_reference = None
    _object_id_field_name = None
    _global_id_field_name = None
    _display_field_name = None
    _allowed_geom_types = ["esriGeometryPoint", "esriGeometryMultipoint", "esriGeometryPolyline",
                           "esriGeometryPolygon", "esriGeometryEnvelope"]

    # ----------------------------------------------------------------------
    def __init__(self,
                 features,
                 fields=None,
                 has_z=False,
                 has_m=False,
                 geometry_type=None,
                 spatial_reference=None,
                 display_field_name=None,
                 object_id_field_name=None,
                 global_id_field_name=None):
        """Constructor"""
        self._fields = fields

        self._has_z = has_z
        self._has_m = has_m
        self._geometry_type = geometry_type
        self._spatial_reference = spatial_reference
        self._display_field_name = display_field_name
        self._object_id_field_name = object_id_field_name
        self._global_id_field_name = global_id_field_name

        # conversion of different inputs to a common list of feature objects
        if isinstance(features, str):
            # convert the featuresclass to a list of features
            features = self._fc_to_features(dataset=features)
            if features is None:
                raise AttributeError("Feature class could not be converted to a feature set")
        elif isinstance(features, list) and len(features) > 0:
            feature = features[0]
            if isinstance(feature, Feature):
                pass
                # features passed in as a list of Feature objects

                # if "attributes" in feature.as_dict:
                #     if "geometry" in feature.as_dict:
                #         features = [Feature(feat.as_dict['geometry'], feat.as_dict['attributes']) for feat in features]
                #     else:
                #         features = [Feature(None, feat.as_dict['attributes']) for feat in features]
                # elif "geometry" in feature.as_dict:
                #     features = [Feature(feat.as_dict['geometry'], None) for feat in features]
            elif isinstance(feature, dict):
                # features passed in as a list of dicts
                if "attributes" in feature:
                    if "geometry" in feature:
                        features = [Feature(feat['geometry'], feat['attributes']) for feat in features]
                    else:
                        features = [Feature(None, feat['attributes']) for feat in features]
                elif "geometry" in feature:
                    features = [Feature(feat['geometry'], None) for feat in features]
            else:
                raise AttributeError("FeatureSet requires a list of features (as dicts or Feature objects)")

        self._features = features
        if len(features) > 0:
            feat_geom = None
            feature = features[0]

            if "geometry" in feature.as_dict: # can construct features out of tables with just attributes, no geometry
                feat_geom = feature.geometry
            elif isinstance(feature, dict):
                if "geometry" in feature:
                    feat_geom = feature['geometry']

            if feat_geom is not None:
                if spatial_reference is None:
                    if 'spatialReference' in feat_geom:
                        self._spatialReference = feat_geom['spatialReference']

                if isinstance(feat_geom, Geometry):
                    geometry = feat_geom
                else:
                    geometry = Geometry(feat_geom)

                if geometry_type is None:
                    if isinstance(geometry, Polyline):
                        self._geometryType = "esriGeometryPolyline"
                    elif isinstance(geometry, Polygon):
                        self._geometryType = "esriGeometryPolygon"
                    elif isinstance(geometry, Point):
                        self._geometryType = "esriGeometryPoint"
                    elif isinstance(geometry, MultiPoint):
                        self._geometryType = "esriGeometryMultipoint"
                # else:
                #     raise AttributeError("Invalid geometry type") # Dont raise this error as input can be tables without geometries

            # Try to find the object ID field if not specified
            if self._object_id_field_name is None:
                # check to see if features a dict or feature object
                if isinstance(feature, Feature):
                    # Look for OBJECTID first, if it does not exist, look for FID
                    if self._fields is None:
                        self._fields = feature.fields  # get fields from first feature if not set
                    for field in feature.fields:
                        if re.search("^{0}$".format("OBJECTID"), field, re.IGNORECASE):
                            self._objectIdFieldName = field
                            break
                    for field in feature.fields:
                        if re.search("^{0}$".format("FID"), field, re.IGNORECASE):
                            self._objectIdFieldName = field
                            break
                else:
                    for field, _ in feature.items():
                        if re.search("^{0}$".format("OBJECTID"), field, re.IGNORECASE):
                            self._object_id_field_name = field
                            break
                    for field, _ in feature.items():
                        if re.search("^{0}$".format("FID"), field, re.IGNORECASE):
                            self._object_id_field_name = field
                            break

    # ----------------------------------------------------------------------
    def __str__(self):
        """returns object as string"""
        return json.dumps(self.value, default=_date_handler)

    __repr__ = __str__

    # noinspection PyUnresolvedReferences
    @staticmethod
    def _fc_to_features(dataset):
        """
           converts a dataset to a list of feature objects, if ArcPy is available
           Input:
              dataset - path to table or feature class
           Output:
              list of feature objects
        """
        try:
            import arcpy
            arcpy_found = True
        except:
            arcpy_found = False
            raise AttributeError("ArcPy is required to create a feature set from a feature class")
        if arcpy_found:
            if not arcpy.Exists(dataset=dataset):
                raise AttributeError("Error creating FeatureSet: {0} does not exist".format(dataset))

            desc = arcpy.Describe(dataset)
            fields = [field.name for field in arcpy.ListFields(dataset) if field.type not in ['Geometry']]
            date_fields = [field.name for field in arcpy.ListFields(dataset) if field.type == 'Date']
            non_geom_fields = copy.deepcopy(fields)
            features = []
            if hasattr(desc, "shapeFieldName"):
                fields.append("SHAPE@JSON")
            del desc
            with arcpy.da.SearchCursor(dataset, fields) as rows:
                for row in rows:
                    row = list(row)
                    for date_field in date_fields:
                        if row[fields.index(date_field)] is not None:
                            row[fields.index(date_field)] = int((_date_handler(row[fields.index(date_field)])))
                    template = {
                        "attributes": dict(zip(non_geom_fields, row))
                    }
                    if "SHAPE@JSON" in fields:
                        template['geometry'] = \
                            json.loads(row[fields.index("SHAPE@JSON")])

                    features.append(
                        Feature.from_dict(template)
                    )
                    del row
            return features
        return None
        # ----------------------------------------------------------------------

    @property
    def value(self):
        """returns object as dictionary"""
        val = {
            "features": [f.as_dict for f in self._features]
        }

        if self._object_id_field_name is not None:
            val["objectIdFieldName"] = self._object_id_field_name
        if self._display_field_name is not None:
            val["displayFieldName"] = self._display_field_name
        if self._global_id_field_name is not None:
            val["globalIdFieldName"] = self._global_id_field_name
        if self._spatial_reference is not None:
            val["spatialReference"] = self._spatial_reference
        if self._geometry_type is not None:
            val["geometryType"] = self._geometry_type
        if self._has_z:
            val["hasZ"] = self._has_z
        if self._has_m:
            val["hasM"] = self._has_m
        if self._fields is not None:
            val["fields"] = self._fields

        return val

        # return {
        #    "objectIdFieldName" : self._objectIdFieldName,
        #    "displayFieldName" : self._displayFieldName,
        #    "globalIdFieldName" : self._globalIdFieldName,
        #    "geometryType" : self._geometryType,
        #    "spatialReference" : self._spatialReference,
        #    "hasZ" : self._hasZ,
        #    "hasM" : self._hasM,
        #    "fields" : self._fields,
        #    "features" : [f.as_dict for f in self._features]
        # }

    # ----------------------------------------------------------------------
    @property
    def to_json(self):
        """converts the object to JSON"""
        return json.dumps(self.value, default=_date_handler)

    def to_dict(self):
        """converts the object to Python dictionary"""
        return self.value

    @property
    def df(self):
        """converts the FeatureSet to a Pandas dataframe. Requires pandas"""
        try:
            try:
                import arcpy
                arcpy_found = True
            except:
                arcpy_found = False
            from pandas.io.json import json_normalize
            from arcgis.features import SpatialDataFrame
            if self.geometry_type is not None:
                if self.spatial_reference and \
                   'wkt' in self.spatial_reference.keys():
                    sr = SpatialReference(self.spatial_reference)
                elif self.spatial_reference and \
                     'wkid' in self.spatial_reference:
                    sr = SpatialReference(self.spatial_reference)
                else:
                    sr = None
                geoms = []
                attributes = []
                for feat in self.features:
                    attributes.append(feat.attributes)
                    geoms.append(Geometry(feat.geometry))
                    del feat
                df = json_normalize(attributes)
                df.columns = df.columns.str.replace('attributes.', '')
                return SpatialDataFrame(df, geometry=geoms, sr=sr)
            else:
                #df = pandas.DataFrame.from_dict([f.attributes for f in fs.features])
                df = json_normalize(self.value['features'])
                df.columns = df.columns.str.replace('attributes.', '')
                if self._object_id_field_name is not None:
                    df.set_index([self._object_id_field_name], inplace=True)
                else:
                    if 'OBJECTID' in df.columns:
                        df.set_index(['OBJECTID'], inplace=True)
                    elif 'FID' in df.columns:
                        df.set_index(['FID'], inplace=True)
                return df
        except ImportError:
            raise ImportError("pandas not found, please install it")

    # ----------------------------------------------------------------------
    def __iter__(self):
        """featureset iterator on features in feature set"""
        for feature in self._features:
            yield feature

    # ----------------------------------------------------------------------
    def __len__(self):
        """returns the number of features in feature set"""
        return len(self._features)

    # ----------------------------------------------------------------------
    @staticmethod
    def from_json(json_str):
        """returns a featureset from a JSON string"""
        return FeatureSet.from_dict(json.loads(json_str))

    @staticmethod
    def from_dataframe(df):
        """returns a featureset from a Pandas' Data or Spatial DataFrame"""
        from ._data.geodataset import SpatialDataFrame
        import pandas as pd
        try:
            import arcpy
            HASARCPY = True
        except ImportError:
            HASARCPY = False
        features = []
        index = 0
        sr = None
        if isinstance(df, SpatialDataFrame):
            df_rows = df.copy()
            del df_rows['SHAPE']
            geoms = df['SHAPE'].tolist()
            sr = df.sr
        elif isinstance(df, pd.DataFrame):
            geoms = []
            df_rows = df.copy().to_dict('records')
        else:
            raise ValueError("Invalid input type")
        index = 0
        for row in df_rows.to_dict('records'):
            if len(geoms) > 0:
                features.append(
                    {
                        "geometry": json.loads(json.dumps(geoms[0])),
                        "attributes": row
                    })
            else:
                features.append(
                    {
                        "attributes": row
                    })
            index += 1
        fs =  FeatureSet.from_dict(featureset_dict={'features': features})

        if sr is not None:
            fs.spatial_reference = sr

        return fs

    # ----------------------------------------------------------------------
    @staticmethod
    def from_dict(featureset_dict):
        """returns a featureset from a dict"""

        features = []
        if 'fields' in featureset_dict:
            fields = featureset_dict['fields']
        else:
            fields = {'fields': []}
        if 'features' in featureset_dict:
            for feat in featureset_dict['features']:
                features.append(Feature.from_dict(feat))
        return FeatureSet(
            features=features, fields=fields,
            has_z=featureset_dict['hasZ'] if 'hasZ' in featureset_dict else False,
            has_m=featureset_dict['hasM'] if 'hasM' in featureset_dict else False,
            geometry_type=featureset_dict['geometryType'] if 'geometryType' in featureset_dict else None,
            object_id_field_name=featureset_dict['objectIdFieldName'] if 'objectIdFieldName' in featureset_dict else None,
            global_id_field_name=featureset_dict['globalIdFieldName'] if 'globalIdFieldName' in featureset_dict else None,
            display_field_name=featureset_dict['displayFieldName'] if 'displayFieldName' in featureset_dict else None,
            spatial_reference=featureset_dict['spatialReference'] if 'spatialReference' in featureset_dict else None)

    # ----------------------------------------------------------------------
    @property
    def spatial_reference(self):
        """gets the featureset's spatial reference"""
        return self._spatial_reference

    # ----------------------------------------------------------------------
    @spatial_reference.setter
    def spatial_reference(self, value):
        """sets the featureset's spatial reference"""
        if isinstance(value, SpatialReference):
            self._spatial_reference = value
        elif isinstance(value, int):
            self._spatial_reference = SpatialReference(wkid=value)
        elif isinstance(value, str) and \
                str(value).isdigit():
            self._spatial_reference = SpatialReference(wkid=int(value))
        else:
            self._spatial_reference = SpatialReference(value)


    # ----------------------------------------------------------------------
    @property
    def has_z(self):
        """gets/sets the Z-property"""
        return self._has_z

    # ----------------------------------------------------------------------
    @has_z.setter
    def has_z(self, value):
        """gets/sets the Z-property"""
        if isinstance(value, bool):
            self._has_z = value

    # ----------------------------------------------------------------------
    @property
    def has_m(self):
        """gets/set the M-property"""
        return self._has_m

    # ----------------------------------------------------------------------
    @has_m.setter
    def has_m(self, value):
        """gets/set the M-property"""
        if isinstance(value, bool):
            self._has_m = value

    # ----------------------------------------------------------------------
    @property
    def geometry_type(self):
        """gets/sets the geometry Type"""
        return self._geometry_type

    # ----------------------------------------------------------------------
    @geometry_type.setter
    def geometry_type(self, value):
        """gets/sets the geometry Type"""
        if value in self._allowed_geom_types:
            self._geometry_type = value

    # ----------------------------------------------------------------------
    @property
    def object_id_field_name(self):
        """gets/sets the object id field"""
        return self._object_id_field_name

    # ----------------------------------------------------------------------
    @object_id_field_name.setter
    def object_id_field_name(self, value):
        """gets/sets the object id field"""
        self._object_id_field_name = value

    # ----------------------------------------------------------------------
    @property
    def global_id_field_name(self):
        """gets/sets the globalIdFieldName"""
        return self._global_id_field_name

    # ----------------------------------------------------------------------
    @global_id_field_name.setter
    def global_id_field_name(self, value):
        """gets/sets the globalIdFieldName"""
        self._global_id_field_name = value

    # ----------------------------------------------------------------------
    @property
    def display_field_name(self):
        """gets/sets the displayFieldName"""
        return self._display_field_name

    # ----------------------------------------------------------------------
    @display_field_name.setter
    def display_field_name(self, value):
        """gets/sets the displayFieldName"""
        self._display_field_name = value

    # ----------------------------------------------------------------------
    def save(self, save_location, out_name):
        """
        Saves a featureset object to a feature class
        Input:
           saveLocation - output location of the data
           outName - name of the table the data will be saved to
                Types:
                    *.csv - CSV file returned
                    *.json - text file with json
                    * If no extension, a shapefile if the path is a
                        folder, a featureclass if the path is a GDB

        """
        _, file_extension = os.path.splitext(out_name)
        if file_extension.lower() not in ['.csv', '.json'] and \
           HASARCPY == False:
            raise ImportError("ArcPy is required to export a feature class.")
        import sys
        if sys.version_info[0] == 2:
            access = 'wb+'
            kwargs = {}
        else:
            access = 'wt+'
            kwargs = {'newline': ''}

        if file_extension == ".csv":
            res = os.path.join(save_location, out_name)
            with open(res, access, **kwargs) as csv_file:
                import csv
                csv_writer = csv.writer(csv_file)
                fields = []
                # write the headers to the csv
                for field in self.fields:
                    fields.append(field['name'])
                csv_writer.writerow(fields)

                new_row = []
                # Loop through the results and save each to a row
                for feature in self:
                    new_row = []
                    for field in self.fields:
                        new_row.append(feature.get_value(field['name']))
                    csv_writer.writerow(new_row)
                csv_file.close()
            del csv_file
        elif file_extension == ".json":
            res = os.path.join(save_location, out_name)
            with open(res, access) as writer:

                json.dump(self.value, writer, sort_keys=True, indent=4, ensure_ascii=False)
                writer.flush()
                writer.close()
            del writer

        else:
            temp_dir = tempfile.gettempdir()
            temp_file = os.path.join(temp_dir, "%s.json" % uuid.uuid4().hex)
            with open(temp_file, 'wt') as writer:
                writer.write(self.to_json)
                writer.flush()
                writer.close()
            del writer
            res = json_to_featureclass(json_file=temp_file,
                                       out_fc=os.path.join(save_location, out_name))
            os.remove(temp_file)
        return res

    # ----------------------------------------------------------------------
    @property
    def features(self):
        """gets the features in the FeatureSet"""
        return self._features

    # ----------------------------------------------------------------------
    @property
    def fields(self):
        """gets the fields in the FeatureSet"""
        return self._fields

    # ----------------------------------------------------------------------
    @fields.setter
    def fields(self, fields):
        """sets the fields in the FeatureSet"""
        self._fields = fields


class FeatureCollection(Layer):
    """
    FeatureCollection is an object with a layer definition and a feature set.

    It is an in-memory collection of features with rendering information.

    Feature Collections can be stored as Items in the GIS, added as layers to a map or scene,
    passed as inputs to feature analysis tools, and returned as results from feature analysis tools
    if an output name for a feature layer is not specified when calling the tool.
    """

    # noinspection PyMissingConstructor
    def __init__(self, dictdata):
        self._hydrated = True
        self.properties = PropertyMap(dictdata)
        self.layer = self.properties

    @property
    def _lyr_json(self):
        return dict(self.properties)

    @property
    def _lyr_dict(self):
        return dict(self.properties)

    def __str__(self):
        return '<%s>' % type(self).__name__

    def __repr__(self):
        return '<%s>' % type(self).__name__

    def query(self):
        """
        Returns the data in this feature collection as a FeatureSet.
        Filtering by where clause is not supported for feature collections
        """
        if 'layers' in self.properties:
            return FeatureSet.from_dict(self.properties['layers'][0]['featureSet'])
        else:
            return FeatureSet.from_dict(self.properties['featureSet'])

