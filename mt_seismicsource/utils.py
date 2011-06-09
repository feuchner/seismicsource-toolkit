# -*- coding: utf-8 -*-
"""
SHARE Seismic Source Toolkit

This module holds utility functions.

Author: Fabian Euchner, fabian@sed.ethz.ch
"""

############################################################################
#    This program is free software; you can redistribute it and/or modify  #
#    it under the terms of the GNU General Public License as published by  #
#    the Free Software Foundation; either version 2 of the License, or     #
#    (at your option) any later version.                                   #
#                                                                          #
#    This program is distributed in the hope that it will be useful,       #
#    but WITHOUT ANY WARRANTY; without even the implied warranty of        #
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         #
#    GNU General Public License for more details.                          #
#                                                                          #
#    You should have received a copy of the GNU General Public License     #
#    along with this program; if not, write to the                         #
#    Free Software Foundation, Inc.,                                       #
#    59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.             #
############################################################################

import numpy
import os
import shapely.geometry
import shutil
import stat
import subprocess
import tempfile
import time

from PyQt4.QtCore import *
from PyQt4.QtGui import *

from qgis.core import *

import features

SHAPEFILE_ENCODING = "UTF-8"

EARTH_CIRCUMFERENCE_EQUATORIAL_KM = 40075.017

# maximum likelihood a- and b-values, as implemented in ZMAP

def assignActivityMaxLikelihood():
    pass

def computeActivityMaxLikelihood(zones, catalog):
    """Computes a-and b values using the maximum likelihood method for
    a set of source zone polygons.
    
    Input: 
        zones       iterable of polygon features in QGis format
        catalog     earthquake catalog as QuakePy object

    Output: list of (a, b) pairs
    """
    pass

# Misc. QGis/Shapely featutes

def featureCount(layer, checkGeometry=False):
    """Get number of features in layer provider, or selected features.

    layer: can be of type QGis provider, or of type list
    """

    if isinstance(layer, list):
        if checkGeometry is False:
            return len(layer)
        else:
            counter = 0
            for feature in layer:
                if verticesOuterFromQGSPolygon(feature) is not None:
                    counter += 1
            return counter
    else:
        if checkGeometry is False:
            return layer.featureCount()
        else:
            counter = 0
            layer.rewind()
            for feature in layer:
                if verticesOuterFromQGSPolygon(feature) is not None:
                    counter += 1
            layer.rewind()
            return counter

def walkValidPolygonFeatures(provider):
    """Generator that yields index and feature for polygon layer, skips
    features with invalid geometry.
    """
    feature_idx = 0
    provider.rewind()
    for feature in provider:
        if verticesOuterFromQGSPolygon(feature) is None:
            continue
        else:
            feature_idx += 1
            yield(feature_idx-1, feature)

def verticesOuterFromQGSPolygon(feature):
    """Return list of (lon, lat) vertices from QGis polygon feature."""
    geom = feature.geometry().asPolygon()
    if len(geom) == 0:
        return None
    else:
        # skip last vertex is it's a duplicate of first one
        vertices = [(x.x(), x.y()) for x in geom[0][0:-1]]
        if len(vertices) == 0:
            return None
    return vertices

def polygonsQGS2Shapely(polygons, getVertices=False):
    """Convert feature geometry of QGis polygon iterable to list of Shapely
    polygons. Polygons can be a list of QGis features, or a data provider."""

    polygons_shapely = []
    vertices_shapely = []

    for feature in polygons:

        vertices = verticesOuterFromQGSPolygon(feature)
        if vertices is None:
            continue

        shapely_polygon = shapely.geometry.Polygon(vertices)
        polygons_shapely.append(shapely_polygon)

        if getVertices is True:
            for vertex in vertices:
                vertices_shapely.append(shapely.geometry.Point(vertex))

    return (polygons_shapely, vertices_shapely)

def findBackgroundZone(point, provider_back):
    """Find background zone in which a given Shapely point lies."""
    
    bg_zone = None

    # TODO(fab): this can probably be made more efficient
    # loop over background zones
    provider_back.select()
    provider_back.rewind()
    for bgz in provider_back:

        # convert background zone polygon to Shapely
        bg_poly, vertices = polygonsQGS2Shapely((bgz,))

        if point.within(bg_poly[0]):
            bg_zone = bgz
            break

    return bg_zone

def getSelectedRefZoneIndices(reference_zones):
    """Get indices of selected zones from list of all source zones.
    reference_zones is list of selected QGis features."""
    return []

def getAttributeIndex(provider, attributes, create=True):
    """Get indices of attributes in QGis layer. 

    Input:
        provider    layer provider
        attributes  iterable of dicts with attributes 'name', 'type', e.g.
                    (('name': 'a_rm', 'type': QVariant.Double), 
                     ('name': 'b_rm', 'type': QVariant.Double)).
        create      if True, missing attributes will be added to the layer.

    Output:
        return value is a dictionary with attribute name as keys, and 
        (index, type) pais as values
    """
    
    attribute_map = {}

    for attr_dict in attributes:
        attr_index = provider.fieldNameIndex(attr_dict['name'])

        # if attribute not existing (return value -1), create it,
        # if create is True
        if attr_index == -1 and create is True:
            provider.addAttributes([QgsField(attr_dict['name'], 
                attr_dict['type'])])
            attr_index = provider.fieldNameIndex(attr_dict['name'])

        attribute_map[attr_dict['name']] = (attr_index, attr_dict['type'])

    return attribute_map

def distrostring2plotdata(distrostring):
    """Get discrete distribution from serialization."""

    value_arr = distrostring.split()
    abscissae = [float(x) for x in value_arr[::2]]
    ordinates = [float(x) for x in value_arr[1::2]]

    data = numpy.vstack((numpy.array(abscissae), numpy.array(ordinates)))

    return data

def shp2memory(layer, name):
    """Convert QGis layer from shapefile to QGis layer in memory.
    Returns layer from memory provider.

    Works only for Polygon and LineString layers at the moment.
    """

    pr_orig = layer.dataProvider()
    geometry_type = pr_orig.geometryType()
    if geometry_type == 3:
        geometry_token = "Polygon"
    elif geometry_type == 2:
        geometry_token = "LineString"
    else:
        error_str = "Currently, only geometry types Polygon (3) and " \
            "LineString (2) are supported."
        raise RuntimeError, error_str

    # create layer
    mem_layer = QgsVectorLayer(geometry_token, name, "memory")
    pr = mem_layer.dataProvider()
    mem_layer.startEditing()

    # TODO(fab): check if encoding() and crs() have to be set in new layer

    # add fields
    pr.addAttributes([field for idx, field in pr_orig.fields().items()])

    # select all attribute indexes
    allAttrIndices = pr_orig.attributeIndexes()
    pr_orig.select(allAttrIndices)

    for feat in pr_orig:
        geom = feat.geometry()
        attrs = feat.attributeMap()

        f = QgsFeature()
        f.setGeometry(geom)

        for attr_idx, attr in attrs.items():
            f[attr_idx] = QVariant(attr)
        pr.addFeatures([f])

    mem_layer.commitChanges()
    mem_layer.updateExtents()
    return mem_layer

def polygonAreaFromWGS84(polygon):
    """Compute area of polygon given in WGS84 lon/lat converted
    to square metres.

    Input:
        polygon     Shapely polygon

    Output:
        area        Polygon area in square metres
    """
    poly_area_deg = polygon.area
    poly_center = polygon.centroid

    # get coordinates of polygon centre
    area = poly_area_deg * \
        numpy.power((EARTH_CIRCUMFERENCE_EQUATORIAL_KM * 1000 / 360.0), 2) * \
        numpy.cos(numpy.pi * float(poly_center.y) / 180.0)

    return area

def writeLayerToShapefile(layer, path, crs, encoding=SHAPEFILE_ENCODING):
    error = QgsVectorFileWriter.writeAsShapefile(layer, path, encoding, crs)
    if error != QgsVectorFileWriter.NoError:
        QMessageBox.warning(None, "Error writing shapefile", 
            "Error %s: Cannot write layer to shapefile: %s" % (error, path))

def check_only_one_feature_selected(layer):
    """Display a warning box if no feature or more than one feature
    is selected."""
    feature_count = featureCount(layer.selectedFeatures())
    if feature_count == 0:
        warning_box_no_feature_selected()
        return False
    elif feature_count > 1:
        warning_box_more_than_one_feature_selected()
        return False
    else:
        return True

def check_at_least_one_feature_selected(layer):
    """Display a warning box if no feature is selected."""
    feature_count = featureCount(layer.selectedFeatures())
    if feature_count == 0:
        warning_box_no_feature_selected()
        return False
    else:
        return True

def getFeatureAttributes(layer, feature, attributes):
    """Get feature attributes."""
    
    attributes_out = []
    
    provider = layer.dataProvider()
    attribute_map = getAttributeIndex(provider, attributes, create=False)
    
    for attr_dict in attributes:
        (curr_idx, curr_type) = attribute_map[attr_dict['name']]
        
        if curr_idx == -1:
            attribute_value = None
        else:
            attribute_value = feature[curr_idx]
            
        attributes_out.append(attribute_value)
    
    return attributes_out

def centralValueOfList(list_in):
    """Return central value of a list."""
    central_idx = len(list_in) / 2
    return list_in[central_idx]
    
def warning_box_missing_layer_file(filename):
    QMessageBox.warning(None, "File not found", 
        "Layer file not found: %s" % os.path.basename(filename))

def warning_box_broken_area_features(broken_features):
     QMessageBox.warning(None, "Broken features", 
        "IDs of broken features:\n %s" % " ".join(
        [str(x) for x in broken_features]))

def warning_box_no_feature_selected():
    QMessageBox.warning(None, "No feature selected", 
    "Please select a feature")

def warning_box_more_than_one_feature_selected():
    QMessageBox.warning(None, "Too many features selected", 
    "Please select one and only one feature")


