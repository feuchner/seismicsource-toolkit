# -*- coding: utf-8 -*-
"""
SHARE Seismic Source Toolkit

Loader for area source layer.

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

import os
import shapely.geometry

from PyQt4.QtCore import *
from PyQt4.QtGui import *

from qgis.core import *

from mt_seismicsource import layers
from mt_seismicsource import features
from mt_seismicsource import utils

ZONE_FILE_DIR = 'area_sources'
ZONE_FILES = ('share-v2.01-150411.shp', 'share-v2.0-301110.shp', 
    'GEM1_europe_source_model.shp')

TEMP_FILENAME = 'area-source-zones.shp'

COPY_ATTRIBUTES = (features.AREA_SOURCE_ATTR_MMAX,
    features.AREA_SOURCE_ATTR_MCDIST)

def loadAreaSourceLayer(cls):
    """Load area source layer from Shapefile. Add required feature attributes
    if they are missing.
    """
    area_source_path = os.path.join(layers.DATA_DIR, 
        ZONE_FILE_DIR, unicode(cls.comboBoxZoneInput.currentText()))
    if not os.path.isfile(area_source_path):
        utils.warning_box_missing_layer_file(area_source_path)
        return

    temp_area_source_layer = QgsVectorLayer(area_source_path, 
        "Area Sources", "ogr")

    # PostGIS SRID 4326 is allocated for WGS84
    crs = QgsCoordinateReferenceSystem(4326, 
        QgsCoordinateReferenceSystem.PostgisCrsId)

    layer = utils.shp2memory(temp_area_source_layer, "Area Sources")
    layer.setCrs(crs) 

    # check if all features are okay
    _checkAreaSourceLayer(layer)

    # assign attributes from background zones
    assignAttributesFromBackgroundZones(layer, cls.background_zone_layer)

    QgsMapLayerRegistry.instance().addMapLayer(layer)
    utils.writeLayerToShapefile(layer, os.path.join(layers.DATA_DIR, 
        ZONE_FILE_DIR, TEMP_FILENAME), crs)

    return layer

def assignAttributesFromBackgroundZones(layer, background_layer):
    """Copy attributes from background zone layer."""
    provider = layer.dataProvider()
    provider_back = background_layer.dataProvider()

    # create missing attributes
    for attribute_list in features.AREA_SOURCE_ATTRIBUTES_ALL:
        utils.getAttributeIndex(provider, attribute_list, create=True)

    values = {}
    attribute_map = utils.getAttributeIndex(provider, COPY_ATTRIBUTES)

    provider.select()
    provider.rewind()
    for zone_idx, zone in utils.walkValidPolygonFeatures(provider):

        attributes = {}
        skipZone = False

        # get mmax and mcdist from background zones
        polygon, vertices = utils.polygonsQGS2Shapely((zone,))
        centroid = polygon[0].centroid
        copy_attr = getAttributesFromBackgroundZones(centroid,
            provider_back)

        for attr_idx, attr_dict in enumerate(COPY_ATTRIBUTES):
            (curr_idx, curr_type) = attribute_map[attr_dict['name']]

            # if one of the attribute values is None, skip zone
            if copy_attr[attr_idx] is None:
                skipZone = True
                break
                
            try:
                # attributes are of type QVariant
                attributes[curr_idx] = copy_attr[attr_idx]
            except Exception, e:
                error_str = \
        "error in attribute: curr_idx: %s, zone_idx: %s, attr_idx: %s, %s" % (
                    curr_idx, zone_idx, attr_idx, e)
                raise RuntimeError, error_str
        
        if skipZone is False:
            values[zone.id()] = attributes

    try:
        provider.changeAttributeValues(values)
    except Exception, e:
        error_str = "cannot update attribute values, %s" % (e)
        raise RuntimeError, error_str

def getAttributesFromBackgroundZones(point, provider_back):
    """Get mmax and mcdist from background zone at a given
    Shapely point."""

    attribute_map = utils.getAttributeIndex(provider_back, COPY_ATTRIBUTES)

    # identify matching background zone
    background_zone = utils.findBackgroundZone(point, provider_back)
    
    if background_zone is not None:
        # leave values as QVariant
        background_attrs = [background_zone[attribute_map[x['name']][0]] \
            for x in COPY_ATTRIBUTES]
    else:
        background_attrs = [None, None]

    return background_attrs

def _checkAreaSourceLayer(layer):
    """Check if features in area source layer are without errors.

    Input:
        layer       polygon layer
    """

    provider = layer.dataProvider()
    provider.select()
    provider.rewind()
    broken_features = []

    for feature_idx, feature in enumerate(provider):
        try:
            qgis_geometry_aspolygon = feature.geometry().asPolygon()
        except Exception:
            broken_features.append(feature_idx)
            continue

        # no outer ring given
        if len(qgis_geometry_aspolygon) == 0:
            broken_features.append(feature_idx)
            continue

        # check if there are enough vertices
        vertices = [(x.x(), x.y()) for x in qgis_geometry_aspolygon[0]]
        if len(vertices) < 4:
            broken_features.append(feature_idx)
            continue

        try:
            shapely_polygon = shapely.geometry.Polygon(vertices)
        except Exception:
            broken_features.append(feature_idx)
            continue

    if len(broken_features) > 0:
        utils.warning_box_broken_area_features(broken_features)
