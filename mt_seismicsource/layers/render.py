# -*- coding: utf-8 -*-
"""
SHARE Seismic Source Toolkit

Renderer for layers.

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

AREA_LAYER_STYLE_FILE = 'style/layer-style-area-zones.qml'
FAULT_LAYER_STYLE_FILE = 'style/layer-style-fault-zones.qml'
EQ_LAYER_STYLE_FILE = 'style/layer-style-eq-catalog-base.qml'
BACKGROUND_ZONE_LAYER_STYLE_FILE = 'style/layer-style-background-zones.qml'
BACKGROUND_LAYER_STYLE_FILE = 'style/layer-style-political-boundaries.qml'

def setRenderers(area_layer, fault_layer, eq_layer, background_zone_layer,
    background_layer):

    #r_area_layer = area_layer.rendererV2()
    #r_fault_layer = fault_layer.rendererV2()
    #r_eq_layer = eq_layer.rendererV2()
    #r_background_zone_layer = background_zone_layer.rendererV2()
    #r_background_layer = background_layer.rendererV2()

    area_layer.loadNamedStyle(os.path.join(os.path.dirname(__file__), 
        AREA_LAYER_STYLE_FILE))

    fault_layer.loadNamedStyle(os.path.join(os.path.dirname(__file__), 
        FAULT_LAYER_STYLE_FILE))

    eq_layer.loadNamedStyle(os.path.join(os.path.dirname(__file__), 
        EQ_LAYER_STYLE_FILE))

    background_zone_layer.loadNamedStyle(
        os.path.join(os.path.dirname(__file__), 
        BACKGROUND_ZONE_LAYER_STYLE_FILE))

    background_layer.loadNamedStyle(os.path.join(os.path.dirname(__file__), 
        BACKGROUND_LAYER_STYLE_FILE))
