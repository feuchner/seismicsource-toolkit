# -*- coding: utf-8 -*-
"""
SHARE Seismic Source Toolkit

Loader for fault source background zone layer.

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

from mt_seismicsource.layers import render

FAULT_BACKGROUND_FILE_DIR = 'fault_background'
FAULT_BACKGROUND_FILES = ('FSBGZ01_1_region.shp',)

TEMP_FILENAME = 'fault-background.shp'

def loadFaultBackgroundLayer(cls):
    """Load fault source background layer from Shapefile.
    """
    fault_background_path = os.path.join(layers.DATA_DIR, 
        FAULT_BACKGROUND_FILE_DIR, unicode(
            cls.comboBoxFaultBackgrZoneInput.currentText()))

    if not os.path.isfile(fault_background_path):
        utils.warning_box_missing_layer_file(fault_background_path)
        return

    save_path = os.path.join(layers.DATA_DIR, FAULT_BACKGROUND_FILE_DIR, 
        TEMP_FILENAME)
    layer = loadFaultBackgroundFromSHP(fault_background_path, save_path,
        layer2file=True)

    # register layer in QGis
    QgsMapLayerRegistry.instance().addMapLayer(layer)
    
    # set layer visibility
    cls.legend.setLayerVisible(layer, 
        render.FAULT_BACKGROUND_LAYER_STYLE['visible'])
    
    return layer

def loadFaultBackgroundFromSHP(filename_in, filename_out=None, 
    layer2file=True):
    """Load fault source background layer from Shapefile, independent of 
    QGis UI."""
    
    temp_fault_background_layer = QgsVectorLayer(filename_in, 
        "Fault Background", "ogr")

    # PostGIS SRID 4326 is allocated for WGS84
    crs = QgsCoordinateReferenceSystem(4326, 
        QgsCoordinateReferenceSystem.PostgisCrsId)

    layer = utils.shp2memory(temp_fault_background_layer, "Fault Background")
    layer.setCrs(crs) 

    # write memory layer to disk (as a Shapefile)
    if layer2file is True:
        utils.writeLayerToShapefile(layer, filename_out, crs)
        
    return layer
