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

# minimum magintude for recurrence computation
MAGNITUDE_MIN = 5.0

# magnitude binning of result FMD
MAGNITUDE_BINNING = 0.1

# shear modulus (mu, rigidity) for all faults, in GPa
SHEAR_MODULUS = 3.0e07

# parameter c in Bungum paper, Table 1, line 7
C_BUNGUM = 16.05

# parameter d in Bungum paper, Table 1, line 7
D_BUNGUM = 1.5

# parameter alpha in Bungum paper, Table 1, line 9
# this is fault slip to fault length ratio
# this could in principle be computed from geometry of fault polygon
# and annual slip rate integrated over time
ALPHA_BUNGUM = 1.0e-04

# fault length to fault width factor, Bungum paper, Table 1, line 10
# this could be determined from geometry of fault polygon, but seems hard
# to do
FAULT_ASPECT_RATIO = 2.0

# buffer around fault polygons, in km
BUFFER_AROUND_FAULT_POLYGONS = 30.0

def assignRecurrence(provider_fault, provider_area=None, catalog=None):
    """Compute recurrence parameters according to Bungum paper. Add
    total seismic moment rate and activity rate as attributes to fault polygon
    layer.

    Input:
        provider_fault  QGis layer provider for fault polygon layer
        provider_area   QGis layer provider for area source zone layer
        catalog         earthquake catalog as QuakePy object
    """

    # get attribute indexes
    provider_fault.select()
    attribute_map = utils.getAttributeIndex(provider_fault, 
        features.FAULT_SOURCE_ATTRIBUTES_RECURRENCE_COMPUTE, create=True)

    provider_fault.rewind()
    recurrence = computeRecurrence(provider_fault, provider_area, catalog)

    QMessageBox.information(None, "Recurrence", "%s" % repr(recurrence))

    # assemble value dict
    values = {}
    provider_fault.rewind()
    for zone_idx, zone in utils.walkValidPolygonFeatures(provider_fault):

        attributes = {}
        for attr_idx, attr_dict in enumerate(
            features.FAULT_SOURCE_ATTRIBUTES_RECURRENCE_COMPUTE):
            (curr_idx, curr_type) = attribute_map[attr_dict['name']]
            try:
                attributes[curr_idx] = QVariant(recurrence[1][zone_idx][attr_idx])
            except Exception, e:
                error_str = \
        "error in attribute: curr_idx: %s, zone_idx: %s, attr_idx: %s, %s" % (
                    curr_idx, zone_idx, attr_idx, e)
                raise RuntimeError, error_str

        values[zone.id()] = attributes

    try:
        provider_fault.changeAttributeValues(values)
    except Exception, e:
        error_str = "cannot update attribute values, %s" % (e)
        raise RuntimeError, error_str

    return recurrence[0]

def computeRecurrence(provider_fault, provider_area=None, catalog=None):
    """Compute recurrence parameters according to Bungum paper. 

    Output:
        (total seismic moment rate (summed over all fault zones),
         [activity rate values per fault polygon (string),
          extrapolated occurrence (M=0) per fault polygon (float)]
        )
    

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
    total_seismic_moment_rate = 0.0

    # loop over fault polygons
    for zone_idx, zone in utils.walkValidPolygonFeatures(provider_fault):

        zone_data_string = ""

        # get attribute values of zone:
        # - MAXMAG, SLIPRATEMA
        attribute_map = utils.getAttributeIndex(provider_fault, 
            features.FAULT_SOURCE_ATTRIBUTES_RECURRENCE, create=True)
        
        # get maximum magnitude
        # (curr_idx, curr_type) = attribute_map['MAXMAG']
        maxmag = zone[attribute_map['MAXMAG'][0]].toDouble()[0]

        # get maximum of annual slip rate (parameter D ??)
        # (curr_idx, curr_type) = attribute_map['SLIPRATEMA']
        slipratema = zone[attribute_map['SLIPRATEMA'][0]].toDouble()[0]

        # TODO(fab): 
        # find corresponding large background zone (from RM zonation)
        # get b-value (RM method) from background zone (either already stored
        # in layer, or compute on-the-fly)
        b_value = 1.0

        # TODO(fab): 
        # get properties of fault polygon (area, length, width)
        # CHECK(fab): do we need length and width, or is just the area required?
        # NOTE: length and width are non-trivial to determine!
        #       since CRS is degrees, we have an area of square degrees
        #       -> convert to square metres

        # convert fault polygon to Shapely
        fault_poly, fault_vertices = utils.polygonsQGS2Shapely((zone,))

        poly_area_deg = fault_poly[0].area
        poly_center = fault_poly[0].centroid

        # get coordinates of polygon centre
        area_metres = poly_area_deg * numpy.power((40000 * 1000 / 360.0), 2) *\
            numpy.cos(numpy.pi * float(poly_center.y) / 180.0)

        # equidistant magnitude array on which activity rates are computed
        # from global Mmin to zone-dependent Mmax
        # TODO(fab): THIS IS A WRONG APPROACH
        # we have to loop over fault lengths until we reach Mmax given in the
        # fault shapefile
        mag_arr = numpy.arange(MAGNITUDE_MIN, maxmag, MAGNITUDE_BINNING)

        cumulative_number = cumulative_occurrence_model_2(mag_arr, maxmag, 
            slipratema, b_value, area_metres)

        extrapolated_value = cumulative_occurrence_model_2(0.0, maxmag, 
            slipratema, b_value, area_metres)

        # compute contribution to total seismic moment
        seismic_moment_rate = (1.0e8 * SHEAR_MODULUS) * \
            (slipratema / 10.0) * (area_metres * 1.0e4)
        total_seismic_moment_rate += seismic_moment_rate

        # serialize activity rate FMD
        # TODO(fab): formatting of floating point numbers
        for value_pair_idx in xrange(mag_arr.shape[0]):
            zone_data_string = "%s %.1f %.2e" % (zone_data_string, 
                mag_arr[value_pair_idx], cumulative_number[value_pair_idx])
        
        result_values.append([zone_data_string.lstrip(), seismic_moment_rate,
            extrapolated_value])

    return (total_seismic_moment_rate, result_values)

def cumulative_occurrence_model_2(mag_arr, maxmag, slipratema, b_value, 
    area_metres):
    """Compute cumulative occurrence rate for given magnitude (model 2,
    eq. 7 in Bungum paper.

    Input:
        mag_arr     array of target magnitudes (CHANGE)
        maxmag      maximum magnitude of fault
        slipratema  maximum annual slip rate (mm/yr) ?
        b_value     b value of background seismicity
        area_metres fault area in metres
    
    """

    # re-scaled parameters, as given for eq. 5 in Bungum paper
    # b value of background seismicity
    b_bar = b_value * numpy.log(10.0)

    # d coefficient from scaling ratio of seismic moment to
    # moment magnitude
    d_bar = D_BUNGUM * numpy.log(10.0)
    
    # alpha is the ratio of total displacement across the fault 
    # and fault length. Use fixed parameter value.
    alpha = ALPHA_BUNGUM

    # Original equation has W (fault width) in denominator, we replace 
    # this with fault area (which we get from geometry), 
    # and fixed fault length/width ratio
    beta_numerator = alpha * C_BUNGUM

    # convert shear modulus from GPa (10^9 N/m^2, 10^9 kg/(m * s^2)) 
    # to dyn/cm^2, 1 dyn = 1 g * cm/s^2 = 10^-5 N
    # 1 GPa = 10^9 kg/(m * s^2) = 10^12 g/(m * s^2) = 10^10 g/(cm *s^2) 
    # = 10^10 dyn/cm^2
    # convert area from square metres to square centimetres
    beta_denominator = 1.0e10 * SHEAR_MODULUS * numpy.sqrt(
        area_metres * 100 * 100/ FAULT_ASPECT_RATIO)
    beta = numpy.sqrt(beta_numerator / beta_denominator)

    # factors in Bungum eq. 7
    f1 = (d_bar - b_bar) / b_bar

    # convert annual slip rate from mm/yr to cm/yr 
    f2 = slipratema / (10 * beta)
    f3 = numpy.exp(b_bar * (maxmag - mag_arr)) - 1
    f4 = numpy.exp(-0.5 * d_bar * maxmag)

    # compute activity rate per fault polygon
    cumulative_number = f1 * f2 * f3 * f4

    return cumulative_number