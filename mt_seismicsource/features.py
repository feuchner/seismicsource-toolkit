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

# max/min magnitudes
AREA_SOURCE_ATTR_MMIN = {'name': 'mmin', 'type': QVariant.Double}
AREA_SOURCE_ATTR_MMAX = {'name': 'mmax', 'type': QVariant.Double}
AREA_SOURCE_ATTR_MMAXDIST = {'name': 'mmaxdist', 'type': QVariant.String}

AREA_SOURCE_ATTRIBUTES_MINMAXMAG = (AREA_SOURCE_ATTR_MMIN, 
    AREA_SOURCE_ATTR_MMAX, AREA_SOURCE_ATTR_MMAXDIST)

# magnitude of completeness
AREA_SOURCE_ATTR_MC = {'name': 'mc', 'type': QVariant.Double}
AREA_SOURCE_ATTR_MCDIST = {'name': 'mcdist', 'type': QVariant.String}

AREA_SOURCE_ATTRIBUTES_MC = (AREA_SOURCE_ATTR_MC, AREA_SOURCE_ATTR_MCDIST)

# a/b prior
AREA_SOURCE_ATTR_A_PRIOR = {'name': 'a_prior', 'type': QVariant.Double}
AREA_SOURCE_ATTR_B_PRIOR = {'name': 'b_prior', 'type': QVariant.Double}

AREA_SOURCE_ATTRIBUTES_AB_PRIOR = (AREA_SOURCE_ATTR_A_PRIOR, 
    AREA_SOURCE_ATTR_B_PRIOR)

# a/b maximum likelihood
AREA_SOURCE_ATTR_A_ML = {'name': 'a_ml', 'type': QVariant.Double}
AREA_SOURCE_ATTR_B_ML = {'name': 'b_ml', 'type': QVariant.Double}

AREA_SOURCE_ATTRIBUTES_AB_ML = (AREA_SOURCE_ATTR_A_ML, AREA_SOURCE_ATTR_B_ML)

# a/b according to RogerMusson's AtticIvy
AREA_SOURCE_ATTR_A_RM = {'name': 'a_rm', 'type': QVariant.Double}
AREA_SOURCE_ATTR_B_RM = {'name': 'b_rm', 'type': QVariant.Double}
AREA_SOURCE_ATTR_ACTIVITY_RM = {'name': 'activit_rm', 'type': QVariant.String}

AREA_SOURCE_ATTRIBUTES_AB_RM = (AREA_SOURCE_ATTR_A_RM, AREA_SOURCE_ATTR_B_RM, 
    AREA_SOURCE_ATTR_ACTIVITY_RM)

# combination of all attribute groups
AREA_SOURCE_ATTRIBUTES_ALL = (AREA_SOURCE_ATTRIBUTES_MINMAXMAG, 
    AREA_SOURCE_ATTRIBUTES_MC, AREA_SOURCE_ATTRIBUTES_AB_PRIOR, 
    AREA_SOURCE_ATTRIBUTES_AB_ML, AREA_SOURCE_ATTRIBUTES_AB_RM)
