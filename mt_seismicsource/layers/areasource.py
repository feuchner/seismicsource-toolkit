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

from mt_seismicsource.layers import render

ZONE_FILE_DIR = 'area_sources'
ZONE_FILES = ('share-v2.01-150411.shp', 'share-v2.0-301110.shp', 
    'GEM1_europe_source_model.shp')

TEMP_FILENAME = 'area-source-zones.shp'

MCDIST_MMAX_ATTRIBUTES = (features.AREA_SOURCE_ATTR_MCDIST,
    features.AREA_SOURCE_ATTR_MMAX)

MCDIST_ATTRIBUTES = (features.AREA_SOURCE_ATTR_MCDIST,)
MMAX_ATTRIBUTES = (features.AREA_SOURCE_ATTR_ID, 
    features.AREA_SOURCE_ATTR_MMAX)

def loadAreaSourceLayer(cls):
    """Load area source layer from Shapefile. Add required feature attributes
    if they are missing.
    """
    area_source_path = os.path.join(layers.DATA_DIR, 
        ZONE_FILE_DIR, unicode(cls.comboBoxAreaZoneInput.currentText()))
        
    if not os.path.isfile(area_source_path):
        utils.warning_missing_layer_file(area_source_path)
        return

    save_path = os.path.join(layers.DATA_DIR, ZONE_FILE_DIR, TEMP_FILENAME)
    layer = loadAreaSourceFromSHP(area_source_path, cls.data.mmax, 
        cls.background_zone_layer, save_path, layer2file=True)
    
    # register layer in QGis
    QgsMapLayerRegistry.instance().addMapLayer(layer)
    
    # set layer visibility
    cls.legend.setLayerVisible(layer, render.AREA_LAYER_STYLE['visible'])
    
    return layer

def loadAreaSourceFromSHP(filename_in, mmax_data, background_layer, 
    filename_out=None, layer2file=False, ui_mode=True):
    """Load area source layer from Shapefile, independent of QGis UI."""
    
    temp_area_source_layer = QgsVectorLayer(filename_in, "Area Sources", "ogr")

    # PostGIS SRID 4326 is allocated for WGS84
    crs = QgsCoordinateReferenceSystem(4326, 
        QgsCoordinateReferenceSystem.PostgisCrsId)

    layer = utils.shp2memory(temp_area_source_layer, "Area Sources")
    layer.setCrs(crs) 

    # check if all features are okay
    _checkAreaSourceLayer(layer, ui_mode=ui_mode)

    # assign Mmax from Meletti data set
    assignMmaxfromMelettiDataset(layer, mmax_data)
    
    # assign attributes from background zones
    assignAttributesFromBackgroundZones(layer, background_layer, 
        MCDIST_ATTRIBUTES)

    # write memory layer to disk (as a Shapefile)
    if layer2file is True:
        utils.writeLayerToShapefile(layer, filename_out, crs, ui_mode=ui_mode)
        
    return layer
        
def assignMmaxfromMelettiDataset(layer, mmax_data):
    """Assign Mmax from Meletti data set to area source zone layer."""
    
    provider = layer.dataProvider()
    
    # create missing attributes (if required)
    for attribute_list in features.AREA_SOURCE_ATTRIBUTES_ALL:
        utils.getAttributeIndex(provider, attribute_list, create=True)
        
    values = {}
    attribute_map = utils.getAttributeIndex(provider, MMAX_ATTRIBUTES)
    
    id_idx, id_type = attribute_map[features.AREA_SOURCE_ATTR_ID['name']]
    mmax_idx, mmax_type = \
        attribute_map[features.AREA_SOURCE_ATTR_MMAX['name']]
            
    provider.select()
    provider.rewind()
    for zone_idx, zone in utils.walkValidPolygonFeatures(provider):

        zone_id = int(zone[id_idx].toInt()[0])
        
        # mmax from Meletti data set
        try:
            mmax = mmax_data[zone_id]['mmax']
        except Exception:
            continue

        try:
            values[zone.id()] = {mmax_idx: QVariant(mmax)}
        except Exception, e:
            error_str = \
            "error in attribute: zone_idx: %s, zone_id: %s, mmax: %s, %s" % (
                zone_idx, zone.id(), mmax, e)
            raise RuntimeError, error_str
        
    try:
        provider.changeAttributeValues(values)
    except Exception, e:
        error_str = "cannot update attribute values, %s" % (e)
        raise RuntimeError, error_str
    
    layer.commitChanges()

def assignAttributesFromBackgroundZones(layer, background_layer, 
    attributes_in):
    """Copy attributes from background zone layer."""
    
    provider = layer.dataProvider()
    provider_back = background_layer.dataProvider()

    # create missing attributes (if required)
    for attribute_list in features.AREA_SOURCE_ATTRIBUTES_ALL:
        utils.getAttributeIndex(provider, attribute_list, create=True)

    values = {}
    attribute_map = utils.getAttributeIndex(provider, attributes_in)

    provider.select()
    provider.rewind()
    for zone_idx, zone in utils.walkValidPolygonFeatures(provider):

        attributes = {}
        skipZone = False

        # get mmax and mcdist from background zones
        polygon, vertices = utils.polygonsQGS2Shapely((zone,))
        centroid = polygon[0].centroid
        copy_attr = getAttributesFromBackgroundZones(centroid,
            provider_back, attributes_in)

        for attr_idx, attr_dict in enumerate(attributes_in):
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
    
    layer.commitChanges()

def getAttributesFromBackgroundZones(point, provider_back, attributes):
    """Get attribute list (from mmax and mcdist) from background zone 
    at a given Shapely point."""

    attribute_map = utils.getAttributeIndex(provider_back, attributes)

    # identify matching background zone
    (background_zone, bgz_poly, bgz_area) = utils.findBackgroundZone(
        point, provider_back)
    
    if background_zone is not None:
        # leave values as QVariant
        background_attrs = [background_zone[attribute_map[x['name']][0]] \
            for x in attributes]
    else:
        background_attrs = [None] * len(attributes)

    return background_attrs

def _checkAreaSourceLayer(layer, ui_mode=True):
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
        utils.warning_broken_area_features(broken_features, ui_mode=True)
