# -*- coding: utf-8 -*-
"""
SHARE Seismic Source Toolkit

Loader for fault source layer.

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

from PyQt4.QtCore import *
from PyQt4.QtGui import *

from qgis.core import *

from mt_seismicsource import layers
from mt_seismicsource import features
from mt_seismicsource import utils

#FAULT_FILE_DIR = 'fault_sources/DISS'
#FAULT_FILE = 'CSSTop_polyline.shp'
#FAULT_FILES = ('CSSTop_polyline.shp',)

FAULT_FILE_DIR = 'fault_sources/DISS-3.2-2011-04-19'
FAULT_FILE = 'CSSources_region.shp'
FAULT_FILES = ('CSSources_region.shp',)

def loadFaultSourceLayer(cls):
    """Load fault source layer from Shapefile. Add required feature attributes
    if they are missing.

    Input:
        path    Filename of Shapefile
    """
    fault_source_path = os.path.join(layers.DATA_DIR, 
        FAULT_FILE_DIR, unicode(cls.comboBoxFaultInput.currentText()))

    if not os.path.isfile(fault_source_path):
        utils.warning_box_missing_layer_file(fault_source_path)
        return

    temp_fault_source_layer = QgsVectorLayer(fault_source_path, 
        "Fault Sources", "ogr")

    layer = utils.shp2memory(temp_fault_source_layer, "Fault Sources")
    QgsMapLayerRegistry.instance().addMapLayer(layer)
    return layer
