# -*- coding: utf-8 -*-
"""
SHARE Seismic Source Toolkit

Attribute computation on ASZ layer.

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

from mt_seismicsource.engine import fmd

from mt_seismicsource.layers import areasource
from mt_seismicsource.layers import eqcatalog

def computeASZ(layer, catalog, data_in, mindepth=eqcatalog.CUT_DEPTH_MIN,
    maxdepth=eqcatalog.CUT_DEPTH_MAX, catalog_time_span=None, 
    mc_method=qpfmd.DEFAULT_MC_METHOD, mc=None, ui_mode=True):
    """Compute attributes on selected features of ASZ layer.
    
    Output:
        parameters      Parameters that do not go into feature attributes.
    """
    
    # check that at least one feature is selected
    if not utils.check_at_least_one_feature_selected(layer):
        return

    (cat_depthcut, catalog_time_span) = engine.prepareEQCatalog(catalog, 
        catalog_time_span, mindepth, maxdepth)
        
    updateASZAtticIvy(layer, catalog, mindepth, maxdepth, ui_mode)
    
    parameters_ml_ab = updateASZMaxLikelihoodAB(layer, cat_depthcut, 
        catalog_time_span, mc_method, mc, ui_mode)
    parameters_mr = updateASZMomentRate(layer, cat_depthcut, 
        catalog_time_span, data_in, ui_mode)
        
    parameters = parameters_ml_ab
    for param_idx, parameter in enumerate(parameters):
        parameter.update(parameters_mr[param_idx])
    
    return parameters

def updateASZAtticIvy(layer, catalog, mindepth=eqcatalog.CUT_DEPTH_MIN,
    maxdepth=eqcatalog.CUT_DEPTH_MAX, ui_mode=True):
    """Update AtticIvy attributes on ASZ layer."""
    
    atticivy.assignActivityAtticIvy(layer, catalog, atticivy.ATTICIVY_MMIN,
        mindepth, maxdepth, ui_mode)

def updateASZMaxLikelihoodAB(layer, catalog, catalog_time_span, 
    mc_method=qpfmd.DEFAULT_MC_METHOD, mc=None, ui_mode=True):
    """Update max likelihood a/b value attributes on ASZ layer."""

    ab_attributes = (features.AREA_SOURCE_ATTR_A_ML, 
        features.AREA_SOURCE_ATTR_B_ML, features.AREA_SOURCE_ATTR_MC, 
        features.AREA_SOURCE_ATTR_MAGCTR_ML,
        features.AREA_SOURCE_ATTR_MC_METHOD)
        
    (ab_values, parameters) = computeMaxLikelihoodAB(layer, catalog, 
        catalog_time_span, mc_method, mc, ui_mode)
    attributes.writeLayerAttributes(layer, ab_attributes, ab_values)
    
    return parameters
        
def updateASZMomentRate(layer, catalog, catalog_time_span, data_in, 
    ui_mode=True):
    """Update seismic moment rate attributes on ASZ layer."""
    
    mr_attributes = []
    mr_attributes.extend(features.AREA_SOURCE_ATTRIBUTES_MOMENTRATE)
    mr_attributes.extend(features.AREA_SOURCE_ATTRIBUTES_MISC)
        
    (mr_values, parameters) = computeMomentRate(layer, catalog, 
        catalog_time_span, data_in, ui_mode)
    attributes.writeLayerAttributes(layer, mr_attributes, mr_values)
    
    return parameters
    
def computeMaxLikelihoodAB(layer, catalog, catalog_time_span, 
    mc_method=qpfmd.DEFAULT_MC_METHOD, mc=None, ui_mode=True):
    """Compute a and b values with maximum likelihood method.
    
    Input:
        catalog     QPCatalog that is already cut at min/max depth
        
    Returns a list of 4-tuples:
    (ml_a, ml_b, ml_mc, ml_magctr, mc_method)
    """
    
    fts = layer.selectedFeatures()
    
    if ui_mode is False:
        print "\n=== Computing MaxLikelihoodAB for %s features ===" % len(fts)

    result_values = []
    out_parameters = []
    
    # loop over features
    for zone_idx, feature in enumerate(fts):

        parameters = {}
        
        # get Shapely polygon from feature geometry
        polylist, vertices = utils.polygonsQGS2Shapely((feature,))
        poly = polylist[0]
    
        # get quakes from catalog (cut with polygon)
        poly_cat = QPCatalog.QPCatalog()
        poly_cat.merge(catalog)
        poly_cat.cut(geometry=poly)
    
        ## Maximum likelihood a/b values
        if poly_cat.size() == 0:
            parameters['fmd'] = None
            attribute_list = [float(numpy.nan), float(numpy.nan), 
                float(numpy.nan), 0, qpfmd.DEFAULT_MC_METHOD]
                
            error_msg = "max likelihood AB: no EQs in zone with ID %s" % (
                feature.id())
            if ui_mode is True:
                QMessageBox.warning(None, "Max likelihood AB", error_msg)
            else:
                print error_msg
            
        else:
            parameters['fmd'] = fmd.computeZoneFMD(feature, poly_cat, 
                catalog_time_span, mc_method, mc)
            attribute_list = list(fmd.getFMDValues(parameters['fmd']))

            if ui_mode is False:
                print "FMD: %s" % str(attribute_list)
                
        result_values.append(attribute_list)
        out_parameters.append(parameters)
    
    return (result_values, out_parameters)
    
def computeMomentRate(layer, catalog, catalog_time_span, data_in, ui_mode=True):
    """Compute moment rate contributions for ASZ layer.
    
    Input:
        catalog     QPCatalog that is already cut at min/max depth
        data_in     Data object that holds additional data sets, like
                    global strain and tectonic regimes
    
    Returns a list of 6-tuples:
    (mr_eq, mr_activity_str, mr_strain_barba, mr_strain_bird, area_sqkm, 
        eq_count)
    """
    
    fts = layer.selectedFeatures()
    
    # get attribute index of AtticIvy result
    provider = layer.dataProvider()
    attribute_map = utils.getAttributeIndex(provider, 
        (features.AREA_SOURCE_ATTR_ACT_RM_A, 
            features.AREA_SOURCE_ATTR_ACT_RM_B, 
            features.AREA_SOURCE_ATTR_MMAX))

    attribute_act_a_name = features.AREA_SOURCE_ATTR_ACT_RM_A['name']
    attribute_act_a_idx = attribute_map[attribute_act_a_name][0]

    attribute_act_b_name = features.AREA_SOURCE_ATTR_ACT_RM_B['name']
    attribute_act_b_idx = attribute_map[attribute_act_b_name][0]

    attribute_mmax_name = features.AREA_SOURCE_ATTR_MMAX['name']
    attribute_mmax_idx = attribute_map[attribute_mmax_name][0]
        
    if ui_mode is False:
        print "\n=== Computing moment rate for %s features ===" % len(fts)
        
    result_values = []
    out_parameters = []
    
    # loop over features
    for zone_idx, feature in enumerate(fts):
        
        parameters = {}
        
        # get Shapely polygon from feature geometry
        polylist, vertices = utils.polygonsQGS2Shapely((feature,))
        poly = polylist[0]
    
        # get polygon area in square kilometres
        parameters['area_sqkm'] = utils.polygonAreaFromWGS84(poly) * 1.0e-6

        # zone ID and title
        (feature_id, feature_title, feature_name) = utils.getFeatureAttributes(
            layer, feature, features.AREA_SOURCE_ATTRIBUTES_ID)
            
        if feature_title.toString() == '' and feature_name.toString() == '':
            zone_name_str = ""
        elif feature_title.toString() == '' and feature_name.toString() != '':
            zone_name_str = feature_name.toString()
        elif feature_title.toString() != '' and feature_name.toString() == '':
            zone_name_str = feature_title.toString()
        else:
            zone_name_str = "%s, %s" % (
                feature_title.toString(), feature_name.toString())
        
        parameters['plot_title_fmd'] = "Zone %s, %s" % (
            feature_id.toInt()[0], zone_name_str)

        ## moment rate from EQs

        # get quakes from catalog (cut with polygon)
        poly_cat = QPCatalog.QPCatalog()
        poly_cat.merge(catalog)
        poly_cat.cut(geometry=poly)

        parameters['eq_count'] = poly_cat.size()
        
        # sum up moment from quakes (converted from Mw with Kanamori eq.)
        magnitudes = []
        for ev in poly_cat.eventParameters.event:
            mag = ev.getPreferredMagnitude()
            magnitudes.append(mag.mag.value)

        moment = numpy.array(momentrate.magnitude2moment(magnitudes))

        # scale moment: per year and area (in km^2)
        parameters['mr_eq'] = moment.sum() / (
            parameters['area_sqkm'] * catalog_time_span)
        
        ## moment rate from activity (RM)

        # get RM (a, b) values from feature attributes
        try:
            activity_a_str = str(feature[attribute_act_a_idx].toString())
            activity_a_arr = activity_a_str.strip().split()
        except KeyError:
            activity_a_arr = [numpy.nan]
            error_msg = "No valid activity a parameter in %s" % (
                parameters['plot_title_fmd'])
            if ui_mode is True:
                QMessageBox.warning(None, "MomentRate", error_msg)
            else:
                print error_msg
        try:
            activity_b_str = str(feature[attribute_act_b_idx].toString())
            activity_b_arr = activity_b_str.strip().split()
        except KeyError:
            activity_b_arr = [numpy.nan]
            error_msg = "No valid activity b parameter in %s" % (
                parameters['plot_title_fmd'])
            if ui_mode is True:
                QMessageBox.warning(None, "MomentRate", error_msg)
            else:
                print error_msg
            
        # ignore weights
        parameters['activity_mmin'] = atticivy.ATTICIVY_MMIN
        parameters['activity_a'] = [float(x) for x in activity_a_arr]
        parameters['activity_b'] = [float(x) for x in activity_b_arr]
        parameters['mmax'] = float(feature[attribute_mmax_idx].toDouble()[0])

        momentrates_arr = numpy.array(momentrate.momentrateFromActivity(
            parameters['activity_a'], parameters['activity_b'], 
            parameters['mmax'])) / catalog_time_span
        parameters['mr_activity'] = momentrates_arr.tolist()
        parameters['mr_activity_str'] = ' '.join(
            ["%.3e" % (x) for x in parameters['mr_activity']])

        ## moment rate from geodesy (strain)
        momentrate_strain_barba = momentrate.momentrateFromStrainRateBarba(
            poly, data_in.strain_rate_barba, data_in.deformation_regimes_bird)
        parameters['mr_strain_barba'] = \
            momentrate_strain_barba / catalog_time_span

        momentrate_strain_bird = momentrate.momentrateFromStrainRateBird(poly, 
            data_in.strain_rate_bird, data_in.deformation_regimes_bird)
        parameters['mr_strain_bird'] = \
            momentrate_strain_bird / catalog_time_span

        attribute_list = []
        attribute_list.extend([float(parameters['mr_eq']),
            str(parameters['mr_activity_str']), 
            float(parameters['mr_strain_barba']),
            float(parameters['mr_strain_bird'])])
        
        attribute_list.extend([float(parameters['area_sqkm']), 
            int(parameters['eq_count'])])
            
        if ui_mode is False:
            print "Moment rate: %s" % str(attribute_list)
                
        result_values.append(attribute_list)
        out_parameters.append(parameters)
        
    return (result_values, out_parameters)
