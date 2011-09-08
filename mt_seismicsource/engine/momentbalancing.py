# -*- coding: utf-8 -*-
"""
SHARE Seismic Source Toolkit

Various computations on area and fault source layers.

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
from mt_seismicsource.algorithms import recurrence

from mt_seismicsource.engine import fmd

from mt_seismicsource.layers import areasource
from mt_seismicsource.layers import eqcatalog

# ----------------------------------------------------------------------------

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


# ----------------------------------------------------------------------------

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


# ----------------------------------------------------------------------------

def updateDataFaultBackgr(cls, feature, 
    m_threshold=recurrence.FAULT_BACKGROUND_MAG_THRESHOLD):
    """Update or compute moment rates for selected feature of fault background
    zone layer.

    Input:
        feature         QGis polygon feature from fault background zone layer

    Output:
        parameters      dict of computed parameters
    """

    provider = cls.fault_background_layer.dataProvider()
    provider_fault = cls.fault_source_layer.dataProvider()
    provider_area = cls.area_source_layer.dataProvider()
    provider_back = cls.background_zone_layer.dataProvider()

    parameters = {}

    # get Shapely polygon from feature geometry
    polylist, vertices = utils.polygonsQGS2Shapely((feature,))
    poly = polylist[0]

    # get polygon area in square kilometres
    parameters['area_background_sqkm'] = \
        utils.polygonAreaFromWGS84(poly) * 1.0e-6

    # get mmax and mcdist for FBZ from background zone
    (mcdist_qv, mmax_qv) = areasource.getAttributesFromBackgroundZones(
        poly.centroid, provider_back, areasource.MCDIST_MMAX_ATTRIBUTES)
        
    mmax = float(mmax_qv.toDouble()[0])
    mcdist = str(mcdist_qv.toString())

    parameters['mmax'] = mmax 
    
    ## moment rate from EQs

    # get quakes from catalog (cut with fault background zone polygon)
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
        parameters['area_background_sqkm'] * cls.catalog_time_span[0])

    ## moment rate from activity (RM)
    
    parameters['activity_mmin'] = atticivy.ATTICIVY_MMIN
    activity = atticivy.computeActivityAtticIvy(
        (poly, ), (mmax, ), (mcdist, ), cls.catalog, 
        mmin=parameters['activity_mmin'])
    
    # get RM (a, b) values from feature attribute
    activity_str_a = activity[0][3]
    activity_arr_a = activity_str_a.strip().split()
    activity_str_b = activity[0][4]
    activity_arr_b = activity_str_b.strip().split()
    
    # ignore weights
    activity_a = [float(x) for x in activity_arr_a]
    activity_b = [float(x) for x in activity_arr_b]
    parameters['activity_a'] = activity_a
    parameters['activity_b'] = activity_b 
    
    a_values = activity_a
    momentrates_arr = numpy.array(momentrate.momentrateFromActivity(
        a_values, activity_b, mmax)) / cls.catalog_time_span[0]
    parameters['mr_activity'] = momentrates_arr.tolist()
    
    # get separate catalogs below and above magnitude threshold
    cat_below_threshold = QPCatalog.QPCatalog()
    cat_below_threshold.merge(poly_cat)
    cat_below_threshold.cut(maxmag=m_threshold, maxmag_excl=True)
    parameters['eq_count_below'] = cat_below_threshold.size()
        
    cat_above_threshold = QPCatalog.QPCatalog()
    cat_above_threshold.merge(poly_cat)
    cat_above_threshold.cut(minmag=m_threshold, maxmag_excl=False)
    parameters['eq_count_above'] = cat_above_threshold.size()

    activity_below_threshold = atticivy.computeActivityAtticIvy(
        (poly,), (mmax,), (mcdist,), cat_below_threshold, 
        mmin=parameters['activity_mmin'])

    activity_above_threshold = atticivy.computeActivityAtticIvy(
        (poly,), (mmax,), (mcdist,), cat_above_threshold, 
        mmin=parameters['activity_mmin'])
        
    # get RM (weight, a, b) values from feature attribute
    activity_below_str_a = activity_below_threshold[0][3]
    activity_below_arr_a = activity_below_str_a.strip().split()
    activity_below_str_b = activity_below_threshold[0][4]
    activity_below_arr_b = activity_below_str_b.strip().split()
    
    activity_above_str_a = activity_above_threshold[0][3]
    activity_above_arr_a = activity_above_str_a.strip().split()
    activity_above_str_b = activity_above_threshold[0][4]
    activity_above_arr_b = activity_above_str_b.strip().split()
    
    # ignore weights
    activity_below_a = [float(x) for x in activity_below_arr_a]
    activity_below_b = [float(x) for x in activity_below_arr_b]

    activity_above_a = [float(x) for x in activity_above_arr_a]
    activity_above_b = [float(x) for x in activity_above_arr_b]
    
    a_values_below = activity_below_a
    momentrates_below_arr = numpy.array(momentrate.momentrateFromActivity(
        a_values_below, activity_below_b, mmax)) / cls.catalog_time_span[0]
            
    a_values_above = activity_above_a
    momentrates_above_arr = numpy.array(momentrate.momentrateFromActivity(
        a_values_above, activity_above_b, mmax)) / cls.catalog_time_span[0]
            
    parameters['activity_below_a'] = activity_below_a
    parameters['activity_below_b'] = activity_below_b 
    
    parameters['activity_above_a'] = activity_above_a
    parameters['activity_above_b'] = activity_above_b 
    
    parameters['mr_activity_below'] = momentrates_below_arr.tolist()
    parameters['mr_activity_above'] = momentrates_above_arr.tolist()
    
    parameters['activity_m_threshold'] = m_threshold
    
    # FMD from quakes in FBZ
    cls.feature_data_fault_background['fmd'] = fmd.computeZoneFMD(cls, 
        feature, poly_cat)
    (parameters['ml_a'], parameters['ml_b'], parameters['ml_mc'], 
        parameters['ml_magctr']) = fmd.getFMDValues(
            cls.feature_data_fault_background['fmd'])
            
    ## moment rate from slip rate

    sliprate_min_name = features.FAULT_SOURCE_ATTR_SLIPRATE_MIN['name']
    sliprate_max_name = features.FAULT_SOURCE_ATTR_SLIPRATE_MAX['name']

    attribute_map = utils.getAttributeIndex(provider_fault, 
        (features.FAULT_SOURCE_ATTR_SLIPRATE_MIN,
         features.FAULT_SOURCE_ATTR_SLIPRATE_MAX), create=False)
    
    moment_rate_min = 0.0
    moment_rate_max = 0.0
    parameters['area_fault_sqkm'] = 0.0
    parameters['fault_count'] = 0
    
    provider_fault.rewind()
    for fault in provider_fault:
        
        fault_poly, vertices = utils.polygonsQGS2Shapely((fault,))
        if fault_poly[0].intersects(poly):
            
            parameters['fault_count'] += 1
            
            sliprate_min = \
                fault[attribute_map[sliprate_min_name][0]].toDouble()[0]
            sliprate_max = \
                fault[attribute_map[sliprate_max_name][0]].toDouble()[0]
            area_fault = utils.polygonAreaFromWGS84(fault_poly[0])
            
            # TODO(fab): correct scaling of moment rate from slip rate
            (rate_min, rate_max) = momentrate.momentrateFromSlipRate(
                sliprate_min, sliprate_max, area_fault)
            
            moment_rate_min += rate_min
            moment_rate_max += rate_max
            parameters['area_fault_sqkm'] += area_fault
            
    moment_rate_min /= cls.catalog_time_span[0]
    moment_rate_max /= cls.catalog_time_span[0]
    
    parameters['mr_slip'] = [moment_rate_min, moment_rate_max]
    parameters['area_fault_sqkm'] *= 1.0e-6

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
