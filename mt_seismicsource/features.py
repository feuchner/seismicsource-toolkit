## -*- coding: utf-8 -*-
"""
SHARE Seismic Source Toolkit

This module holds definitons for feature attributes in data layers.

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

#import numpy
#import os
#import shapely.geometry
#import shutil
#import stat
#import subprocess
#import tempfile

from PyQt4.QtCore import *
#from PyQt4.QtGui import *

#from qgis.core import *

# NOTE: attribute names can have max 10 chars

AREA_SOURCE_ATTR_A_RM = {'name': 'a_rm', 'type': QVariant.Double}
AREA_SOURCE_ATTR_B_RM = {'name': 'b_rm', 'type': QVariant.Double}
AREA_SOURCE_ATTR_ACTIVITY_RM = {'name': 'activit_rm', 'type': QVariant.String}

AREA_SOURCE_ATTRIBUTES_RM = (AREA_SOURCE_ATTR_A_RM, AREA_SOURCE_ATTR_B_RM, 
    AREA_SOURCE_ATTR_ACTIVITY_RM) 
