# -*- coding: utf-8 -*-
"""
SHARE Seismic Source Toolkit

Attribute computation on FSZ layer.

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

from qgis.core import *

import QPCatalog
import qpfmd

from mt_seismicsource import attributes
from mt_seismicsource import engine
from mt_seismicsource import features
from mt_seismicsource import utils

from mt_seismicsource.algorithms import atticivy
from mt_seismicsource.algorithms import momentrate
from mt_seismicsource.algorithms import recurrence

from mt_seismicsource.engine import fmd

from mt_seismicsource.layers import areasource
from mt_seismicsource.layers import eqcatalog

def computeFSZ(layer_fault, layer_fault_background, layer_background, catalog,
    catalog_time_span=None, b_value=None,
    mmin=atticivy.ATTICIVY_MMIN, 
    m_threshold=recurrence.FAULT_BACKGROUND_MAG_THRESHOLD,
    mindepth=eqcatalog.CUT_DEPTH_MIN, maxdepth=eqcatalog.CUT_DEPTH_MAX,
    mc_method=qpfmd.DEFAULT_MC_METHOD, mc=None,
    ui_mode=True):
    """Compute attributes on selected features of ASZ layer."""
    
    # check that at least one feature is selected
    if not utils.check_at_least_one_feature_selected(layer_fault, 
        ui_mode=ui_mode):
        return

    (cat_depthcut, catalog_time_span) = engine.prepareEQCatalog(catalog, 
        catalog_time_span, mindepth, maxdepth)

    updateFSZRecurrence(layer_fault, layer_fault_background, layer_background,
        catalog, catalog_time_span, b_value, mmin, m_threshold, mindepth, 
        maxdepth, ui_mode=ui_mode)
        
    parameters_ml_ab = updateFSZMaxLikelihoodAB(layer_fault,
        layer_fault_background, cat_depthcut, catalog_time_span, mc_method, 
        mc, ui_mode=ui_mode)
    parameters_mr = updateFSZMomentRate(layer_fault, cat_depthcut, 
        catalog_time_span, ui_mode=ui_mode)
    
    parameters = parameters_ml_ab
    for param_idx, parameter in enumerate(parameters):
        parameter.update(parameters_mr[param_idx])
    
    return parameters
    
def updateFSZRecurrence(layer_fault, layer_fault_background=None, 
    layer_background=None, catalog=None, catalog_time_span=None, b_value=None,
    mmin=atticivy.ATTICIVY_MMIN, 
    m_threshold=recurrence.FAULT_BACKGROUND_MAG_THRESHOLD,
    mindepth=eqcatalog.CUT_DEPTH_MIN, maxdepth=eqcatalog.CUT_DEPTH_MAX,
    ui_mode=True):
    """Update AtticIvy attributes on FSZ layer."""

    recurrence.assignRecurrence(layer_fault, layer_fault_background, 
        layer_background, catalog, catalog_time_span, 
        m_threshold=m_threshold, mindepth=mindepth, maxdepth=maxdepth, 
        ui_mode=ui_mode)

def updateFSZMaxLikelihoodAB(layer, layer_back, catalog, catalog_time_span,
    mc_method=qpfmd.DEFAULT_MC_METHOD, mc=None, ui_mode=True):
    """Update max likelihood a/b value attributes on FSZ layer."""
    
    ab_attributes = features.FAULT_SOURCE_ATTRIBUTES_AB_ML_COMPUTE
        
    (ab_values, parameters) = computeMaxLikelihoodAB(layer, layer_back,
        catalog, catalog_time_span, mc_method, mc, ui_mode=ui_mode)
    attributes.writeLayerAttributes(layer, ab_attributes, ab_values)
    
    return parameters

def updateFSZMomentRate(layer, catalog, catalog_time_span, ui_mode=True):
    """Update seismic moment rate attributes on FSZ layer."""
    
    mr_attributes = features.FAULT_SOURCE_ATTRIBUTES_MOMENTRATE_COMPUTE
        
    (mr_values, parameters) = computeMomentRate(layer, catalog, 
        catalog_time_span, ui_mode=ui_mode)
    attributes.writeLayerAttributes(layer, mr_attributes, mr_values)
    
    return parameters

def computeMaxLikelihoodAB(layer, layer_back, catalog, catalog_time_span,
    mc_method=qpfmd.DEFAULT_MC_METHOD, mc=None, ui_mode=True):
    """Compute a and b values with maximum likelihood method.
    
    Input:
        catalog     QPCatalog that is already cut at min/max depth
        
    Returns a list of 7-tuples:
    (ml_a, ml_b, ml_mc, ml_magctr, mc_method, eq_count_fbz, area_fbz_sqkm)
    """
    
    fts = layer.selectedFeatures()
    provider = layer.dataProvider()
    provider_fault_back = layer_back.dataProvider()
    
    area_fbz_sqkm_name = features.FAULT_SOURCE_ATTR_AREA_FBZ['name']
    eq_count_fbz_name = features.FAULT_SOURCE_ATTR_EQ_CNT_FBZ['name']
    
    if ui_mode is False:
        print "\n=== Computing MaxLikelihoodAB for %s features ===" % len(fts)

    result_values = []
    out_parameters = []
    
    # loop over features
    for zone_idx, feature in enumerate(fts):

        parameters = {}
        brokenZone = False
        
        # get Shapely polygon from feature geometry
        polylist, vertices = utils.polygonsQGS2Shapely((feature,))
        
        try:
            fault_poly = polylist[0]
        except IndexError:
            error_msg = "FSZ, max likelihood AB: invalid FSZ geometry, "\
                "id %s" % (feature.id())
            if ui_mode is True:
                QMessageBox.warning(None, "FSZ Warning", error_msg)
            else:
                print error_msg
                
            brokenZone = True
            attribute_list = getEmptyMaxLikelihoodABAttributeList()

        if brokenZone is False:
            # find fault background zone in which centroid of fault zone lies
            # NOTE: this can yield a wrong background zone if the fault zone
            # is curved and at the edge of background zone.
            # TODO(fab): use GIS "within" function instead, but note that fault
            # zone can overlap several BG zones
            (fbz, fbz_poly, parameters[area_fbz_sqkm_name]) = \
                utils.findBackgroundZone(fault_poly.centroid, 
                provider_fault_back, ui_mode=ui_mode)

            # get quakes from catalog (cut with fault background polygon)
            fbz_cat = QPCatalog.QPCatalog()
            fbz_cat.merge(catalog)
            fbz_cat.cut(geometry=fbz_poly)
            parameters[eq_count_fbz_name] = fbz_cat.size()

            ## Maximum likelihood a/b values
            if parameters[eq_count_fbz_name] == 0:
                parameters[fmd.PARAMETER_FMD_NAME] = None
                attribute_list = getEmptyMaxLikelihoodABAttributeList()
                
                # set correct area
                attribute_list[-1] = parameters[area_fbz_sqkm_name]
                    
                error_msg = "FSZ, max likelihood AB: no EQs in zone with "\
                    "ID %s" % (feature.id())
                if ui_mode is True:
                    QMessageBox.warning(None, "FSZ: Max likelihood AB", 
                        error_msg)
                else:
                    print error_msg
                
            else:
                
                # FMD from quakes in FBZ
                parameters[fmd.PARAMETER_FMD_NAME] = fmd.computeZoneFMD(
                    feature, fbz_cat, catalog_time_span, mc_method, mc)
                attribute_list = list(fmd.getFMDValues(
                    parameters[fmd.PARAMETER_FMD_NAME]))
                attribute_list.append(parameters[eq_count_fbz_name])
                attribute_list.append(parameters[area_fbz_sqkm_name])
                
                if ui_mode is False:
                    print "FSZ (id %s), FMD: %s" % (feature.id(), 
                        str(attribute_list))
                
        result_values.append(attribute_list)
        out_parameters.append(parameters)
    
    return (result_values, out_parameters)

def computeMomentRate(layer, catalog, catalog_time_span, ui_mode=True):
    """Compute moment rate contributions for FSZ layer.
    
    Input:
        catalog     QPCatalog that is already cut at min/max depth
    
    Returns a list of 7-tuples:
    (mr_eq, mr_activity_str, mr_activity_fbz_at_str, mr_slip_min, mr_slip_max,
        eq_count_bz, area_bz_sqkm)
    """
    
    fts = layer.selectedFeatures()

    act_buf_a_name = features.FAULT_SOURCE_ATTR_ACT_BUF_A['name']
    act_buf_b_name = features.FAULT_SOURCE_ATTR_ACT_BUF_B['name']
    
    afbz_at_a_name = features.FAULT_SOURCE_ATTR_ACT_FBZ_AT_A['name']
    afbz_at_b_name = features.FAULT_SOURCE_ATTR_ACT_FBZ_AT_B['name']
    
    mr_eq_name = features.FAULT_SOURCE_ATTR_MR_EQ['name']
    mr_act_buf_name = features.FAULT_SOURCE_ATTR_MR_ACTIVITY_BUF['name']
    mr_act_fbz_name = features.FAULT_SOURCE_ATTR_MR_ACTIVITY_FBZ['name']
    
    sliprate_min_name = features.FAULT_SOURCE_ATTR_SLIPRATE_MIN['name']
    sliprate_max_name = features.FAULT_SOURCE_ATTR_SLIPRATE_MAX['name']
    mmax_bg_name = features.FAULT_SOURCE_ATTR_MMAX_BG['name']
    
    area_bz_sqkm_name = features.FAULT_SOURCE_ATTR_AREA_BZ['name']
    eq_count_bz_name = features.FAULT_SOURCE_ATTR_EQ_CNT_BZ['name']
    area_fault_sqkm_name = features.FAULT_SOURCE_ATTR_AREA_FAULT['name']
    
    if ui_mode is False:
        print "\n=== Computing moment rate for %s features ===" % len(fts)
        
    result_values = []
    out_parameters = []
    
    # loop over features
    for zone_idx, feature in enumerate(fts):
        
        parameters = {}
        brokenZone = False
        
        # get Shapely polygon from feature geometry
        polylist, vertices = utils.polygonsQGS2Shapely((feature,))
        
        try:
            fault_poly = polylist[0]
        except IndexError:
            error_msg = "FSZ, moment rates: invalid FSZ geometry, id %s" % (
                feature.id())
            if ui_mode is True:
                QMessageBox.warning(None, "FSZ Warning", error_msg)
            else:
                print error_msg
                
            brokenZone = True
            attribute_list = getEmptyMomentRateAttributeList()

        if brokenZone is False:
            recurrence_attributes = attributes.getAttributesFromRecurrence(
                layer, feature, ui_mode=ui_mode)
            
            if recurrence_attributes is not None:
                parameters.update(recurrence_attributes)
            else:
                error_msg = "FSZ (id %s): error reading already computed "\
                    "attribute values" % feature.id()
                if ui_mode is True:
                    QMessageBox.warning(None, "FSZ Warning", error_msg)
                else:
                    print error_msg
                    
                brokenZone = True
                attribute_list = getEmptyMomentRateAttributeList()

        if brokenZone is False:
            # fault zone polygon area in square kilometres
            parameters[area_fault_sqkm_name] = utils.polygonAreaFromWGS84(
                fault_poly) * 1.0e-6
            
            # get buffer zone around fault zone (convert buffer distance to degrees)
            (bz_poly, parameters[area_bz_sqkm_name]) = utils.computeBufferZone(
                fault_poly, momentrate.BUFFER_AROUND_FAULT_ZONE_KM)
    
            attribute_list = [features.FAULT_SOURCE_ATTR_MMAX_BG,
                features.FAULT_SOURCE_ATTR_SLIPRATE_MIN,
                features.FAULT_SOURCE_ATTR_SLIPRATE_MAX]
                
            # get missing attribute values from layer
            parameters_new = attributes.getAttributesFromFeature(layer, 
                feature, attribute_list)
            parameters.update(parameters_new)
            
            ## moment rate from EQs

            # get quakes from catalog (cut with buffer zone polygon)
            bz_cat = QPCatalog.QPCatalog()
            bz_cat.merge(catalog)
            bz_cat.cut(geometry=bz_poly)
            
            parameters[eq_count_bz_name] = bz_cat.size()
            
            # sum up moment from quakes (converted from Mw with Kanamori eq.)
            # use quakes in buffer zone
            magnitudes = []
            for ev in bz_cat.eventParameters.event:
                mag = ev.getPreferredMagnitude()
                magnitudes.append(mag.mag.value)

            moment = numpy.array(momentrate.magnitude2moment(magnitudes))

            # scale moment: per year and area (in km^2)
            parameters[mr_eq_name] = moment.sum() / (
                parameters[area_bz_sqkm_name] * catalog_time_span)
            
            ## moment rate from activity (RM)

            # moment rates from activity: use a and b values from buffer zone
            
            act_bz_arr_a = parameters[act_buf_a_name].strip().split()
            act_bz_arr_b = parameters[act_buf_b_name].strip().split()
            
            a_bz_arr = [float(x) for x in act_bz_arr_a]
            b_bz_arr = [float(x) for x in act_bz_arr_b]
            
            a_values = a_bz_arr
            momentrates_arr = numpy.array(momentrate.momentrateFromActivity(
                a_values, b_bz_arr, parameters[mmax_bg_name])) / catalog_time_span

            parameters['mr_act_list'] = momentrates_arr.tolist()
            parameters[mr_act_buf_name] = ' '.join(
                ["%.3e" % (x) for x in parameters['mr_act_list']])
                
            # moment rates from activity: use a and b values from FBZ 
            # (above threshold)

            act_fbz_at_arr_a = parameters[afbz_at_a_name].strip().split()
            act_fbz_at_arr_b = parameters[afbz_at_b_name].strip().split()
            
            a_fbz_at_arr = [float(x) for x in act_fbz_at_arr_a]
            b_fbz_at_arr = [float(x) for x in act_fbz_at_arr_b]
            
            a_values = a_fbz_at_arr
            momentrates_fbz_at_arr = numpy.array(momentrate.momentrateFromActivity(
                a_values, b_fbz_at_arr, parameters[mmax_bg_name])) / catalog_time_span

            parameters['mr_act_fbz_at_list'] = momentrates_fbz_at_arr.tolist()
            parameters[mr_act_fbz_name] = ' '.join(
                ["%.3e" % (x) for x in parameters['mr_act_fbz_at_list']])
            
            #parameters['activity_m_threshold'] = m_threshold
            
            ## moment rate from slip rate

            # TODO(fab): check correct scaling of moment rate from slip rate
            (moment_rate_min, moment_rate_max) = \
                momentrate.momentrateFromSlipRate(parameters[sliprate_min_name], 
                    parameters[sliprate_max_name], 
                    parameters[area_fault_sqkm_name] * 1.0e6)

            #parameters['mr_slip'] = [moment_rate_min, moment_rate_max]
            
            # ------------------------------------------------------------------
            
            attribute_list = []
            attribute_list.extend([
                float(parameters[mr_eq_name]),
                str(parameters[mr_act_buf_name]),
                str(parameters[mr_act_fbz_name]),
                float(moment_rate_min),
                float(moment_rate_max),
                int(parameters[eq_count_bz_name]),
                float(parameters[area_bz_sqkm_name]),
                float(parameters[area_fault_sqkm_name])])

        result_values.append(attribute_list)
        out_parameters.append(parameters)
        
        if ui_mode is False:
            print "FSZ (id %s), moment rate: %s" % (feature.id(), 
                str(attribute_list))

    return (result_values, out_parameters)

def getEmptyMaxLikelihoodABAttributeList():
    
    attribute_list = []
    
    # a_ml
    attribute_list.append(attributes.EMPTY_REAL_ATTR)
    
    # b_ml
    attribute_list.append(attributes.EMPTY_REAL_ATTR)
    
    # mc_ml
    attribute_list.append(attributes.EMPTY_REAL_ATTR)
    
    # magctr_ml
    attribute_list.append(attributes.EMPTY_INTEGER_ATTR)
    
    # mcmethod
    attribute_list.append(qpfmd.DEFAULT_MC_METHOD)
    
    # eq_count_fbz
    attribute_list.append(attributes.EMPTY_INTEGER_ATTR)
    
    # area_fbz_sqkm
    attribute_list.append(attributes.EMPTY_REAL_ATTR)
    
    return attribute_list
                
def getEmptyMomentRateAttributeList():
    """Return list of empty feature attributes."""

    attribute_list = []
    
    # mr_eq
    attribute_list.append(attributes.EMPTY_REAL_ATTR)
    
    # mr_activity_str
    attribute_list.append(attributes.EMPTY_STRING_ATTR)
    
    # mr_activity_fbz_at_str
    attribute_list.append(attributes.EMPTY_STRING_ATTR)
            
    # moment_rate_min
    attribute_list.append(attributes.EMPTY_REAL_ATTR)
    
    # moment_rate_max
    attribute_list.append(attributes.EMPTY_REAL_ATTR)
    
    # eq_count_bz
    attribute_list.append(attributes.EMPTY_INTEGER_ATTR)
    
    # area_bz_sqkm
    attribute_list.append(attributes.EMPTY_REAL_ATTR)
    
    # area_fault_sqkm
    attribute_list.append(attributes.EMPTY_REAL_ATTR)
    
    return attribute_list
