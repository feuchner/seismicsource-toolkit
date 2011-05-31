# -*- coding: utf-8 -*-
"""
SHARE Seismic Source Toolkit

Load strain rate datas set.

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
import numpy

import shapely.geometry
import shapely.ops

from PyQt4.QtCore import *
from PyQt4.QtGui import *

from mt_seismicsource import layers

STRAIN_DATA_DIR = 'strain'


# strain rate data file from Salvatore Barba

STRAIN_DATA_BARBA_FILE = 'strain_rate_ns_d09.dat'

# strain rate data file from Bird/Kreemer/Holt
# Bird, Kreemer & Holt (2010) SRL, 81(2), 184

STRAIN_DATA_BIRD_FILE = 'average_strain.dat.txt'
DEFORMATION_REGIMES_BIRD_FILE = 'tectonic_areas.dat.txt'
STRAIN_BIRD_LAST_COLUMN_TO_READ = 5

# Definitions for seismic moment computation from strain rate

DEFORMATION_REGIME_KEY_CTF = 'ctf' # Continental Transform Fault
DEFORMATION_REGIME_KEY_CCB = 'ccb' # Continental Convergent Boundary
DEFORMATION_REGIME_KEY_CRB = 'crb' # Continental Rift Boundary
DEFORMATION_REGIME_KEY_OSR = 'osr' # Oceanic Spreading Ridge
DEFORMATION_REGIME_KEY_OTF = 'otf' # Oceanic Transform Fault
DEFORMATION_REGIME_KEY_OCB = 'ocb' # Oceanic Rift Boundary

DEFORMATION_REGIME_KEY_C = 'C' # Continental
DEFORMATION_REGIME_KEY_R = 'R' # Ridge-transform

# The following dict holds coupled thickness (cz) and corner magnitude (mc)
# for the different deformation regimes
# cz is in kilometres
# From: Bird, Kreemer & Holt (2010) SRL, 81(2), 184 (page 187)
BIRD_SEISMICITY_PARAMETERS = {
        DEFORMATION_REGIME_KEY_CTF: {'cz': 8.6, 'mc': 8.01},
        DEFORMATION_REGIME_KEY_CCB: {'cz': 18.0, 'mc': 8.46},
        DEFORMATION_REGIME_KEY_CRB: {'cz': 3.0, 'mc': 7.64},
        DEFORMATION_REGIME_KEY_OSR: {'cz': 0.13, 'mc': 5.86},
        DEFORMATION_REGIME_KEY_OTF: {'cz': 1.8, 'mc': 6.55},
        DEFORMATION_REGIME_KEY_OCB: {'cz': 3.8, 'mc': 8.04}}
        
# Factor from Table 2 of Bird & Liu (2007)
BIRD_CONTINENTAL_REGIME_COMPARISON_FACTOR = 0.364
DEFORMATION_REGIME_DATA_POLYGON_VERTICES_CNT = 5

def loadStrainRateDataBarba():
    """Load strain rate data from Salvatore Barba into Python list.
    """
    strain_values = []

    path = os.path.join(layers.DATA_DIR, STRAIN_DATA_DIR, 
        STRAIN_DATA_BARBA_FILE)

    with open(path, 'r') as fh:

        for line in fh:

            # skip blank lines
            if len(line.strip()) == 0:
                continue
            
            else:
                line_arr = [float(x.strip()) for x in line.strip().split()]
                strain_values.append(line_arr)

    return strain_values

def loadStrainRateDataBird():
    """Load GSRM strain rate data from Bird/Kreemer dataset into Python list.
    """
    strain_values = []

    path = os.path.join(layers.DATA_DIR, STRAIN_DATA_DIR, 
        STRAIN_DATA_BIRD_FILE)

    with open(path, 'r') as fh:

        for line_idx, line in enumerate(fh):

            # skip first line and blank lines
            if line_idx == 0 or len(line.strip()) == 0:
                continue
            
            else:
                line_arr = [float(x.strip()) for x in \
                    line.strip().split()[0:STRAIN_BIRD_LAST_COLUMN_TO_READ]]
                strain_values.append(line_arr)
                
    return strain_values

def loadDeformationRegimesBird():
    """Load deformation regime polygons into Python dict.
    
    The format of the input file is as follows:
    
    > C
    -160.0  40.0
    ...
    
    > R
    ...
    
    I.e., a line with the deformation regime type (from C, O, R, S, I),
    followed by five (lon lat) lines giving polygon vertices.
    
    We only extract data for deformation regime types 'C' and 'R'.
    
    Note: Longitudes are given on an interval of 0...360, this has to be 
    converted to -180...180.
    """
    
    deformation_regimes = {}
    regime_polygons = {
            DEFORMATION_REGIME_KEY_C: [],
            DEFORMATION_REGIME_KEY_R: []}
            
    path = os.path.join(layers.DATA_DIR, STRAIN_DATA_DIR, 
        DEFORMATION_REGIMES_BIRD_FILE)

    with open(path, 'r') as fh:
        while (True):
            
            line = fh.readline()
            
            if not line:
                break
            
            # read regime code
            ignoreRegime = False
            regime_code = line.strip().split()[1]
            
            if regime_code not in (DEFORMATION_REGIME_KEY_C, 
                DEFORMATION_REGIME_KEY_R):
                ignoreRegime = True
            
            # read vertex coords of 5 polygon vertices
            vertices = []
            for vertex_line_idx in xrange(
                DEFORMATION_REGIME_DATA_POLYGON_VERTICES_CNT):
                    
                line = fh.readline()
                if ignoreRegime is True:
                    continue
                else:
                    coords = line.strip().split()
                    lat = float(coords[1])
                    lon = float(coords[0])
                    
                    # TODO(fab): fix polygons that cross 180 deg longitude 
                    # meridian
                    if lon > 180.0:
                        lon = lon - 360.0
                    vertices.append((lon, lat))
                    
            if ignoreRegime is False:
                poly = shapely.geometry.Polygon(vertices)
                regime_polygons[regime_code].append(poly)
                
    for regime_code in (DEFORMATION_REGIME_KEY_C, DEFORMATION_REGIME_KEY_R):
        
        deformation_regimes[regime_code] = shapely.ops.cascaded_union(
            regime_polygons[regime_code])
        
    return deformation_regimes
    
def strainRateComponentsFromDataset(rates_in):
    """Compute strain rate components as needed in Bird/Kreemer/Holt paper 
    from original strain rate components of Kreemer dataset.
    
    Input:
        triple of epp, ett, ept (in original dataset denoted 
        exx, eyy, exy) strain rate tensor components
        
    Output:
        6-tuple of e1, e2, e3, e1h, e2h, err strain rate components
    """
    
    (epp, ett, ept) = rates_in
    err = -(epp + ett)
    sum1 = 0.5 * (epp + ett)
    sum2 = numpy.sqrt(ept * ept + 0.25 * numpy.power((epp - ett), 2))
    e1h = sum1 - sum2
    e2h = sum1 + sum2
    
    if err >= e2h:
        (e1, e2, e3) = (e1h, e2h, err)
    elif err <= e1h:
        (e1, e2, e3) = (err, e1h, e2h)
    else:
        (e1, e2, e3) = (e1h, err, e2h)
        
    return (e1, e2, e3, e1h, e2h, err)

    