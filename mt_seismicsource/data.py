# -*- coding: utf-8 -*-
"""
SHARE Seismic Source Toolkit

This module holds classes for additional (non-layer) datasets.

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

import csv
import os

from mt_seismicsource import layers
from mt_seismicsource.algorithms import strain

MMAX_FILE_DIR = 'mmax'
MMAX_FILE = 'Mmax_20110520.csv'
MMAX_CSV_DELIMITER = ','
MMAX_ID_IDX = 0
MMAX_NAME_IDX = 1
MMAX_MMAX_IDX = 10

class Datasets(object):
    """Additional (non-layer) datasets."""

    def __init__(self):

        self.strain_rate_barba = strain.loadStrainRateDataBarba()
        self.strain_rate_bird = strain.loadStrainRateDataBird()
        self.deformation_regimes_bird = strain.loadDeformationRegimesBird()
        
        self.mmax = self.loadMmaxData()
        
    def loadMmaxData(self):
        
        self.mmax = {}
        
        mmax_path = os.path.join(layers.DATA_DIR, MMAX_FILE_DIR, MMAX_FILE)
        with open(mmax_path, 'r') as fh:
            reader = csv.reader(fh, delimiter=MMAX_CSV_DELIMITER)

            for line_idx, line in enumerate(reader):
                
                # skip first line with field names
                if line_idx == 0:
                    continue
                
                zone_id = int(line[MMAX_ID_IDX].strip())
                zone_name = line[MMAX_NAME_IDX].strip()
                zone_mmax = float(line[MMAX_MMAX_IDX].strip())

                self.mmax[zone_id] = {'name': zone_name, 'mmax': zone_mmax}
