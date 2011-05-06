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

# shear modulus (mu, rigidity) for all faults
SHEAR_MODULUS = 1.0

# buffer around fault polygons, in km
BUFFER_AROUND_FAULT_POLYGONS = 30.0

def assignRecurrence(provider_fault, provider_area, catalog, truncate=False):
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
        features.FAULT_SOURCE_ATTRIBUTES_RECURRENCE, create=True)

    provider_fault.rewind()
    recurrence = computeRecurrence(provider_fault, provider_area, catalog, 
        truncate)

    # assemble value dict
    values = {}
    provider_fault.rewind()
    for zone_idx, zone in utils.walkValidPolygonFeatures(provider_fault):

        attributes = {}
        for attr_idx, attr_dict in enumerate(
            features.FAULT_SOURCE_ATTRIBUTES_RECURRENCE):
            (curr_idx, curr_type) = attribute_map[attr_dict['name']]
            try:
                attributes[curr_idx] = QVariant(recurrence[zone_idx][attr_idx])
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

def computeRecurrence(provider_fault, provider_area, catalog, truncate=False):
    """Compute recurrence parameters according to Bungum paper. 

    Output (per fault polygon):
        total seismic moment rate
        activity rate 

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

    % Model 1, no truncation at Mmax
    rParams.nModel = 1; 
    [vCumNumber1,vMagnitude] = calc_RecurrenceModel(rParams);

    % Model 2, no truncation at Mmax
    rParams.nModel = 2; 
    [vCumNumber2,vMagnitude] = calc_RecurrenceModel(rParams);
    """

    # loop over fault polygons
    #   find corresponding large background zone (from RM zonation)
    #   get b-value (RM method) from background zone (either already stored
    #     in layer, or compute on-the-fly)
    #   get properties of fault polygon (area, length, width)
    #     -NOTE: length and width are non-trivial to determine!
    #   compute total seismic moment rate and activity rate per fault polygon
    return []
