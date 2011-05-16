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
STRAIN_DATA_FILE = 'strain_rate_ns_d09.dat'

LON_RANGE = (-42.0, 46.0, 0.2)
LAT_RANGE = (76.0, 28.0, -0.2)

def loadStrainRateData():
    """Read output from AtticIvy program. Returns list of 
    [a, b, activity_string] value triples.
    a: activity
    b: b-value
    activity_string: string of all [weight, a, b] triples per zone, in a row,
                     separated by white space
    """
    strain_values = []

    path = os.path.join(layers.DATA_DIR, STRAIN_DATA_DIR, STRAIN_DATA_FILE)
    LON_BINS = int((LON_RANGE[1] - LON_RANGE[0]) / LON_RANGE[2])
    LAT_BINS = int((LAT_RANGE[1] - LAT_RANGE[0]) / LAT_RANGE[2])

    with open(path, 'r') as fh:

        for lon_idx in xrange(LON_BINS):
            for lat_idx in xrange(LAT_BINS):

                line = fh.readline()
                line_arr = [float(x.strip()) for x in line.strip().split()]
                strain_values.append(line_arr)

    return strain_values
