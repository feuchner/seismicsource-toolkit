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

from PyQt4.QtCore import *
from PyQt4.QtGui import *

from qgis.core import *

def setRenderers(area_layer, fault_layer, eq_layer, background_zone_layer,
    background_layer):

    r_area_layer = area_layer.rendererV2()
    r_fault_layer = fault_layer.rendererV2()
    r_eq_layer = eq_layer.rendererV2()
    r_background_zone_layer = background_zone_layer.rendererV2()
    r_background_layer = background_layer.rendererV2()

    # TODO(fab): configure renderers
    return {'area': r_area_layer,
            'fault': r_fault_layer,
            'eq': r_eq_layer,
            'background_zone': r_background_zone_layer,
            'background': r_background_layer
           }
