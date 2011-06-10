# -*- coding: utf-8 -*-
"""
SHARE Seismic Source Toolkit

Python implementation of Hilmar Bungum's recurrence code.
See: Bungum (2007) Computers & Geosciences, 33, 808--820
     doi:10.1016/j.cageo.2006.10.011

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
import os
import shutil
import stat
import subprocess
import tempfile

from PyQt4.QtCore import *
from PyQt4.QtGui import *

from qgis.core import *

from mt_seismicsource import features
from mt_seismicsource import utils
from mt_seismicsource.algorithms import atticivy
from mt_seismicsource.algorithms import momentrate
from mt_seismicsource.layers import areasource

import QPCatalog

# minimum magintude for recurrence computation
MAGNITUDE_MIN = 5.0

# magnitude binning of result FMD
MAGNITUDE_BINNING = 0.1

# parameter alpha in Bungum paper, Table 1, line 9
# this is fault slip to fault length ratio
# this could in principle be computed from geometry of fault polygon
# and annual slip rate integrated over time
ALPHA_BUNGUM = 1.0e-04

# fault length to fault width factor, Bungum paper, Table 1, line 10
# this could be determined from geometry of fault polygon, but seems hard
# to do
FAULT_ASPECT_RATIO = 2.0

def assignRecurrence(layer_fault, layer_fault_background=None, 
    layer_background=None, catalog=None, b_value=None, 
    mmin=atticivy.ATTICIVY_MMIN):
    """Compute recurrence parameters according to Bungum paper. Add
    activity rates, a/b values, and min/max seismic moment rate 
    as attributes to fault polygon layer.

    Input:
        layer_fault              QGis layer with fault zone features
        layer_fault_background   QGis layer with fault background zone features
        layer_background         QGis layer with background zone features
                                 (provides Mmax and Mc distribution)
        catalog                  Earthquake catalog as QuakePy object
        b_value                  b value to be used for computation
    """

    if b_value is None and (layer_fault_background is None or \
        layer_background is None or catalog is None):
        error_msg = \
            "If no b value is given, the other parameters must not be None"
        raise RuntimeError, error_msg
        
    # get attribute indexes
    provider_fault = layer_fault.dataProvider()
    fts = layer_fault.selectedFeatures()

    attribute_map = utils.getAttributeIndex(provider_fault, 
        features.FAULT_SOURCE_ATTRIBUTES_RECURRENCE_COMPUTE, create=True)

    recurrence = computeRecurrence(layer_fault, layer_fault_background, 
        layer_background, catalog, b_value, mmin)

    # assemble value dict
    values = {}
    for zone_idx, zone in enumerate(fts):

        attributes = {}
        skipZone = False
        for attr_idx, attr_dict in enumerate(
            features.FAULT_SOURCE_ATTRIBUTES_RECURRENCE_COMPUTE):
            (curr_idx, curr_type) = attribute_map[attr_dict['name']]
            try:
                attributes[curr_idx] = QVariant(recurrence[zone_idx][attr_idx])
            except Exception, e:
                skipZone = True
                break
                #error_str = \
        #"error in attribute: curr_idx: %s, zone_idx: %s, attr_idx: %s, %s" % (
                    #curr_idx, zone_idx, attr_idx, e)
                #raise RuntimeError, error_str
        if skipZone is False:
            values[zone.id()] = attributes

    try:
        provider_fault.changeAttributeValues(values)
    except Exception, e:
        error_str = "cannot update attribute values, %s" % (e)
        raise RuntimeError, error_str

def computeRecurrence(layer_fault, layer_fault_background=None, 
    layer_background=None, catalog=None, b_value=None, 
    mmin=atticivy.ATTICIVY_MMIN):
    """Compute recurrence parameters according to Bungum paper. 

    Parameters from Jochen's Matlab implementation:

    % rParams.fBvalue : b-value 
    % rParams.fS      : Slip rate (mm/year)
    % rParams.fD      : Average slip (m)
    % rParams.fLength : Fault length (m)
    % rParams.fWidth  : Fault width (m)
    % rParams.fM00    : M0(0) for Ms = 0, c in logM0=c-dM
    % rParams.fMmin   : Minimum magnitude
    % rParams.fBinM   : magnitude binnning
    % rParams.fMmax   : Maximum magnitude
    % rParams.fDmoment : d in  logM0=c-dM
    % rParams.fRigid : Rgidity in Pascal

    rParams.fBvalue = 1;
    rParams.fS = 1e-3;
    rParams.fD = 1;
    rParams.fLength = 100000;
    rParams.fWidth = 50000;
    rParams.fM00  = 16.05;
    rParams.fMmin = 5;
    rParams.fBinM = 0.1;
    rParams.fMmax = 8;
    rParams.fDmoment = 1.5;
    rParams.fRigid = 30e+6;
    """

    result_values = []

    provider_fault = layer_fault.dataProvider()
    fts = layer_fault.selectedFeatures()

    # loop over fault polygons
    for zone_idx, zone in enumerate(fts):

        zone_data_string_min = ""
        zone_data_string_max = ""

        # get attribute values of zone:
        # - MAXMAG, SLIPRATEMI, SLIPRATEMA
        attribute_map = utils.getAttributeIndex(provider_fault, 
            features.FAULT_SOURCE_ATTRIBUTES_RECURRENCE, create=True)
        
        # get maximum magnitude
        maxmag = zone[attribute_map['MAXMAG'][0]].toDouble()[0]

        # get minimum of annual slip rate
        slipratemi = zone[attribute_map['SLIPRATEMI'][0]].toDouble()[0]

        # get maximum of annual slip rate
        slipratema = zone[attribute_map['SLIPRATEMA'][0]].toDouble()[0]

        if b_value is None:
            b_value = computeBValueFromBackground(zone,
                layer_fault_background, layer_background, catalog, mmin)

        # TODO(fab): 
        # get properties of fault polygon (area, length, width)
        # CHECK(fab): do we need length and width, or is just the area required?
        # NOTE: length and width are non-trivial to determine!
        #       since CRS is degrees, we have an area of square degrees
        #       -> convert to square metres

        # convert fault polygon to Shapely
        fault_poly, fault_vertices = utils.polygonsQGS2Shapely((zone,))
        area = utils.polygonAreaFromWGS84(fault_poly[0])

        # equidistant magnitude array on which activity rates are computed
        # from global Mmin to zone-dependent Mmax
        mag_arr = numpy.arange(MAGNITUDE_MIN, maxmag, MAGNITUDE_BINNING)

        cumulative_number_min = cumulative_occurrence_model_2(mag_arr, maxmag, 
            slipratemi, b_value, area)

        cumulative_number_max = cumulative_occurrence_model_2(mag_arr, maxmag, 
            slipratema, b_value, area)

        # use a value computed with max of slip rate
        a_value = getAValueFromOccurrence(cumulative_number_max[0], b_value,
            MAGNITUDE_MIN)
        
        # compute contribution to total seismic moment
        # TODO(fab): double-check scaling with Laurentiu!
        # shear modulus: Pa = N / m^2 = kg / (m * s^2) = kg / (10^-3 km * s^2)
        #                1 kg / (km * s^2) = 10^3 N
        # slip rate: mm / year
        # area: m^2
        # moment rate unit: Nm / (year * km^2)
        #  kg * 10^-3 m * m^2 / (m * s^2 * 365.25*24*60*60 s) 
        # = 10^3 N * 10^-3 m^3 / (10^-3 * [year] s))
        #  = 10^3 Nm * m^2 / [year] s <- divide this by area in metres (?)
        # kg m^3 / (m s^3) = kg m^2 / s^3
        (seismic_moment_rate_min, seismic_moment_rate_max) = \
            momentrate.momentrateFromSlipRate(slipratemi, slipratema, area)

        # serialize activity rate FMD
        for value_pair_idx in xrange(mag_arr.shape[0]):
            zone_data_string_min = "%s %.1f %.2e" % (zone_data_string_min, 
                mag_arr[value_pair_idx], 
                cumulative_number_min[value_pair_idx])
            zone_data_string_max = "%s %.1f %.2e" % (zone_data_string_max, 
                mag_arr[value_pair_idx], 
                cumulative_number_max[value_pair_idx])

        result_values.append(
            [a_value,
             b_value,
             zone_data_string_min.lstrip(), 
             zone_data_string_max.lstrip(), 
             seismic_moment_rate_min,
             seismic_moment_rate_max])

    return result_values

def cumulative_occurrence_model_2(mag_arr, maxmag, sliprate, b_value, 
    area_metres):
    """Compute cumulative occurrence rate for given magnitude (model 2,
    eq. 7 in Bungum paper.

    Input:
        mag_arr     array of target magnitudes (CHANGE)
        maxmag      maximum magnitude of fault
        sliprate    annual slip rate (mm/yr)
        b_value     b value of background seismicity
        area_metres fault area in metres
    
    """

    # re-scaled parameters, as given for eq. 5 in Bungum paper
    # b value of background seismicity
    b_bar = b_value * numpy.log(10.0)

    # d coefficient from scaling ratio of seismic moment to
    # moment magnitude
    d_bar = momentrate.CONST_KANAMORI_D * numpy.log(10.0)
    
    # alpha is the ratio of total displacement across the fault 
    # and fault length. Use fixed parameter value.
    alpha = ALPHA_BUNGUM

    beta_numerator = alpha * numpy.power(10, momentrate.CONST_KANAMORI_C_CGS)

    # convert shear modulus from Pa (N/m^2, kg/(m * s^2)) 
    # to dyn/cm^2, 1 dyn = 1 g * cm/s^2 = 10^-5 N
    # 1 GPa = 10^9 kg/(m * s^2) = 10^12 g/(m * s^2) = 10^10 g/(cm *s^2) 
    # = 10^10 dyn/cm^2
    # convert area from square metres to square centimetres

    # Original equation has W (fault width) in denominator, we replace 
    # this with fault area (which we get from geometry), 
    # and fixed fault length/width ratio
    beta_denominator = 1.0e10 * momentrate.SHEAR_MODULUS * numpy.sqrt(
        area_metres * 100 * 100 / FAULT_ASPECT_RATIO)
    beta = numpy.sqrt(beta_numerator / beta_denominator)

    # factors in Bungum eq. 7
    f1 = (d_bar - b_bar) / b_bar

    # convert annual slip rate from mm/yr to cm/yr 
    f2 = sliprate / (10 * beta)
    f3 = numpy.exp(b_bar * (maxmag - mag_arr)) - 1
    f4 = numpy.exp(-0.5 * d_bar * maxmag)

    # compute activity rate per fault polygon
    cumulative_number = f1 * f2 * f3 * f4

    return cumulative_number

def getAValueFromOccurrence(lg_occurrence, b_value, mmin=MAGNITUDE_MIN):
    return lg_occurrence + b_value * mmin
    
def computeBValueFromBackground(zone, layer_fault_background, layer_background,
    catalog, mmin=atticivy.ATTICIVY_MMIN):
    """
    Input:
        zone        fault source zone
    """
    
    provider_fault_back = layer_fault_background.dataProvider()
    provider_background = layer_background.dataProvider()
    
    # get Shapely polygon from feature geometry
    fault_polylist, vertices = utils.polygonsQGS2Shapely((zone,))
    fault_poly = fault_polylist[0]
    
    # find fault background zone in which centroid of fault zone lies
    provider_fault_back.rewind()
    fault_background_zone = utils.findBackgroundZone(fault_poly.centroid, 
        provider_fault_back)
        
    fbz_polylist, vertices = utils.polygonsQGS2Shapely((fault_background_zone,))
    fault_background_poly = fbz_polylist[0]
    
    # get mmax and mcdist for fault background zone from large background zone
    (mcdist_qv, mmax_qv) = areasource.getAttributesFromBackgroundZones(
        fault_background_poly.centroid, provider_background, 
        areasource.MCDIST_MMAX_ATTRIBUTES)
        
    mmax = float(mmax_qv.toDouble()[0])
    mcdist = str(mcdist_qv.toString())

    activity = atticivy.computeActivityAtticIvy((fault_background_poly, ), 
        (mmax, ), (mcdist, ), catalog, mmin)

    return activity[0][1]
        
    