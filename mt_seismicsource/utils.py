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

def featureCount(layer_provider, checkGeometry=False):
    if checkGeometry is False:
        return layer_provider.featureCount()
    else:
        counter = 0
        layer_provider.rewind()
        for feature in layer_provider:
            if verticesOuterFromQGSPolygon(feature) is not None:
                counter += 1
        layer_provider.rewind()
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

    #QMessageBox.information(None, "Orig Layer", "%s, %s, %s, %s" % (
        #pr_orig.encoding(), pr_orig.geometryType(),
            #pr_orig.crs(), pr_orig.fields()))

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

    mem_layer.updateExtents()
    return mem_layer

def writeLayerToShapefile(layer, path, crs, encoding=SHAPEFILE_ENCODING):
    error = QgsVectorFileWriter.writeAsShapefile(layer, path, encoding, crs)
    if error != QgsVectorFileWriter.NoError:
        QMessageBox.error(None, "Error writing shapefile", 
            "Cannot write layer to shapefile: %s" % path)

def warning_box_missing_layer_file(filename):
    QMessageBox.warning(None, "File not found", 
        "Layer file not found: %s" % os.path.basename(filename))

def warning_box_broken_area_features(broken_features):
     QMessageBox.warning(None, "Broken features", 
        "IDs of broken features:\n %s" % " ".join(
        [str(x) for x in broken_features]))
