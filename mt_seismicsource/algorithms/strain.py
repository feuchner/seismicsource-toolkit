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

from mt_seismicsource import layers

STRAIN_DATA_DIR = 'strain'

STRAIN_DATA_BARBA_FILE = 'strain_rate_ns_d09.dat'

#LON_RANGE_BARBA = (-42.0, 46.0, 0.2)
#LAT_RANGE_BARBA = (76.0, 28.0, -0.2)

STRAIN_DATA_BIRD_FILE = 'average_strain.dat.txt'
STRAIN_BIRD_LAST_COLUMN_TO_READ = 5

def loadStrainRateDataBarba():
    """Load strain rate data from Salvatore Barba into Python list.
    """
    strain_values = []

    path = os.path.join(layers.DATA_DIR, STRAIN_DATA_DIR, 
        STRAIN_DATA_BARBA_FILE)
        
    #LON_BINS = int((LON_RANGE_BARBA[1] - LON_RANGE_BARBA[0]) / LON_RANGE_BARBA[2])
    #LAT_BINS = int((LAT_RANGE_BARBA[1] - LAT_RANGE_BARBA[0]) / LAT_RANGE_BARBA[2])

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
    """Load strain rate data from Peter Bird et al. into Python list.
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
