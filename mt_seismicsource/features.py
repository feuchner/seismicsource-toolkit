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

# NOTE: Limitations of shapefile when serialized to disk:
# - attribute names can have max 10 chars (also for memory provider)
# - string attributes can have max 254 chars
# - a feature can have max 255 attributes (fields)
# - default length of string attributes in QGis is 80 chars

## area source attributes

# ID (integer number)
AREA_SOURCE_ATTR_ID = {'name': 'Id', 'type': QVariant.Int}
AREA_SOURCE_ATTR_TITLE = {'name': 'Title', 'type': QVariant.String}
AREA_SOURCE_ATTR_NAME = {'name': 'Name', 'type': QVariant.Int}

AREA_SOURCE_ATTRIBUTES_ID = (AREA_SOURCE_ATTR_ID, AREA_SOURCE_ATTR_TITLE,
    AREA_SOURCE_ATTR_NAME)

# max/min depth
AREA_SOURCE_ATTR_DEPTHMIN = {'name': 'mindepth', 'type': QVariant.Int}
AREA_SOURCE_ATTR_DEPTHMAX = {'name': 'maxdepth', 'type': QVariant.Int}

AREA_SOURCE_ATTRIBUTES_MINMAXDEPTH = (AREA_SOURCE_ATTR_DEPTHMIN, 
    AREA_SOURCE_ATTR_DEPTHMAX)
    
# max/min magnitudes
AREA_SOURCE_ATTR_MMAX = {'name': 'mmax', 'type': QVariant.Double}

AREA_SOURCE_ATTRIBUTES_MINMAXMAG = (AREA_SOURCE_ATTR_MMAX,)

# magnitude of completeness
AREA_SOURCE_ATTR_MC = {'name': 'mc', 'type': QVariant.Double}
AREA_SOURCE_ATTR_MC_METHOD = {'name': 'mcmethod', 'type': QVariant.String}
AREA_SOURCE_ATTR_MCDIST = {'name': 'mcdist', 'type': QVariant.String, 'length': 254}

AREA_SOURCE_ATTRIBUTES_MC = (AREA_SOURCE_ATTR_MC, AREA_SOURCE_ATTR_MC_METHOD, 
    AREA_SOURCE_ATTR_MCDIST)

# a/b prior
#AREA_SOURCE_ATTR_A_PRIOR = {'name': 'a_prior', 'type': QVariant.Double}
#AREA_SOURCE_ATTR_B_PRIOR = {'name': 'b_prior', 'type': QVariant.Double}

#AREA_SOURCE_ATTRIBUTES_AB_PRIOR = (AREA_SOURCE_ATTR_A_PRIOR, 
    #AREA_SOURCE_ATTR_B_PRIOR)

# a/b maximum likelihood
AREA_SOURCE_ATTR_A_ML = {'name': 'a_ml', 'type': QVariant.Double}
AREA_SOURCE_ATTR_B_ML = {'name': 'b_ml', 'type': QVariant.Double}
AREA_SOURCE_ATTR_MAGCTR_ML = {'name': 'magctr_ml', 'type': QVariant.Int}

AREA_SOURCE_ATTRIBUTES_AB_ML = (AREA_SOURCE_ATTR_A_ML, AREA_SOURCE_ATTR_B_ML, 
    AREA_SOURCE_ATTR_MAGCTR_ML)

# a/b according to Roger Musson's AtticIvy
AREA_SOURCE_ATTR_A_RM = {'name': 'a_rm', 'type': QVariant.Double}
AREA_SOURCE_ATTR_B_RM = {'name': 'b_rm', 'type': QVariant.Double}
AREA_SOURCE_ATTR_ACT_RM_W = {'name': 'act_rm_w', 'type': QVariant.String, 'length': 254}
AREA_SOURCE_ATTR_ACT_RM_A = {'name': 'act_rm_a', 'type': QVariant.String, 'length': 254}
AREA_SOURCE_ATTR_ACT_RM_B = {'name': 'act_rm_b', 'type': QVariant.String, 'length': 254}

AREA_SOURCE_ATTRIBUTES_AB_RM = (AREA_SOURCE_ATTR_A_RM, AREA_SOURCE_ATTR_B_RM,
    AREA_SOURCE_ATTR_ACT_RM_W, AREA_SOURCE_ATTR_ACT_RM_A, 
    AREA_SOURCE_ATTR_ACT_RM_B)

# moment rate components
AREA_SOURCE_ATTR_MR_EQ = {'name': 'mr_eq', 'type': QVariant.Double}
AREA_SOURCE_ATTR_MR_ACTIVITY = {'name': 'mr_act', 'type': QVariant.String, 
    'length': 254}
AREA_SOURCE_ATTR_MR_STRAIN_BIRD = {'name': 'mr_bird', 'type': QVariant.Double}
AREA_SOURCE_ATTR_MR_STRAIN_BARBA = {'name': 'mr_barba', 
    'type': QVariant.Double}

AREA_SOURCE_ATTRIBUTES_MOMENTRATE = (AREA_SOURCE_ATTR_MR_EQ,
    AREA_SOURCE_ATTR_MR_ACTIVITY, AREA_SOURCE_ATTR_MR_STRAIN_BIRD,
    AREA_SOURCE_ATTR_MR_STRAIN_BARBA)

# misc components
AREA_SOURCE_ATTR_AREA = {'name': 'area_sqkm', 'type': QVariant.Double}
AREA_SOURCE_ATTR_EQ_CNT = {'name': 'eq_count', 'type': QVariant.Int}

AREA_SOURCE_ATTRIBUTES_MISC = (AREA_SOURCE_ATTR_AREA,
    AREA_SOURCE_ATTR_EQ_CNT)
    
# combination of all attribute groups
# skip: AREA_SOURCE_ATTRIBUTES_AB_PRIOR
AREA_SOURCE_ATTRIBUTES_ALL = []
AREA_SOURCE_ATTRIBUTES_ALL.extend(AREA_SOURCE_ATTRIBUTES_ID)
AREA_SOURCE_ATTRIBUTES_ALL.extend(AREA_SOURCE_ATTRIBUTES_MINMAXDEPTH)
AREA_SOURCE_ATTRIBUTES_ALL.extend(AREA_SOURCE_ATTRIBUTES_MINMAXMAG)
AREA_SOURCE_ATTRIBUTES_ALL.extend(AREA_SOURCE_ATTRIBUTES_MC)
AREA_SOURCE_ATTRIBUTES_ALL.extend(AREA_SOURCE_ATTRIBUTES_AB_ML)
AREA_SOURCE_ATTRIBUTES_ALL.extend(AREA_SOURCE_ATTRIBUTES_AB_RM)
AREA_SOURCE_ATTRIBUTES_ALL.extend(AREA_SOURCE_ATTRIBUTES_MOMENTRATE)
AREA_SOURCE_ATTRIBUTES_ALL.extend(AREA_SOURCE_ATTRIBUTES_MISC)

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

# Activity parameters

FAULT_SOURCE_ATTR_ID_FBZ = {'name': 'id_fbz', 'type': QVariant.String}

FAULT_SOURCE_ATTR_A_FBZ = {'name': 'a_fbz', 'type': QVariant.Double}
FAULT_SOURCE_ATTR_B_FBZ = {'name': 'b_fbz', 'type': QVariant.Double}
FAULT_SOURCE_ATTR_ACT_FBZ_W = {'name': 'act_fbz_w', 'type': QVariant.String, 'length': 254}
FAULT_SOURCE_ATTR_ACT_FBZ_A = {'name': 'act_fbz_a', 'type': QVariant.String, 'length': 254}
FAULT_SOURCE_ATTR_ACT_FBZ_B = {'name': 'act_fbz_b', 'type': QVariant.String, 'length': 254}

FAULT_SOURCE_ATTR_A_BUF = {'name': 'a_buf', 'type': QVariant.Double}
FAULT_SOURCE_ATTR_B_BUF = {'name': 'b_buf', 'type': QVariant.Double}
FAULT_SOURCE_ATTR_ACT_BUF_W = {'name': 'act_buf_w', 'type': QVariant.String, 'length': 254}
FAULT_SOURCE_ATTR_ACT_BUF_A = {'name': 'act_buf_a', 'type': QVariant.String, 'length': 254}
FAULT_SOURCE_ATTR_ACT_BUF_B = {'name': 'act_buf_b', 'type': QVariant.String, 'length': 254}

FAULT_SOURCE_ATTR_M_THRES = {'name': 'm_thres', 'type': QVariant.Double}

FAULT_SOURCE_ATTR_A_FBZ_BT = {'name': 'a_fbz_bt', 'type': QVariant.Double}
FAULT_SOURCE_ATTR_B_FBZ_BT = {'name': 'b_fbz_bt', 'type': QVariant.Double}
FAULT_SOURCE_ATTR_ACT_FBZ_BT_W = {'name': 'afbz_bt_w', 'type': QVariant.String, 'length': 254}
FAULT_SOURCE_ATTR_ACT_FBZ_BT_A = {'name': 'afbz_bt_a', 'type': QVariant.String, 'length': 254}
FAULT_SOURCE_ATTR_ACT_FBZ_BT_B = {'name': 'afbz_bt_b', 'type': QVariant.String, 'length': 254}

FAULT_SOURCE_ATTR_A_FBZ_AT = {'name': 'a_fbz_at', 'type': QVariant.Double}
FAULT_SOURCE_ATTR_B_FBZ_AT = {'name': 'b_fbz_at', 'type': QVariant.Double}
FAULT_SOURCE_ATTR_ACT_FBZ_AT_W = {'name': 'afbz_at_w', 'type': QVariant.String, 'length': 254}
FAULT_SOURCE_ATTR_ACT_FBZ_AT_A = {'name': 'afbz_at_a', 'type': QVariant.String, 'length': 254}
FAULT_SOURCE_ATTR_ACT_FBZ_AT_B = {'name': 'afbz_at_b', 'type': QVariant.String, 'length': 254}

FAULT_SOURCE_ATTR_A_REC_MIN = {'name': 'a_rec_min', 'type': QVariant.Double}
FAULT_SOURCE_ATTR_A_REC_MAX = {'name': 'a_rec_max', 'type': QVariant.Double}

# activity rate from recurrence
FAULT_SOURCE_ATTR_ACTIVITYRATE_MIN = {'name': 'actrate_mi', 
    'type': QVariant.String, 'length': 254}
FAULT_SOURCE_ATTR_ACTIVITYRATE_MAX = {'name': 'actrate_ma', 
    'type': QVariant.String, 'length': 254}

# max. likelihood a and b values

FAULT_SOURCE_ATTR_A_ML = {'name': 'a_ml', 'type': QVariant.Double}
FAULT_SOURCE_ATTR_B_ML = {'name': 'b_ml', 'type': QVariant.Double}
FAULT_SOURCE_ATTR_MC_ML = {'name': 'mc_ml', 'type': QVariant.Double}
FAULT_SOURCE_ATTR_MAGCTR_ML = {'name': 'magctr_ml', 'type': QVariant.Int}
FAULT_SOURCE_ATTR_MC_METHOD = {'name': 'mcmethod', 'type': QVariant.String}

# moment rate components
FAULT_SOURCE_ATTR_MR_EQ = {'name': 'mr_eq', 'type': QVariant.Double}
FAULT_SOURCE_ATTR_MR_ACTIVITY_BUF = {'name': 'mr_act_buf', 
    'type': QVariant.String, 'length': 254}
FAULT_SOURCE_ATTR_MR_ACTIVITY_FBZ = {'name': 'mr_act_fbz', 
    'type': QVariant.String, 'length': 254}
FAULT_SOURCE_ATTR_MOMENTRATE_MIN = {'name': 'mr_slip_mi', 
    'type': QVariant.Double}
FAULT_SOURCE_ATTR_MOMENTRATE_MAX = {'name': 'mr_slip_ma', 
    'type': QVariant.Double}

# misc components

FAULT_SOURCE_ATTR_SLIPRATE_MIN = {'name': 'SLIPRATEMI', 
    'type': QVariant.Double}
FAULT_SOURCE_ATTR_SLIPRATE_MAX = {'name': 'SLIPRATEMA', 
    'type': QVariant.Double}

FAULT_SOURCE_ATTR_MAGNITUDE_MAX = {'name': 'MAXMAG', 'type': QVariant.Double}

FAULT_SOURCE_ATTR_MMAX_BG = {'name': 'mmax_bg', 'type': QVariant.Double}
FAULT_SOURCE_ATTR_EQ_CNT = {'name': 'eq_count', 'type': QVariant.Int}

FAULT_SOURCE_ATTRIBUTES_RECURRENCE = (
    FAULT_SOURCE_ATTR_ID_FBZ,
    FAULT_SOURCE_ATTR_A_FBZ,
    FAULT_SOURCE_ATTR_B_FBZ,
    FAULT_SOURCE_ATTR_ACT_FBZ_A,
    FAULT_SOURCE_ATTR_ACT_FBZ_B,
    FAULT_SOURCE_ATTR_A_BUF,
    FAULT_SOURCE_ATTR_B_BUF,
    FAULT_SOURCE_ATTR_ACT_BUF_A,
    FAULT_SOURCE_ATTR_ACT_BUF_B,
    FAULT_SOURCE_ATTR_M_THRES,
    FAULT_SOURCE_ATTR_A_FBZ_BT,
    FAULT_SOURCE_ATTR_B_FBZ_BT,
    FAULT_SOURCE_ATTR_ACT_FBZ_BT_A,
    FAULT_SOURCE_ATTR_ACT_FBZ_BT_B,
    FAULT_SOURCE_ATTR_A_FBZ_AT,
    FAULT_SOURCE_ATTR_B_FBZ_AT,
    FAULT_SOURCE_ATTR_ACT_FBZ_AT_A,
    FAULT_SOURCE_ATTR_ACT_FBZ_AT_B,
    FAULT_SOURCE_ATTR_A_REC_MIN,
    FAULT_SOURCE_ATTR_A_REC_MAX,
    FAULT_SOURCE_ATTR_ACTIVITYRATE_MIN, 
    FAULT_SOURCE_ATTR_ACTIVITYRATE_MAX,
    FAULT_SOURCE_ATTR_A_ML,
    FAULT_SOURCE_ATTR_B_ML,
    FAULT_SOURCE_ATTR_MC_ML,
    FAULT_SOURCE_ATTR_MAGCTR_ML,
    FAULT_SOURCE_ATTR_MC_METHOD,
    FAULT_SOURCE_ATTR_MR_EQ,
    FAULT_SOURCE_ATTR_MR_ACTIVITY_BUF,
    FAULT_SOURCE_ATTR_MR_ACTIVITY_FBZ,
    FAULT_SOURCE_ATTR_MOMENTRATE_MIN,
    FAULT_SOURCE_ATTR_MOMENTRATE_MAX,
    FAULT_SOURCE_ATTR_SLIPRATE_MIN,
    FAULT_SOURCE_ATTR_SLIPRATE_MAX,
    FAULT_SOURCE_ATTR_MAGNITUDE_MAX,
    FAULT_SOURCE_ATTR_MMAX_BG,
    FAULT_SOURCE_ATTR_EQ_CNT)

FAULT_SOURCE_ATTRIBUTES_RECURRENCE_COMPUTE = (
    FAULT_SOURCE_ATTR_ID_FBZ,
    FAULT_SOURCE_ATTR_A_FBZ,
    FAULT_SOURCE_ATTR_B_FBZ,
    FAULT_SOURCE_ATTR_ACT_FBZ_A,
    FAULT_SOURCE_ATTR_ACT_FBZ_B,
    FAULT_SOURCE_ATTR_A_BUF,
    FAULT_SOURCE_ATTR_B_BUF,
    FAULT_SOURCE_ATTR_ACT_BUF_A,
    FAULT_SOURCE_ATTR_ACT_BUF_B,
    FAULT_SOURCE_ATTR_M_THRES,
    FAULT_SOURCE_ATTR_A_FBZ_BT,
    FAULT_SOURCE_ATTR_B_FBZ_BT,
    FAULT_SOURCE_ATTR_ACT_FBZ_BT_A,
    FAULT_SOURCE_ATTR_ACT_FBZ_BT_B,
    FAULT_SOURCE_ATTR_A_FBZ_AT,
    FAULT_SOURCE_ATTR_B_FBZ_AT,
    FAULT_SOURCE_ATTR_ACT_FBZ_AT_A,
    FAULT_SOURCE_ATTR_ACT_FBZ_AT_B,
    FAULT_SOURCE_ATTR_A_REC_MIN,
    FAULT_SOURCE_ATTR_A_REC_MAX,
    FAULT_SOURCE_ATTR_ACTIVITYRATE_MIN, 
    FAULT_SOURCE_ATTR_ACTIVITYRATE_MAX,
    FAULT_SOURCE_ATTR_MMAX_BG)
    
FAULT_SOURCE_ATTRIBUTES_AB_ML_COMPUTE = (
    FAULT_SOURCE_ATTR_A_ML,
    FAULT_SOURCE_ATTR_B_ML,
    FAULT_SOURCE_ATTR_MC_ML,
    FAULT_SOURCE_ATTR_MAGCTR_ML,
    FAULT_SOURCE_ATTR_MC_METHOD,
    FAULT_SOURCE_ATTR_EQ_CNT)
    
FAULT_SOURCE_ATTRIBUTES_MOMENTRATE_COMPUTE = (
    FAULT_SOURCE_ATTR_MR_EQ,
    FAULT_SOURCE_ATTR_MR_ACTIVITY_BUF,
    FAULT_SOURCE_ATTR_MR_ACTIVITY_FBZ,
    FAULT_SOURCE_ATTR_MOMENTRATE_MIN,
    FAULT_SOURCE_ATTR_MOMENTRATE_MAX)

## fault background zone attributes

# ID
FAULT_BACKGROUND_ATTR_ID = {'name': 'ID', 'type': QVariant.Double}
FAULT_BACKGROUND_ATTR_NAME = {'name': 'NAME', 'type': QVariant.String}

FAULT_BACKGROUND_ATTRIBUTES_ID = (FAULT_BACKGROUND_ATTR_ID, 
    FAULT_BACKGROUND_ATTR_NAME)
