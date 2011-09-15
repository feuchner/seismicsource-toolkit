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

from PyQt4.QtCore import *
from PyQt4.QtGui import *

from mt_seismicsource import features
from mt_seismicsource import utils

def getAttributesFromASZ(cls, feature):
    """Get attribute values from selected feature in ASZ.""" 
    pass

def getAttributesFromFSZ(cls, feature):
    """Get attribute values from selected feature in FSZ.""" 
    pass

def getAttributesFromASZ(cls, feature):
    """Get attribute values from selected feature in ASZ.""" 
    pass

def getAttributesFromFBZ(cls, feature):
    """Get attribute values from selected feature in FBZ.""" 
    pass

def getAttributesFromFeature(cls, feature):
    """Get a list of attribute values from a feature."""
    pass

def getAttributesFromRecurrence(provider, feature):
    """Read recurrence attributes from fault layer."""
    
    parameters = {}
    
    attribute_map_fault = utils.getAttributeIndex(provider, 
        features.FAULT_SOURCE_ATTRIBUTES_RECURRENCE, create=False)
        
    # get fault background zone ID
    id_name = features.FAULT_SOURCE_ATTR_ID_FBZ['name']
    try:
        parameters['fbz_id'] = str(
            feature[attribute_map_fault[id_name][0]].toString())
    except KeyError:
        error_msg = "No recurrence data for zone %s" % (feature.id())
        QMessageBox.warning(None, "Missing Data", error_msg)
        return None
        
    # a and b value from FBZ (fault layer attributes)

    a_fbz_name = features.FAULT_SOURCE_ATTR_A_FBZ['name']
    b_fbz_name = features.FAULT_SOURCE_ATTR_B_FBZ['name']
    
    parameters['activity_fbz_a'] = \
        feature[attribute_map_fault[a_fbz_name][0]].toDouble()[0]
    parameters['activity_fbz_b'] = \
        feature[attribute_map_fault[b_fbz_name][0]].toDouble()[0]
        
    act_fbz_a_name = features.FAULT_SOURCE_ATTR_ACT_FBZ_A['name']
    act_fbz_b_name = features.FAULT_SOURCE_ATTR_ACT_FBZ_B['name']

    parameters['activity_fbz_act_a'] = str(
        feature[attribute_map_fault[act_fbz_a_name][0]].toString())
    parameters['activity_fbz_act_b'] = str(
        feature[attribute_map_fault[act_fbz_b_name][0]].toString())
        
    # a and b value from buffer zone (fault layer attributes)

    a_bz_name = features.FAULT_SOURCE_ATTR_A_BUF['name']
    b_bz_name = features.FAULT_SOURCE_ATTR_B_BUF['name']
    
    parameters['activity_bz_a'] = \
        feature[attribute_map_fault[a_bz_name][0]].toDouble()[0]
    parameters['activity_bz_b'] = \
        feature[attribute_map_fault[b_bz_name][0]].toDouble()[0]
        
    act_bz_a_name = features.FAULT_SOURCE_ATTR_ACT_BUF_A['name']
    act_bz_b_name = features.FAULT_SOURCE_ATTR_ACT_BUF_B['name']

    parameters['activity_bz_act_a'] = str(
        feature[attribute_map_fault[act_bz_a_name][0]].toString())
    parameters['activity_bz_act_b'] = str(
        feature[attribute_map_fault[act_bz_b_name][0]].toString())
        
    # a and b value from FBZ, above magnitude threshold

    a_fbz_at_name = features.FAULT_SOURCE_ATTR_A_FBZ_AT['name']
    b_fbz_at_name = features.FAULT_SOURCE_ATTR_B_FBZ_AT['name']
    
    parameters['activity_fbz_at_a'] = \
        feature[attribute_map_fault[a_fbz_at_name][0]].toDouble()[0]
    parameters['activity_fbz_at_b'] = \
        feature[attribute_map_fault[b_fbz_at_name][0]].toDouble()[0]
        
    act_fbz_at_a_name = features.FAULT_SOURCE_ATTR_ACT_FBZ_AT_A['name']
    act_fbz_at_b_name = features.FAULT_SOURCE_ATTR_ACT_FBZ_AT_B['name']

    parameters['activity_fbz_at_act_a'] = str(
        feature[attribute_map_fault[act_fbz_at_a_name][0]].toString())
    parameters['activity_fbz_at_act_b'] = str(
        feature[attribute_map_fault[act_fbz_at_b_name][0]].toString())
        
    # a values from recurrence (fault layer attributes)
    
    a_rec_min_name = features.FAULT_SOURCE_ATTR_A_REC_MIN['name']
    a_rec_max_name = features.FAULT_SOURCE_ATTR_A_REC_MAX['name']
    
    parameters['activity_rec_a_min'] = \
        feature[attribute_map_fault[a_rec_min_name][0]].toDouble()[0]
    parameters['activity_rec_a_max'] = \
        feature[attribute_map_fault[a_rec_max_name][0]].toDouble()[0]
        
    sliprate_min_name = features.FAULT_SOURCE_ATTR_SLIPRATE_MIN['name']
    sliprate_max_name = features.FAULT_SOURCE_ATTR_SLIPRATE_MAX['name']
    mmax_fault_name = features.FAULT_SOURCE_ATTR_MAGNITUDE_MAX['name']
    
    parameters['sliprate_min'] = \
        feature[attribute_map_fault[sliprate_min_name][0]].toDouble()[0]
    parameters['sliprate_max'] = \
        feature[attribute_map_fault[sliprate_max_name][0]].toDouble()[0]
    parameters['mmax_fault'] = \
        feature[attribute_map_fault[mmax_fault_name][0]].toDouble()[0]

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
    
    print values
    
    try:
        provider.changeAttributeValues(values)
    except Exception, e:
        error_str = "cannot update attribute values, %s" % (e)
        raise RuntimeError, error_str

    layer.commitChanges()
    