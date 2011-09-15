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
from mt_seismicsource import features
from mt_seismicsource import utils

from mt_seismicsource.algorithms import atticivy
from mt_seismicsource.algorithms import momentrate
from mt_seismicsource.algorithms import recurrence

from mt_seismicsource.engine import fmd

from mt_seismicsource.layers import areasource
from mt_seismicsource.layers import eqcatalog

def computeFSZ(layer_fault, layer_fault_background, layer_background, catalog,
    data_in, catalog_time_span=None, b_value=None,
    mmin=atticivy.ATTICIVY_MMIN, 
    m_threshold=recurrence.FAULT_BACKGROUND_MAG_THRESHOLD,
    mindepth=eqcatalog.CUT_DEPTH_MIN, maxdepth=eqcatalog.CUT_DEPTH_MAX,
    mc_method=qpfmd.DEFAULT_MC_METHOD, mc=None,
    ui_mode=True):
    """Compute attributes on selected features of ASZ layer."""
    
    # check that at least one feature is selected
    if not utils.check_at_least_one_feature_selected(layer_fault):
        return

    if catalog_time_span is None:
        catalog_time_span = catalog.timeSpan()[0]
        
    # cut catalog with depth
    cat_depthcut = QPCatalog.QPCatalog()
    cat_depthcut.merge(catalog)
    
    # cut catalog with min/max depth
    cat_depthcut.cut(mindepth=mindepth, maxdepth=maxdepth)
    
    updateFSZRecurrence(layer_fault, layer_fault_background, layer_background,
        catalog, catalog_time_span, b_value, mmin, m_threshold, mindepth, 
        maxdepth, ui_mode)
    parameters_ml_ab = updateFSZMaxLikelihoodAB()
    parameters_mr = updateFSZMomentRate()

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

def updateFSZMaxLikelihoodAB(ui_mode=True):
    """Update max likelihood a/b value attributes on FSZ layer."""
    pass

def updateFSZMomentRate(ui_mode=True):
    """Update seismic moment rate attributes on FSZ layer."""
    pass


def updateDataFault(cls, feature,
    m_threshold=recurrence.FAULT_BACKGROUND_MAG_THRESHOLD):
    """Update or compute moment rates for selected feature of fault source
    zone layer.

    Input:
        feature         QGis polygon feature from fault source layer

    Output:
        parameters      dict of computed parameters
    """

    provider = cls.fault_source_layer.dataProvider()
    provider_fault_back = cls.fault_background_layer.dataProvider()
    provider_back = cls.background_zone_layer.dataProvider()

    parameters = {}

    # zone ID and title
    (feature_id, feature_name) = utils.getFeatureAttributes(
        cls.fault_background_layer, feature, 
        features.FAULT_BACKGROUND_ATTRIBUTES_ID)

    if feature_name.toString() != '':
        zone_name_str = feature_name.toString()
    else:
        zone_name_str = ""
    
    parameters['plot_title_recurrence'] = 'Zone %s, %s' % (
        feature_id.toString(), zone_name_str)
        
    # get Shapely polygon from feature geometry
    polylist, vertices = utils.polygonsQGS2Shapely((feature,))
    fault_poly = polylist[0]

    # fault zone polygon area in square kilometres
    parameters['area_fault_sqkm'] = utils.polygonAreaFromWGS84(
        fault_poly) * 1.0e-6

    # get buffer zone around fault zone (convert buffer distance to degrees)
    (bz_poly, parameters['area_bz_sqkm']) = utils.computeBufferZone(
        fault_poly, momentrate.BUFFER_AROUND_FAULT_ZONE_KM)

    # find fault background zone in which centroid of fault zone lies
    # NOTE: this can yield a wrong background zone if the fault zone
    # is curved and at the edge of background zone.
    # TODO(fab): use GIS "within" function instead, but note that fault
    # zone can overlap several BG zones
    (fbz, fbz_poly, parameters['area_fbz_sqkm']) = utils.findBackgroundZone(
        fault_poly.centroid, provider_fault_back)

    recurrence_attributes = attributes.getAttributesFromRecurrence(provider, 
        feature)
    
    if recurrence_attributes is not None:
        parameters.update(recurrence_attributes)
    else:
        return None
    
    # get mmax and mcdist for FBZ from background zone
    (mcdist_qv, mmax_qv) = areasource.getAttributesFromBackgroundZones(
        fbz_poly.centroid, provider_back, areasource.MCDIST_MMAX_ATTRIBUTES)
        
    mmax = float(mmax_qv.toDouble()[0])
    mcdist = str(mcdist_qv.toString())
    
    parameters['mmax'] = mmax
    
    ## moment rate from EQs

    # get quakes from catalog (cut with fault background polygon)
    # cut catalog with min/max depth according to UI spinboxes
    (mindepth, maxdepth) = eqcatalog.getMinMaxDepth(cls)
    
    fbz_cat = QPCatalog.QPCatalog()
    fbz_cat.merge(cls.catalog)
    fbz_cat.cut(geometry=fbz_poly)
    fbz_cat.cut(mindepth=mindepth, maxdepth=maxdepth)
    
    bz_cat = QPCatalog.QPCatalog()
    bz_cat.merge(cls.catalog)
    bz_cat.cut(geometry=bz_poly)
    bz_cat.cut(mindepth=mindepth, maxdepth=maxdepth)
    
    parameters['eq_count_fbz'] = fbz_cat.size()
    parameters['eq_count_bz'] = bz_cat.size()
    
    # sum up moment from quakes (converted from Mw with Kanamori eq.)
    # use quakes in buffer zone
    magnitudes = []
    for ev in bz_cat.eventParameters.event:
        mag = ev.getPreferredMagnitude()
        magnitudes.append(mag.mag.value)

    moment = numpy.array(momentrate.magnitude2moment(magnitudes))

    # scale moment: per year and area (in km^2)
    parameters['mr_eq'] = moment.sum() / (
        parameters['area_bz_sqkm'] * cls.catalog_time_span[0])

    ## moment rate from activity (RM)

    # moment rates from activity: use a and b values from buffer zone

    act_bz_arr_a = parameters['activity_bz_act_a'].strip().split()
    act_bz_arr_b = parameters['activity_bz_act_b'].strip().split()
    
    a_bz_arr = [float(x) for x in act_bz_arr_a]
    b_bz_arr = [float(x) for x in act_bz_arr_b]
    
    a_values = a_bz_arr
    momentrates_arr = numpy.array(momentrate.momentrateFromActivity(
        a_values, b_bz_arr, mmax)) / cls.catalog_time_span[0]

    parameters['mr_activity'] = momentrates_arr.tolist()

    # moment rates from activity: use a and b values from FBZ 
    # (above threshold)

    act_fbz_at_arr_a = parameters['activity_fbz_at_act_a'].strip().split()
    act_fbz_at_arr_b = parameters['activity_fbz_at_act_b'].strip().split()
    
    a_fbz_at_arr = [float(x) for x in act_fbz_at_arr_a]
    b_fbz_at_arr = [float(x) for x in act_fbz_at_arr_b]
    
    a_values = a_fbz_at_arr
    momentrates_fbz_at_arr = numpy.array(momentrate.momentrateFromActivity(
        a_values, b_fbz_at_arr, mmax)) / cls.catalog_time_span[0]

    parameters['mr_activity_fbz_at'] = momentrates_fbz_at_arr.tolist()
    
    parameters['activity_m_threshold'] = m_threshold

    # FMD from quakes in FBZ
    cls.feature_data_fault_source['fmd'] = fmd.computeZoneFMD(cls, feature, 
        fbz_cat)
    (parameters['ml_a'], parameters['ml_b'], parameters['ml_mc'], 
        parameters['ml_magctr']) = fmd.getFMDValues(
            cls.feature_data_fault_source['fmd'])
        
    ## moment rate from slip rate

    # TODO(fab): check correct scaling of moment rate from slip rate
    (moment_rate_min, moment_rate_max) = \
        momentrate.momentrateFromSlipRate(parameters['sliprate_min'], 
            parameters['sliprate_max'], 
            parameters['area_fault_sqkm'] * 1.0e6)

    parameters['mr_slip'] = [moment_rate_min, moment_rate_max]
    
    return parameters
