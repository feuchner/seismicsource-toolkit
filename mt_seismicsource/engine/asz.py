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

from mt_seismicsource import attributes
from mt_seismicsource import features
from mt_seismicsource import utils

from mt_seismicsource.algorithms import atticivy
from mt_seismicsource.algorithms import momentrate

from mt_seismicsource.engine import fmd

from mt_seismicsource.layers import areasource
from mt_seismicsource.layers import eqcatalog

def computeASZ(layer, catalog, mindepth=eqcatalog.CUT_DEPTH_MIN,
    maxdepth=eqcatalog.CUT_DEPTH_MAX, ui_mode=True):
    """Compute attributes on selected features of ASZ layer."""
    
    # check that at least one feature is selected
    if not utils.check_at_least_one_feature_selected(layer):
        return

    updateASZAtticIvy(layer, catalog, mindepth, maxdepth, ui_mode)
    updateASZMaxLikelihoodAB()
    updateASZMomentRate()

def updateASZAtticIvy(layer, catalog, mindepth=eqcatalog.CUT_DEPTH_MIN,
    maxdepth=eqcatalog.CUT_DEPTH_MAX, ui_mode=True):
    """Update AtticIvy attributes on ASZ layer."""
    
    atticivy.assignActivityAtticIvy(layer, catalog, atticivy.ATTICIVY_MMIN,
        mindepth, maxdepth, ui_mode)

def updateASZMaxLikelihoodAB(ui_mode=True):
    """Update max likelihood a/b value attributes on ASZ layer."""
    pass

def updateASZMomentRate(ui_mode=True):
    """Update seismic moment rate attributes on ASZ layer."""
    pass

def updateDataArea(cls, feature):
    """Update or compute moment rates for selected feature of area source
    zone layer.

    Input:
        feature         QGis polygon feature from area source layer

    Output:
        parameters      dict of computed parameters
    """

    provider = cls.area_source_layer.dataProvider()
    parameters = {}

    # get Shapely polygon from feature geometry
    polylist, vertices = utils.polygonsQGS2Shapely((feature,))
    poly = polylist[0]
    
    # get polygon area in square kilometres
    parameters['area_sqkm'] = utils.polygonAreaFromWGS84(poly) * 1.0e-6

    # zone ID and title
    (feature_id, feature_title, feature_name) = utils.getFeatureAttributes(
        cls.area_source_layer, feature, features.AREA_SOURCE_ATTRIBUTES_ID)
        
    if feature_title.toString() == '' and feature_name.toString() == '':
        zone_name_str = ""
    elif feature_title.toString() == '' and feature_name.toString() != '':
        zone_name_str = feature_name.toString()
    elif feature_title.toString() != '' and feature_name.toString() == '':
        zone_name_str = feature_title.toString()
    else:
        zone_name_str = "%s, %s" % (
            feature_title.toString(), feature_name.toString())
    
    parameters['plot_title_fmd'] = 'Zone %s, %s' % (
        feature_id.toInt()[0], zone_name_str)

    ## moment rate from EQs

    # get quakes from catalog (cut with polygon)
    poly_cat = QPCatalog.QPCatalog()
    poly_cat.merge(cls.catalog)
    poly_cat.cut(geometry=poly)
    
    # cut catalog with min/max depth according to UI spinboxes
    (mindepth, maxdepth) = eqcatalog.getMinMaxDepth(cls)
    poly_cat.cut(mindepth=mindepth, maxdepth=maxdepth)

    parameters['eq_count'] = poly_cat.size()
    
    # sum up moment from quakes (converted from Mw with Kanamori eq.)
    magnitudes = []
    for ev in poly_cat.eventParameters.event:
        mag = ev.getPreferredMagnitude()
        magnitudes.append(mag.mag.value)

    moment = numpy.array(momentrate.magnitude2moment(magnitudes))

    # scale moment: per year and area (in km^2)
    parameters['mr_eq'] = moment.sum() / (
        parameters['area_sqkm'] * cls.catalog_time_span[0])

    ## moment rate from activity (RM)

    # get attribute index of AtticIvy result
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

    # get RM (a, b) values from feature attributes
    try:
        activity_a_str = str(feature[attribute_act_a_idx].toString())
        activity_a_arr = activity_a_str.strip().split()
    except KeyError:
        activity_a_arr = 3 * [numpy.nan]
        error_msg = "Moment balancing: no valid activity a parameter in %s" % (
            parameters['plot_title_fmd'])
        QMessageBox.warning(None, "Moment balancing warning", error_msg)

    try:
        activity_b_str = str(feature[attribute_act_b_idx].toString())
        activity_b_arr = activity_b_str.strip().split()
    except KeyError:
        activity_b_arr = 3 * [numpy.nan]
        error_msg = "Moment balancing: no valid activity b parameter in %s" % (
            parameters['plot_title_fmd'])
        QMessageBox.warning(None, "Moment balancing warning", error_msg)
        
    # ignore weights
    parameters['activity_mmin'] = atticivy.ATTICIVY_MMIN
    activity_a = [float(x) for x in activity_a_arr]
    activity_b = [float(x) for x in activity_b_arr]
    mmax = float(feature[attribute_mmax_idx].toDouble()[0])
    
    parameters['activity_a'] = activity_a
    parameters['activity_b'] = activity_b 
    parameters['mmax'] = mmax 

    ## Maximum likelihood a/b values
    if poly_cat.size() == 0:
        cls.feature_data_area_source['fmd'] = None
        (parameters['ml_a'], parameters['ml_b'], parameters['ml_mc'], 
            parameters['ml_magctr']) = 4 * [numpy.nan]
        error_msg = "Moment balancing: no EQs in %s" % (
            parameters['plot_title_fmd'])
        QMessageBox.warning(None, "Moment balancing warning", error_msg)
    else:
        cls.feature_data_area_source['fmd'] = fmd.computeZoneFMD(cls, feature, 
            poly_cat)
        (parameters['ml_a'], parameters['ml_b'], parameters['ml_mc'], 
            parameters['ml_magctr']) = fmd.getFMDValues(
                cls.feature_data_area_source['fmd'])

    ## moment rate from activity
    a_values = activity_a
    momentrates_arr = numpy.array(momentrate.momentrateFromActivity(
        a_values, activity_b, mmax)) / cls.catalog_time_span[0]
    parameters['mr_activity'] = momentrates_arr.tolist()

    ## moment rate from geodesy (strain)
    momentrate_strain_barba = momentrate.momentrateFromStrainRateBarba(
        poly, cls.data.strain_rate_barba, 
        cls.data.deformation_regimes_bird)
    parameters['mr_strain_barba'] = momentrate_strain_barba / (
        cls.catalog_time_span[0])

    momentrate_strain_bird = momentrate.momentrateFromStrainRateBird(poly, 
        cls.data.strain_rate_bird, cls.data.deformation_regimes_bird)
    parameters['mr_strain_bird'] = momentrate_strain_bird / (
        cls.catalog_time_span[0])

    return parameters
