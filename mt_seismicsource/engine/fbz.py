# -*- coding: utf-8 -*-
"""
SHARE Seismic Source Toolkit

Attribute computation on FBZ layer.

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
