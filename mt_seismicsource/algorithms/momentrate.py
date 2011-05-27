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
import shapely.geometry

# Kanamori equation
# lg(M_0) = 1.5 * m_W + 9.05
# M_0 is in SI units: Nm = kg * m^2 / s 
CONST_KANAMORI_C = 9.05
CONST_KANAMORI_D = 1.5

# Kanamori equation in CGS units, as given in Bungum paper (Table 1, line 7)
# See: Bungum (2007) Computers & Geosciences, 33, 808--820
#      doi:10.1016/j.cageo.2006.10.011
# lg(M_0_CGS) = 1.5 * m_W + 16.05
# M_0 is in CGS units: g * cm^2 / s = 10^-7 Nm
CONST_KANAMORI_C_CGS = 16.05

# shear modulus (mu, rigidity) for all faults, in Pa
SHEAR_MODULUS = 3.0e10

# cz factor according to Bird & Liu paper
# Bird & Liu, 2007, SRL, 78(1), 37
# use continental, strike-slip
# unit: km
CZ_FACTOR = 8.6

MMIN_MOMENTRATE_FROM_ACTIVITY = 5.0

def magnitude2moment(magnitudes):
    """Compute seismic moment from magnitudes (Mw), acoording to Kanamori
    equation.

    Input:
        magnitudes      list of magnitude values

    Output:
        moments         list of seismic moment values
    """

    # computes moment rate in Nm
    # M_0 = 10**(C + D * M) 
    moments = numpy.power(10, 
        numpy.array(magnitudes) * CONST_KANAMORI_D + CONST_KANAMORI_C)
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

    moment_rate_factor = numpy.power(10, 
        a_incremental + CONST_KANAMORI_C) / (1.5 - b)
    moment_rate_s1 = numpy.power(10, mmax * (1.5 - b))
    moment_rate_s2 = numpy.power(10, MMIN_MOMENTRATE_FROM_ACTIVITY * (1.5 - b))
    mr = moment_rate_factor * (moment_rate_s1 - moment_rate_s2)

    return mr.tolist()

def momentrateFromStrainRateBarba(poly, strain):
    """Compute seismic moment rate from Barba strain rate data set.

    Input:
        poly            Area zone geometry as Shapely polygon
        strain          Strain rate dataset as list of lists
                        [ [lon, lat, value], ...]

    Output:
        momentrate      moment rate computed from strain rate summed 
                        over area zone
    """

    momentrate = 0.0

    for (lon, lat, value) in strain:

        # make Shapely point from lon, lat
        point = shapely.geometry.Point((lon, lat))

        # check if in area zone polygon
        # if positive, sum up strain rate contribution
        if poly.intersects(point) and value > 0.0:
            momentrate += value

    # Bird & Liu eq. 7B
    # Note: unit of values in Barba dataset is s^-1
    # computed strain rate has unit
    # km * Pa / s = 1000 m * N / (m^2 * s) = 1000 (Nm/s) per m^2
    # TODO(fab): double-check this !!
    # convert to strain rate per square kilometre: multiply with 10^-6
    # return 1000 * CZ_FACTOR * SHEAR_MODULUS * strainrate * 1.0e-6
    return 1000 * CZ_FACTOR * SHEAR_MODULUS * momentrate

def momentrateFromStrainRateBird(poly, strain):
    """Compute seismic moment rate from Bird strain rate data set.

    Input:
        poly            Area zone geometry as Shapely polygon
        strain          Strain rate dataset as list of lists
                        [ [lon, lat, value], ...]

    Output:
        momentrate      moment rate computed from strain rate summed 
                        over area zone
    """

    momentrate = 0.0

    for (lat, lon, exx, eyy, exy) in strain:

        # make Shapely point from lon, lat
        point = shapely.geometry.Point((lon, lat))

        # check if in area zone polygon
        # if positive, sum up strain rate contribution
        if poly.intersects(point) and exx > 0.0:
            momentrate += exx

    # TODO(fab): use proper scaling
    return 1000 * CZ_FACTOR * SHEAR_MODULUS * momentrate

def momentrateFromSlipRate(slipratemi, slipratema, area):
    """Compute min/max seismic moment rate from min/max slip rate."""

    # TODO(fab): double-check scaling with Laurentiu!
    # shear modulus: Pa = N / m^2 = kg / (m * s^2) = kg / (10^-3 km * s^2)
    #                1 kg / (km * s^2) = 10^3 N
    # slip rate: mm / year
    # area: m^2
    # moment rate unit: Nm / (year * km^2)
    #  kg * 10^-3 m * m^2 / (m * s^2 * 365.25*24*60*60 s) 
    # = 10^3 N * 10^-3 m^3 / (10^-3 * [year] s))
    #  = 10^3 Nm * m^2 / [year] s <- divide this by area in metres (?)
    # kg m^3 / (m s^3) = kg m^2 / s^3

    slip_rates = numpy.array([slipratemi, slipratema], dtype=float)
    moment_rates = 1.0e3 * SHEAR_MODULUS * slip_rates * area / (
        365.25*24*60*60)

    return moment_rates.tolist()
