# -*- coding: utf-8 -*-
"""
SHARE Seismic Source Toolkit

Get attribute values from memory layers.

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

from PyQt4.QtCore import *
from PyQt4.QtGui import *

from mt_seismicsource import features
from mt_seismicsource import plots
from mt_seismicsource import utils

from mt_seismicsource.algorithms import atticivy

EMPTY_STRING_ATTR = ''
EMPTY_REAL_ATTR = float(numpy.nan)
EMPTY_INTEGER_ATTR = 0

def getAttributesFromASZ(parameters, layer, feature):
    """Get attribute values from selected feature in ASZ.""" 
        
    parameters_new = getAttributesFromFeature(layer, feature, 
        features.AREA_SOURCE_ATTRIBUTES_ALL)
        
    parameters.update(parameters_new)
    parameters.update(getNonAttributesFromASZ(layer, feature))
    
    return parameters

def getNonAttributesFromASZ(layer, feature):
    """Get feature attributes that are not set in layer's attribute table.
    These have to be re-evaluated if a feature is only viewed, not computed.
    """
    parameters = {
        atticivy.ATTICIVY_MMIN_KEY_NAME: atticivy.ATTICIVY_MMIN, 
        plots.PLOT_TITLE_FMD_NAME: utils.getPlotTitleFMD(layer, feature)}
        
    return parameters

def getAttributesFromFSZ(parameters, layer, feature):
    """Get attribute values from selected feature in FSZ.""" 
    
    parameters_new = getAttributesFromFeature(layer, feature, 
        features.FAULT_SOURCE_ATTRIBUTES_RECURRENCE)
    
    parameters.update(parameters_new)
    parameters.update(getNonAttributesFromFSZ(layer, feature))
    
    return parameters

def getNonAttributesFromFSZ(layer, feature):
    """Get feature attributes that are not set in layer's attribute table.
    These have to be re-evaluated if a feature is only viewed, not computed.
    """
    
    parameters = {
        atticivy.ATTICIVY_MMIN_KEY_NAME: atticivy.ATTICIVY_MMIN}
    
    return parameters

def getAttributesFromFBZ(parameters, layer, feature):
    """Get attribute values from selected feature in FBZ.""" 
    
    parameters_new = getAttributesFromFeature(layer, feature, [])
    
    parameters.update(parameters_new)
    parameters.update(getNonAttributesFromFBZ(layer, feature))
    
    return parameters

def getNonAttributesFromFBZ(layer, feature):
    return {}

def getAttributesFromFeature(layer, feature, attributes):
    """Get a list of attribute values from a feature."""
    
    parameters = {}
    
    provider = layer.dataProvider()
    attribute_map = utils.getAttributeIndex(provider, attributes, 
        create=False)
        
    for attribute in attributes:
        attr_name = attribute['name']
        attr_type = attribute['type']
        
        try:
            raw_attribute = feature[attribute_map[attr_name][0]]
            
        except KeyError:
            parameters[attribute['name']] = None
            continue
        
        if attr_type == QVariant.String:
            processed_attribute = str(raw_attribute.toString())
            
        elif attr_type == QVariant.Double:
            processed_attribute = float(raw_attribute.toDouble()[0])
        
        elif attr_type == QVariant.Int:
            processed_attribute = int(raw_attribute.toInt()[0])
        
        else:
            processed_attribute = raw_attribute
            
        parameters[attribute['name']] = processed_attribute
    
    return parameters

def getAttributesFromRecurrence(layer, feature, ui_mode=True):
    """Read recurrence attributes from fault layer."""
    
    parameters = getAttributesFromFeature(layer, feature, 
        features.FAULT_SOURCE_ATTRIBUTES_RECURRENCE_COMPUTE)
        
    id_name = features.FAULT_SOURCE_ATTR_ID_FBZ['name']
    
    if parameters[id_name] is None:
        error_msg = "No recurrence data for zone %s" % (feature.id())
        if ui_mode is True:
            QMessageBox.warning(None, "Missing Data", error_msg)
        else:
            print error_msg
        return None
    else:
        return parameters

def writeLayerAttributes(layer, feature_list, attributes_in):
    """Write attributes to layer.
    
    Input:
    
        attributes_in   list that contains for each feature a list 
                        of attributes
    """
    
    fts = layer.selectedFeatures()
    provider = layer.dataProvider()
    attribute_map = utils.getAttributeIndex(provider, feature_list, 
        create=True)
    
    values = {}

    # loop over selected QGis features
    for zone_idx, zone in enumerate(fts):
        attribute_list = {}
        skipZone = False
        
        for attr_idx, attr_dict in enumerate(feature_list):
            (curr_idx, curr_type) = attribute_map[attr_dict['name']]
            try:
                attribute_list[curr_idx] = QVariant(
                    attributes_in[zone_idx][attr_idx])
            except Exception, e:
                skipZone = True
                break

        if skipZone is False:
            values[zone.id()] = attribute_list
    
    try:
        provider.changeAttributeValues(values)
    except Exception, e:
        error_str = "cannot update attribute values, %s" % (e)
        raise RuntimeError, error_str

    layer.commitChanges()
    