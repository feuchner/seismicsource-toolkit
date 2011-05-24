# -*- coding: utf-8 -*-
"""
SHARE Seismic Source Toolkit

Loader for map overlays (e.g., political boundaries).

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
from mt_seismicsource import utils

MAP_OVERLAY_DIR = 'map_overlay'
MAP_OVERLAY_POLITICAL_FILE = '10m-admin-0-countries.shp'

def loadBackgroundLayer(cls):
    if cls.background_layer is None:
        background_path = os.path.join(layers.DATA_DIR, MAP_OVERLAY_DIR,
            MAP_OVERLAY_POLITICAL_FILE)

        if not os.path.isfile(background_path):
            utils.warning_box_missing_layer_file(background_path)
            return

        cls.background_layer = QgsVectorLayer(background_path, 
            "Political Boundaries", "ogr")
        QgsMapLayerRegistry.instance().addMapLayer(cls.background_layer)

