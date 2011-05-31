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

from PyQt4.QtCore import *
from PyQt4.QtGui import *

from mt_seismicsource.algorithms import strain

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

def momentrateFromStrainRateBarba(poly, strain_in, regime):
    """Compute seismic moment rate from Barba strain rate data set.

    Input:
        poly            Area zone geometry as Shapely polygon
        strain_in       Strain rate dataset as list of lists
                        [ [lon, lat, value], ...]
        regime          Dict of Shapely multipolygons for each deformation regime
                        Currently only Continental (C) and Ridge-transform (R)
                        implemented
                        {'C': Multipolygon, 'R': Multipolygon}

    Output:
        momentrate      moment rate computed from strain rate summed 
                        over area zone
    """

    momentrate = 0.0

    for (lon, lat, value) in strain_in:

        # make Shapely point from lon, lat
        point = shapely.geometry.Point((lon, lat))

        # check if in area zone polygon
        # if positive, sum up strain rate contribution
        if poly.intersects(point) and value > 0.0:
            
            # get deformation regime
            regime_key = strain.tectonicRegimeForPoint(point, regime)
                    
            # if point not in one of the tectonic regions, use value for
            # crustal
            if regime_key not in (strain.DEFORMATION_REGIME_KEY_C, 
                strain.DEFORMATION_REGIME_KEY_R):
                regime_key = strain.DEFORMATION_REGIME_KEY_C
                
            # select value for coupled thickness (cz):
            # if crustal, use value of Continental Transform Fault
            # if ridge-transform: use value of Oceanic Transform Fault
            # unit: km
            if regime_key == strain.DEFORMATION_REGIME_KEY_C:
                cz = strain.BIRD_SEISMICITY_PARAMETERS[\
                    strain.DEFORMATION_REGIME_KEY_CTF]['cz']
            else:
                cz = strain.BIRD_SEISMICITY_PARAMETERS[\
                    strain.DEFORMATION_REGIME_KEY_OTF]['cz']
                    
            momentrate += (cz * value)

    # Bird & Liu eq. 7B
    # Note: unit of values in Barba dataset is s^-1
    # computed strain rate has unit
    # km * Pa / s = 1000 m * N / (m^2 * s) = 1000 (Nm/s) per m^2
    # TODO(fab): double-check this !!
    # convert to strain rate per square kilometre: multiply with 10^-6
    # return 1000 * cz * SHEAR_MODULUS * strainrate * 1.0e-6
    return 1000 * SHEAR_MODULUS * momentrate

def momentrateFromStrainRateBird(poly, strain_in, regime):
    """Compute seismic moment rate from Bird strain rate data set.

    Input:
        poly            Area zone geometry as Shapely polygon
        strain_in       Strain rate dataset as list of lists
                        [ [lat, lon,  exx, eyy, exy], ...]
        regime          Dict of Shapely multipolygons for each deformation regime
                        Currently only Continental (C) and Ridge-transform (R)
                        implemented
                        {'C': Multipolygon, 'R': Multipolygon}

    Output:
        momentrate      moment rate computed from strain rate summed 
                        over area zone
    """

    momentrate = 0.0

    for (lat, lon, exx, eyy, exy) in strain_in:

        # make Shapely point from lon, lat
        point = shapely.geometry.Point((lon, lat))

        # check if in area zone polygon
        # TODO(fab): small area zones that do not include a strain rate
        # grid node
        if poly.intersects(point):
            
            # get deformation regime
            regime_key = strain.tectonicRegimeForPoint(point, regime)
                    
            # select values for cz and mc
            if regime_key not in (strain.DEFORMATION_REGIME_KEY_C, 
                strain.DEFORMATION_REGIME_KEY_R):
                    
                # point not in available regimes, don't evaluate contribution
                # from this point
                continue
           
            else:
                
                (e1, e2, e3, e1h, e2h, err) = \
                    strain.strainRateComponentsFromDataset((exx, eyy, exy))
                
                if regime_key == strain.DEFORMATION_REGIME_KEY_C:
                    
                    # continental regime
                    if (
                err <= strain.BIRD_CONTINENTAL_REGIME_COMPARISON_FACTOR * e2h \
            and err >= strain.BIRD_CONTINENTAL_REGIME_COMPARISON_FACTOR * e1h):
                            
                        # strike-slip faulting dominates
                        parameter_key = strain.DEFORMATION_REGIME_KEY_CTF
                        
                    elif \
                err > strain.BIRD_CONTINENTAL_REGIME_COMPARISON_FACTOR * e2h:
                        # thrust faulting dominates
                        parameter_key = strain.DEFORMATION_REGIME_KEY_CCB
                        
                    else:
                        # normal faulting dominates
                        parameter_key = strain.DEFORMATION_REGIME_KEY_CRB
                        
                elif regime_key == strain.DEFORMATION_REGIME_KEY_R:
                    
                    # ridge-transform regime
                    if e1h >= 0.0:
                        parameter_key = strain.DEFORMATION_REGIME_KEY_OSR
                    elif e2h < 0.0:
                        parameter_key = strain.DEFORMATION_REGIME_KEY_OCB
                    elif (e1h * e2h < 0.0 and (e1h + e2h) >= 0.0):
                        parameter_key = strain.DEFORMATION_REGIME_KEY_OTF
                    elif (e1h * e2h < 0.0 and (e1h + e2h) < 0.0):
                        parameter_key = strain.DEFORMATION_REGIME_KEY_OCB
                    else:
                        # never get here
                        raise RuntimeError, \
                            "Unexpected case in ridge-transform regime"
                        
                # TODO(fab): criterion for not adding contribution
                cz = strain.BIRD_SEISMICITY_PARAMETERS[parameter_key]['cz']
                if e2 < 0:
                    momentrate += (2 * cz * e3)
                else:
                    momentrate += (2 * cz * -e1)

    # convert original unit of [10^-9 yr^-1] to [s^-1]
    return 1000 * SHEAR_MODULUS * 1.0e-9 * momentrate * (
        60 * 60 * 24 * 365.25)
                    
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
