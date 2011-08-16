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

from mt_seismicsource.layers import render

FAULT_FILE_DIR = 'fault_sources'
FAULT_FILES = ('faults-DISS-3.2-2011-04-19.shp',)

TEMP_FILENAME = 'fault-sources.shp'

def loadFaultSourceLayer(cls):
    """Load fault source layer from Shapefile. Add required feature attributes
    if they are missing.
    """
    fault_source_path = os.path.join(layers.DATA_DIR, 
        FAULT_FILE_DIR, unicode(cls.comboBoxFaultZoneInput.currentText()))

    if not os.path.isfile(fault_source_path):
        utils.warning_box_missing_layer_file(fault_source_path)
        return

    save_path = os.path.join(layers.DATA_DIR, FAULT_FILE_DIR, TEMP_FILENAME)
    layer = loadFaultSourceFromSHP(fault_source_path, save_path, 
        layer2file=True)
    
    # register layer in QGis
    QgsMapLayerRegistry.instance().addMapLayer(layer)
    
    # set layer visibility
    cls.legend.setLayerVisible(layer, render.FAULT_LAYER_STYLE['visible'])
        
    return layer

def loadFaultSourceFromSHP(filename_in, filename_out=None, layer2file=True):
    """Load fault source layer from Shapefile, independent of QGis UI."""
    
    temp_fault_source_layer = QgsVectorLayer(filename_in, "Fault Sources", 
        "ogr")

    # PostGIS SRID 4326 is allocated for WGS84
    crs = QgsCoordinateReferenceSystem(4326, 
        QgsCoordinateReferenceSystem.PostgisCrsId)

    layer = utils.shp2memory(temp_fault_source_layer, "Fault Sources")
    layer.setCrs(crs) 
    
    # write memory layer to disk (as a Shapefile)
    if layer2file is True:
        utils.writeLayerToShapefile(layer, filename_out, crs)
    
    return layer
