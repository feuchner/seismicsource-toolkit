# -*- coding: utf-8 -*-
"""
SHARE Seismic Source Toolkit

Algorithms to compute seismic moment rates.

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

import numpy
import os
import shutil
import stat
import subprocess
import tempfile

from PyQt4.QtCore import *
from PyQt4.QtGui import *

from qgis.core import *

from mt_seismicsource import features
from mt_seismicsource import utils

# Kanamori formula as given in Bungum paper (Table 1, line 7)
# See: Bungum (2007) Computers & Geosciences, 33, 808--820
#      doi:10.1016/j.cageo.2006.10.011
CONST_KANAMORI_C = 16.05
CONST_KANAMORI_D = 1.5

# shear modulus (mu, rigidity) for all faults, in GPa
SHEAR_MODULUS = 3.0e07

def magnitude2moment(magnitudes):
    """Compute seismic moment from magnitudes (Mw), acoording to Kanamori
    equation.

    Input:
        magnitudes      list of magnitude values

    Output:
        moments         list of seismic moment values
    """

    # computes natural logarithm of moment rate
    # ln(M_0) = C + D * M 
    moments = numpy.array(magnitudes) * CONST_KANAMORI_D + CONST_KANAMORI_C
    return moments.tolist()

def momentrateFromActivity(activity_a, activity_b):
    """Compute seismic moment rate from pairs of activity (a, b) values.

    Input:
        activity_a      list of activity a values
        activity_b      list of activity b values

    Output:
        momentrates     list of moment rates
    """

    momentrates = []

    a = numpy.array(activity_a)
    b = numpy.array(activity_b)

    mr = a + b

    return mr.tolist()