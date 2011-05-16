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

# Kanamori equation as given in Bungum paper (Table 1, line 7)
# See: Bungum (2007) Computers & Geosciences, 33, 808--820
#      doi:10.1016/j.cageo.2006.10.011
CONST_KANAMORI_C = 16.05
CONST_KANAMORI_D = 1.5

# shear modulus (mu, rigidity) for all faults, in GPa
SHEAR_MODULUS = 3.0e10

MMIN_MOMENTRATE_FROM_ACTIVITY = 5.0

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

def momentrateFromActivity(activity_a, activity_b, mmax):
    """Compute seismic moment rate from pairs of activity (a, b) values.

    Input:
        activity_a      list of activity a values
        activity_b      list of activity b values
        mmax            maximum magnitude

    Output:
        mr               list of moment rates
    """

    a = numpy.array(activity_a)
    b = numpy.array(activity_b)

    a_incremental = a + numpy.log10(b * numpy.log(10.0))

    moment_rate_factor = numpy.power(10, a_incremental + 9.05) / (1.5 - b)
    moment_rate_s1 = numpy.power(10, mmax * (1.5 - b))
    moment_rate_s2 = numpy.power(10, MMIN_MOMENTRATE_FROM_ACTIVITY * (1.5 - b))
    mr = moment_rate_factor * (moment_rate_s1 - moment_rate_s2)

    return mr.tolist()
