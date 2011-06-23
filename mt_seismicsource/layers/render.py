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

AREA_LAYER_STYLE = {'file': 'style/layer-style-area-zones.qml', 
                    'visible': True}
FAULT_LAYER_STYLE = {'file': 'style/layer-style-fault-zones.qml', 
                     'visible': True}
FAULT_BACKGROUND_LAYER_STYLE = \
    {'file': 'style/layer-style-faultsource-background.qml', 
     'visible': True}
EQ_LAYER_STYLE = {'file': 'style/layer-style-eq-catalog-base.qml', 
                  'visible': True}
BACKGROUND_ZONE_LAYER_STYLE = \
    {'file': 'style/layer-style-background-zones.qml', 
     'visible': False}
TECTONIC_LAYER_STYLE = {'file': 'style/layer-style-tectonic-regimes.qml', 
                        'visible': False}
BACKGROUND_LAYER_STYLE = \
    {'file': 'style/layer-style-political-boundaries.qml', 
     'visible': True}

# extent of map view at startup

EXTENT_LON_MIN = -26.0
EXTENT_LON_MAX = 46.0
EXTENT_LAT_MIN = 25.0
EXTENT_LAT_MAX = 72.0

def setRenderers(area_layer, fault_layer, fault_background_layer, eq_layer,
    background_zone_layer, background_layer, tectonic_layer):

    area_layer.loadNamedStyle(os.path.join(os.path.dirname(__file__), 
        AREA_LAYER_STYLE['file']))

    fault_layer.loadNamedStyle(os.path.join(os.path.dirname(__file__), 
        FAULT_LAYER_STYLE['file']))

    fault_background_layer.loadNamedStyle(os.path.join(
        os.path.dirname(__file__), FAULT_BACKGROUND_LAYER_STYLE['file']))
        
    eq_layer.loadNamedStyle(os.path.join(os.path.dirname(__file__), 
        EQ_LAYER_STYLE['file']))

    background_zone_layer.loadNamedStyle(
        os.path.join(os.path.dirname(__file__), 
        BACKGROUND_ZONE_LAYER_STYLE['file']))

    background_layer.loadNamedStyle(os.path.join(os.path.dirname(__file__), 
        BACKGROUND_LAYER_STYLE['file']))
        
    tectonic_layer.loadNamedStyle(os.path.join(os.path.dirname(__file__), 
        TECTONIC_LAYER_STYLE['file']))
