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

from PyQt4.QtCore import *

## NOTE: attribute names can have max 10 chars

## area source attributes

# ID (integer number)
AREA_SOURCE_ATTR_ID = {'name': 'Id', 'type': QVariant.Int}
AREA_SOURCE_ATTR_TITLE = {'name': 'Title', 'type': QVariant.String}
AREA_SOURCE_ATTR_NAME = {'name': 'Name', 'type': QVariant.Int}

AREA_SOURCE_ATTRIBUTES_ID = (AREA_SOURCE_ATTR_ID, AREA_SOURCE_ATTR_TITLE,
    AREA_SOURCE_ATTR_NAME)

# max/min magnitudes
AREA_SOURCE_ATTR_MMIN = {'name': 'mmin', 'type': QVariant.Double}
AREA_SOURCE_ATTR_MMAX = {'name': 'mmax', 'type': QVariant.Double}
AREA_SOURCE_ATTR_MMAXDIST = {'name': 'mmaxdist', 'type': QVariant.String}

# skip: AREA_SOURCE_ATTR_MMAXDIST
AREA_SOURCE_ATTRIBUTES_MINMAXMAG = (AREA_SOURCE_ATTR_MMIN, 
    AREA_SOURCE_ATTR_MMAX)

# magnitude of completeness
# skip: mc
AREA_SOURCE_ATTR_MC = {'name': 'mc', 'type': QVariant.Double}
AREA_SOURCE_ATTR_MCDIST = {'name': 'mcdist', 'type': QVariant.String}

AREA_SOURCE_ATTRIBUTES_MC = (AREA_SOURCE_ATTR_MCDIST, )

# a/b prior
AREA_SOURCE_ATTR_A_PRIOR = {'name': 'a_prior', 'type': QVariant.Double}
AREA_SOURCE_ATTR_B_PRIOR = {'name': 'b_prior', 'type': QVariant.Double}

AREA_SOURCE_ATTRIBUTES_AB_PRIOR = (AREA_SOURCE_ATTR_A_PRIOR, 
    AREA_SOURCE_ATTR_B_PRIOR)

# a/b maximum likelihood
AREA_SOURCE_ATTR_A_ML = {'name': 'a_ml', 'type': QVariant.Double}
AREA_SOURCE_ATTR_B_ML = {'name': 'b_ml', 'type': QVariant.Double}

AREA_SOURCE_ATTRIBUTES_AB_ML = (AREA_SOURCE_ATTR_A_ML, AREA_SOURCE_ATTR_B_ML)

# a/b according to Roger Musson's AtticIvy
AREA_SOURCE_ATTR_A_RM = {'name': 'a_rm', 'type': QVariant.Double}
AREA_SOURCE_ATTR_B_RM = {'name': 'b_rm', 'type': QVariant.Double}
AREA_SOURCE_ATTR_ACTIVITY_RM = {'name': 'activit_rm', 'type': QVariant.String}

AREA_SOURCE_ATTRIBUTES_AB_RM = (AREA_SOURCE_ATTR_A_RM, AREA_SOURCE_ATTR_B_RM, 
    AREA_SOURCE_ATTR_ACTIVITY_RM)

# combination of all attribute groups
# skip: AREA_SOURCE_ATTRIBUTES_AB_PRIOR, AREA_SOURCE_ATTRIBUTES_AB_ML
AREA_SOURCE_ATTRIBUTES_ALL = (
    AREA_SOURCE_ATTRIBUTES_ID, 
    AREA_SOURCE_ATTRIBUTES_MINMAXMAG, 
    AREA_SOURCE_ATTRIBUTES_MC, 
    AREA_SOURCE_ATTRIBUTES_AB_RM)

## fault source attributes 

# Attributes for computing recurrence, from geology.
# These quantities are required to compute total seismic moment rate 
# and activity rate per fault polygon.

# OUTPUT (to be stored in result shapefile)

# * momentrate (total seismic moment rate)
#    this is one scalar value
# * activirate (activity rate)): eq. 7 in Bungum paper
#    this is a frequency-magnitude distribution (two arrays)
#    as shapefile attribute, make it sequence of magnitude/number pairs
#    separated by whitespace

# INPUT

# mu, shear modulus, or rigidity (same for all faults in crust) CONSTANT
# minimum magnitude (fixed, 5.0) CONSTANT
# annual fault slip rate (fixed, 1.0) CONSTANT NOTE: real value has to be obtained!

# SLIPRATEMA (maximum slip rate, attribute in fault polygon shapefile)
# fault rupture area (not an attribute, area of fault polygon)
# b_value (GR, regional b value from large RM background zones)
# magnitude type is Mw per default
# log(seismic moment): seismic moment-to-magnitude conversion: c and d constants from Bungum paper
#  MAXMAG given in fault polygon shapefile 
# aspect ratio of fault: (length / width): impossible to determine automatically from polygon
# - surface trace dataset would make it easier
# - if it can be determined automatically, it's implicit, otherwise store it
# ratio: SLIPRATEMA / fault length
# - if it can be determined automatically, it's implicit, otherwise store it

# ID
FAULT_SOURCE_ATTR_ID = {'name': 'IDSOURCE', 'type': QVariant.String}
FAULT_SOURCE_ATTR_NAME = {'name': 'SOURCENAME', 'type': QVariant.String}

FAULT_SOURCE_ATTRIBUTES_ID = (FAULT_SOURCE_ATTR_ID, FAULT_SOURCE_ATTR_NAME)

# Fault data
FAULT_SOURCE_ATTR_ID_FBZ = {'name': 'id_fbz', 'type': QVariant.String}

FAULT_SOURCE_ATTR_A_FBZ = {'name': 'a_fbz', 'type': QVariant.Double}
FAULT_SOURCE_ATTR_B_FBZ = {'name': 'b_fbz', 'type': QVariant.Double}
FAULT_SOURCE_ATTR_ACT_FBZ = {'name': 'act_fbz', 'type': QVariant.String}

FAULT_SOURCE_ATTR_A_BUF = {'name': 'a_buf', 'type': QVariant.Double}
FAULT_SOURCE_ATTR_B_BUF = {'name': 'b_buf', 'type': QVariant.Double}
FAULT_SOURCE_ATTR_ACT_BUF = {'name': 'act_buf', 'type': QVariant.String}

FAULT_SOURCE_ATTR_A_REC_MIN = {'name': 'a_rec_min', 'type': QVariant.Double}
FAULT_SOURCE_ATTR_A_REC_MAX = {'name': 'a_rec_max', 'type': QVariant.Double}

FAULT_SOURCE_ATTR_ACTIVITYRATE_MIN = {'name': 'actrate_mi', 
    'type': QVariant.String}
FAULT_SOURCE_ATTR_ACTIVITYRATE_MAX = {'name': 'actrate_ma', 
    'type': QVariant.String}
    
FAULT_SOURCE_ATTR_MOMENTRATE_MIN = {'name': 'momrate_mi', 
    'type': QVariant.Double}
FAULT_SOURCE_ATTR_MOMENTRATE_MAX = {'name': 'momrate_ma', 
    'type': QVariant.Double}
    
FAULT_SOURCE_ATTR_SLIPRATE_MIN = {'name': 'SLIPRATEMI', 
    'type': QVariant.Double}
FAULT_SOURCE_ATTR_SLIPRATE_MAX = {'name': 'SLIPRATEMA', 
    'type': QVariant.Double}

FAULT_SOURCE_ATTR_MAGNITUDE_MAX = {'name': 'MAXMAG', 'type': QVariant.Double}

FAULT_SOURCE_ATTRIBUTES_RECURRENCE = (
    FAULT_SOURCE_ATTR_ID_FBZ,
    FAULT_SOURCE_ATTR_A_FBZ,
    FAULT_SOURCE_ATTR_B_FBZ,
    FAULT_SOURCE_ATTR_ACT_FBZ,
    FAULT_SOURCE_ATTR_A_BUF,
    FAULT_SOURCE_ATTR_B_BUF,
    FAULT_SOURCE_ATTR_ACT_BUF,
    FAULT_SOURCE_ATTR_A_REC_MIN,
    FAULT_SOURCE_ATTR_A_REC_MAX,
    FAULT_SOURCE_ATTR_ACTIVITYRATE_MIN, 
    FAULT_SOURCE_ATTR_ACTIVITYRATE_MAX,
    FAULT_SOURCE_ATTR_MOMENTRATE_MIN,
    FAULT_SOURCE_ATTR_MOMENTRATE_MAX,
    FAULT_SOURCE_ATTR_SLIPRATE_MIN,
    FAULT_SOURCE_ATTR_SLIPRATE_MAX, 
    FAULT_SOURCE_ATTR_MAGNITUDE_MAX)

FAULT_SOURCE_ATTRIBUTES_RECURRENCE_COMPUTE = (
    FAULT_SOURCE_ATTR_ID_FBZ,
    FAULT_SOURCE_ATTR_A_FBZ,
    FAULT_SOURCE_ATTR_B_FBZ,
    FAULT_SOURCE_ATTR_ACT_FBZ,
    FAULT_SOURCE_ATTR_A_BUF,
    FAULT_SOURCE_ATTR_B_BUF,
    FAULT_SOURCE_ATTR_ACT_BUF,
    FAULT_SOURCE_ATTR_A_REC_MIN,
    FAULT_SOURCE_ATTR_A_REC_MAX,
    FAULT_SOURCE_ATTR_ACTIVITYRATE_MIN,
    FAULT_SOURCE_ATTR_ACTIVITYRATE_MAX,
    FAULT_SOURCE_ATTR_MOMENTRATE_MIN,
    FAULT_SOURCE_ATTR_MOMENTRATE_MAX)

## fault background zone attributes

# ID
FAULT_BACKGROUND_ATTR_ID = {'name': 'ID', 'type': QVariant.Double}
FAULT_BACKGROUND_ATTR_NAME = {'name': 'NAME', 'type': QVariant.String}

FAULT_BACKGROUND_ATTRIBUTES_ID = (FAULT_BACKGROUND_ATTR_ID, 
    FAULT_BACKGROUND_ATTR_NAME)
