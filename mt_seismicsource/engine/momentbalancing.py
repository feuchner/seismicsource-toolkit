# -*- coding: utf-8 -*-
"""
SHARE Seismic Source Toolkit

Various computations on area and fault source layers.

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

from PyQt4.QtCore import *
from PyQt4.QtGui import *

from qgis.core import *

import QPCatalog

from mt_seismicsource import features
from mt_seismicsource import plots
from mt_seismicsource import utils

from mt_seismicsource.algorithms import atticivy
from mt_seismicsource.algorithms import momentrate
from mt_seismicsource.algorithms import recurrence

from mt_seismicsource.layers import areasource
from mt_seismicsource.layers import eqcatalog

FAULT_BACKGROUND_MAG_THRESHOLD = 5.5

def updateMomentRatesArea(cls, feature):
    """Update or compute moment rates for selected feature of area source
    zone layer.

    Input:
        feature     QGis polygon feature from area source layer

    Output:
        moment_rates    dict of computed moment rates
    """

    provider = cls.area_source_layer.dataProvider()
    moment_rates = {}

    # get Shapely polygon from feature geometry
    poly, vertices = utils.polygonsQGS2Shapely((feature,))

    # get polygon area in square kilometres
    area_sqkm = utils.polygonAreaFromWGS84(poly[0]) * 1.0e-6

    ## moment rate from EQs

    # get quakes from catalog (cut with polygon)
    curr_cat = QPCatalog.QPCatalog()
    curr_cat.merge(cls.catalog)
    curr_cat.cut(geometry=poly[0])

    # sum up moment from quakes (converted from Mw with Kanamori eq.)
    magnitudes = []
    for ev in curr_cat.eventParameters.event:
        mag = ev.getPreferredMagnitude()
        magnitudes.append(mag.mag.value)

    moment = numpy.array(momentrate.magnitude2moment(magnitudes))

    # scale moment: per year and area (in km^2)
    # TODO(fab): compute real catalog time span
    moment_rates['eq'] = moment.sum() / (
        area_sqkm * eqcatalog.CATALOG_TIME_SPAN)

    ## moment rate from activity (RM)

    # get attribute index of AtticIvy result
    attribute_map = utils.getAttributeIndex(provider, 
        (features.AREA_SOURCE_ATTR_ACTIVITY_RM, 
         features.AREA_SOURCE_ATTR_MMAX))

    attribute_act_name = features.AREA_SOURCE_ATTR_ACTIVITY_RM['name']
    attribute_act_idx = attribute_map[attribute_act_name][0]
    attribute_mmax_name = features.AREA_SOURCE_ATTR_MMAX['name']
    attribute_mmax_idx = attribute_map[attribute_mmax_name][0]

    # get RM (weight, a, b) values from feature attribute
    activity_str = str(feature[attribute_act_idx].toString())
    activity_arr = activity_str.strip().split()

    # ignore weights
    activity_a = [float(x) for x in activity_arr[1::3]]
    activity_b = [float(x) for x in activity_arr[2::3]]
    mmax = float(feature[attribute_mmax_idx].toDouble()[0])

    # multiply computed value with area in square kilometres
    momentrates_arr = numpy.array(momentrate.momentrateFromActivity(
        activity_a, activity_b, mmax)) * area_sqkm / (
            eqcatalog.CATALOG_TIME_SPAN)

    moment_rates['activity'] = momentrates_arr.tolist()

    ## moment rate from geodesy (strain)
    momentrate_strain_barba = momentrate.momentrateFromStrainRateBarba(
        poly[0], cls.data.strain_rate_barba, 
        cls.data.deformation_regimes_bird)
    moment_rates['strain_barba'] = momentrate_strain_barba / (
        eqcatalog.CATALOG_TIME_SPAN)

    momentrate_strain_bird = momentrate.momentrateFromStrainRateBird(poly[0], 
        cls.data.strain_rate_bird, cls.data.deformation_regimes_bird)
    moment_rates['strain_bird'] = momentrate_strain_bird / (
        eqcatalog.CATALOG_TIME_SPAN)

    return moment_rates

def updateMomentRateTableArea(cls, moment_rates):
    cls.momentRateTableArea.clearContents()

    ## from EQs
    cls.momentRateTableArea.setItem(0, 0, QTableWidgetItem(QString(
        "%.2e" % moment_rates['eq'])))

    ## from activity (RM)

    # get maximum likelihood value from central line of table
    ml_idx = len(moment_rates['activity']) / 2
    mr_ml = moment_rates['activity'][ml_idx]
    cls.momentRateTableArea.setItem(0, 1, QTableWidgetItem(QString(
        "%.2e" % mr_ml)))

    ## from geodesy (strain)
    cls.momentRateTableArea.setItem(0, 2, QTableWidgetItem(QString(
        "%.2e" % moment_rates['strain_barba'])))

    cls.momentRateTableArea.setItem(0, 3, QTableWidgetItem(QString(
        "%.2e" % moment_rates['strain_bird'])))

def updateMomentRatePlotArea(cls, moment_rates):

    window = plots.createPlotWindow(cls)

    # new moment rate plot
    cls.fig_moment_rate_comparison_area = \
        plots.MomentRateComparisonPlotArea()
    cls.fig_moment_rate_comparison_area = \
        cls.fig_moment_rate_comparison_area.plot(imgfile=None, 
            data=moment_rates)

    cls.canvas_moment_rate_comparison_area = plots.PlotCanvas(
        cls.fig_moment_rate_comparison_area, 
        title="Seismic Moment Rates")
    cls.canvas_moment_rate_comparison_area.draw()

    # plot widget
    window.layoutPlot.addWidget(
        cls.canvas_moment_rate_comparison_area)
    cls.toolbar_moment_rate_comparison_area = plots.createToolbar(
        cls.canvas_moment_rate_comparison_area, 
        window)
    window.layoutPlot.addWidget(
        cls.toolbar_moment_rate_comparison_area)

def updateMomentRatesFault(cls, feature):
    """Update or compute moment rates for selected feature of fault source
    zone layer.

    Input:
        feature         QGis polygon feature from fault source layer

    Output:
        moment_rates    dict of computed moment rates
    """

    provider = cls.fault_source_layer.dataProvider()
    provider_area = cls.area_source_layer.dataProvider()
    provider_back = cls.background_zone_layer.dataProvider()

    attribute_map = utils.getAttributeIndex(provider, 
        (features.FAULT_SOURCE_ATTR_MOMENTRATE_MIN,
        features.FAULT_SOURCE_ATTR_MOMENTRATE_MAX))

    moment_rates = {}

    # get Shapely polygon from feature geometry
    poly, vertices = utils.polygonsQGS2Shapely((feature,))

    # get polygon area in square kilometres
    area_sqkm = utils.polygonAreaFromWGS84(poly[0]) * 1.0e-6

    # get buffer polygon with 30 km extension and its area in square km
    buffer_deg = 360.0 * (recurrence.BUFFER_AROUND_FAULT_POLYGONS / \
        utils.EARTH_CIRCUMFERENCE_EQUATORIAL_KM)
    buffer_poly = poly[0].buffer(buffer_deg)
    buffer_area_sqkm = utils.polygonAreaFromWGS84(buffer_poly) * 1.0e-6

    # get mmax and mcdist for buffer zone from background zone
    (mmax_qv, mcdist_qv) = areasource.getAttributesFromBackgroundZones(
        buffer_poly.centroid, provider_back)
    mmax = float(mmax_qv.toDouble()[0])
    mcdist = str(mcdist_qv.toString())

    ## moment rate from EQs

    # get quakes from catalog (cut with buffer polygon)
    curr_cat = QPCatalog.QPCatalog()
    curr_cat.merge(cls.catalog)
    curr_cat.cut(geometry=buffer_poly)

    # sum up moment from quakes (converted from Mw with Kanamori eq.)
    magnitudes = []
    for ev in curr_cat.eventParameters.event:
        mag = ev.getPreferredMagnitude()
        magnitudes.append(mag.mag.value)

    moment = numpy.array(momentrate.magnitude2moment(magnitudes))

    # scale moment: per year and area (in km^2)
    # TODO(fab): compute real catalog time span
    moment_rates['eq'] = moment.sum() / (
        buffer_area_sqkm * eqcatalog.CATALOG_TIME_SPAN)

    ## moment rate from activity (RM)

    activity = atticivy.computeActivityAtticIvy((buffer_poly, ), (mmax, ), 
        (mcdist, ), cls.catalog)

    # get RM (weight, a, b) values from feature attribute
    activity_str = activity[0][2]
    activity_arr = activity_str.strip().split()

    # ignore weights
    activity_a = [float(x) for x in activity_arr[1::3]]
    activity_b = [float(x) for x in activity_arr[2::3]]

    # multiply computed value with area in square kilometres
    momentrates_arr = numpy.array(momentrate.momentrateFromActivity(
        activity_a, activity_b, mmax)) * buffer_area_sqkm / (
            eqcatalog.CATALOG_TIME_SPAN)

    moment_rates['activity'] = momentrates_arr.tolist()

    ## moment rate from slip rate

    # TODO(fab): correct scaling of moment rate from slip rate
    momrate_min_name = features.FAULT_SOURCE_ATTR_MOMENTRATE_MIN['name']
    momrate_max_name = features.FAULT_SOURCE_ATTR_MOMENTRATE_MAX['name']
    momentrate_min = \
        feature[attribute_map[momrate_min_name][0]].toDouble()[0] / (
            eqcatalog.CATALOG_TIME_SPAN)
    momentrate_max = \
        feature[attribute_map[momrate_max_name][0]].toDouble()[0] / (
            eqcatalog.CATALOG_TIME_SPAN)
    moment_rates['slip'] = [momentrate_min, momentrate_max]

    return moment_rates

def updateMomentRateTableFault(cls, moment_rates):
    cls.momentRateTableFault.clearContents()

    ## from EQs
    cls.momentRateTableFault.setItem(0, 0, QTableWidgetItem(QString(
        "%.2e" % moment_rates['eq'])))

    ## from activity (RM)
    # get maximum likelihood value from central line of table
    ml_idx = len(moment_rates['activity']) / 2
    mr_ml = moment_rates['activity'][ml_idx]
    cls.momentRateTableFault.setItem(0, 1, QTableWidgetItem(QString(
        "%.2e" % mr_ml)))

    ## from geology (slip)
    cls.momentRateTableFault.setItem(0, 2, QTableWidgetItem(QString(
        "%.2e" % moment_rates['slip'][1])))

def updateMomentRatePlotFault(cls, moment_rates):

    window = plots.createPlotWindow(cls)

    # new moment rate plot
    cls.fig_moment_rate_comparison_fault = \
        plots.MomentRateComparisonPlotFault()
    cls.fig_moment_rate_comparison_fault = \
        cls.fig_moment_rate_comparison_fault.plot(imgfile=None, 
            data=moment_rates)

    cls.canvas_moment_rate_comparison_fault = plots.PlotCanvas(
        cls.fig_moment_rate_comparison_fault, 
        title="Seismic Moment Rates")
    cls.canvas_moment_rate_comparison_fault.draw()

    # plot widget
    window.layoutPlot.addWidget(
        cls.canvas_moment_rate_comparison_fault)
    cls.toolbar_moment_rate_comparison_fault = plots.createToolbar(
        cls.canvas_moment_rate_comparison_fault, 
        window)
    window.layoutPlot.addWidget(
        cls.toolbar_moment_rate_comparison_fault)

def updateMomentRatesFaultBackgr(cls, feature):
    """Update or compute moment rates for selected feature of fault background
    zone layer.

    Input:
        feature         QGis polygon feature from fault background zone layer

    Output:
        moment_rates    dict of computed moment rates
    """

    provider = cls.fault_background_layer.dataProvider()
    provider_fault = cls.fault_source_layer.dataProvider()
    provider_area = cls.area_source_layer.dataProvider()
    provider_back = cls.background_zone_layer.dataProvider()

    attribute_map = utils.getAttributeIndex(provider, 
        (features.FAULT_SOURCE_ATTR_MOMENTRATE_MIN,
        features.FAULT_SOURCE_ATTR_MOMENTRATE_MAX))

    moment_rates = {}

    # get Shapely polygon from feature geometry
    poly, vertices = utils.polygonsQGS2Shapely((feature,))

    # get polygon area in square kilometres
    area_sqkm = utils.polygonAreaFromWGS84(poly[0]) * 1.0e-6

    # get mmax and mcdist for buffer zone from background zone
    (mmax_qv, mcdist_qv) = areasource.getAttributesFromBackgroundZones(
        poly[0].centroid, provider_back)
    mmax = float(mmax_qv.toDouble()[0])
    mcdist = str(mcdist_qv.toString())

    ## moment rate from EQs

    # get quakes from catalog (cut with fault background zone polygon)
    curr_cat = QPCatalog.QPCatalog()
    curr_cat.merge(cls.catalog)
    curr_cat.cut(geometry=poly[0])

    # sum up moment from quakes (converted from Mw with Kanamori eq.)
    magnitudes = []
    for ev in curr_cat.eventParameters.event:
        mag = ev.getPreferredMagnitude()
        magnitudes.append(mag.mag.value)

    moment = numpy.array(momentrate.magnitude2moment(magnitudes))

    # scale moment: per year and area (in km^2)
    # TODO(fab): compute real catalog time span
    moment_rates['eq'] = moment.sum() / (
        area_sqkm * eqcatalog.CATALOG_TIME_SPAN)

    ## moment rate from activity (RM)
    
    # get catalogs below and above magnitude threshold
    cat_below_threshold = QPCatalog.QPCatalog()
    cat_below_threshold.merge(cls.catalog)
    cat_below_threshold.cut(maxmag=FAULT_BACKGROUND_MAG_THRESHOLD, 
        maxmag_excl=True)
        
    cat_above_threshold = QPCatalog.QPCatalog()
    cat_above_threshold.merge(cls.catalog)
    cat_above_threshold.cut(minmag=FAULT_BACKGROUND_MAG_THRESHOLD, 
        maxmag_excl=False)

    activity_below_threshold = atticivy.computeActivityAtticIvy(
        (poly[0], ), (mmax, ), (mcdist, ), cat_below_threshold)

    activity_above_threshold = atticivy.computeActivityAtticIvy(
        (poly[0], ), (mmax, ), (mcdist, ), cat_above_threshold)
        
    # get RM (weight, a, b) values from feature attribute
    activity_below_str = activity_below_threshold[0][2]
    activity_below_arr = activity_below_str.strip().split()

    activity_above_str = activity_above_threshold[0][2]
    activity_above_arr = activity_above_str.strip().split()
    
    # ignore weights
    activity_below_a = [float(x) for x in activity_below_arr[1::3]]
    activity_below_b = [float(x) for x in activity_below_arr[2::3]]

    activity_above_a = [float(x) for x in activity_above_arr[1::3]]
    activity_above_b = [float(x) for x in activity_above_arr[2::3]]
    
    # multiply computed value with area in square kilometres
    momentrates_below_arr = numpy.array(momentrate.momentrateFromActivity(
        activity_below_a, activity_below_b, mmax)) * area_sqkm / (
            eqcatalog.CATALOG_TIME_SPAN)
            
    momentrates_above_arr = numpy.array(momentrate.momentrateFromActivity(
        activity_above_a, activity_above_b, mmax)) * area_sqkm / (
            eqcatalog.CATALOG_TIME_SPAN)

    moment_rates['activity_below'] = momentrates_below_arr.tolist()
    moment_rates['activity_above'] = momentrates_above_arr.tolist()
    
    ## moment rate from slip rate

    # find all fault zones that lie in fault background zone
    faults = []
    for fault in provider_fault:
        
        fault_poly, vertices = utils.polygonsQGS2Shapely((fault,))
        if poly[0].contains(fault_poly[0]):
            faults.append(fault)
            
    momentrate_min = 0
    momentrate_max = 0
    momrate_min_name = features.FAULT_SOURCE_ATTR_MOMENTRATE_MIN['name']
    momrate_max_name = features.FAULT_SOURCE_ATTR_MOMENTRATE_MAX['name']
    
    for fault_contrib in faults:
        
        # TODO(fab): correct scaling of moment rate from slip rate
        momentrate_min += \
            fault_contrib[attribute_map[momrate_min_name][0]].toDouble()[0] / (
                eqcatalog.CATALOG_TIME_SPAN)
        momentrate_max += \
            fault_contrib[attribute_map[momrate_max_name][0]].toDouble()[0] / (
                eqcatalog.CATALOG_TIME_SPAN)
    
    moment_rates['slip'] = [momentrate_min, momentrate_max]

    return moment_rates

def updateMomentRateTableFaultBackgr(cls, moment_rates):
    cls.momentRateTableFault.clearContents()

    ## from EQs
    cls.momentRateTableFaultBackgr.setItem(0, 0, QTableWidgetItem(QString(
        "%.2e" % moment_rates['eq'])))

    ## from activity (RM)
    
    # get maximum likelihood value from central line of table
    ml_idx = len(moment_rates['activity_below']) / 2
    mr_ml = moment_rates['activity_below'][ml_idx]
    cls.momentRateTableFaultBackgr.setItem(0, 1, QTableWidgetItem(QString(
        "%.2e" % mr_ml)))
        
    ml_idx = len(moment_rates['activity_above']) / 2
    mr_ml = moment_rates['activity_above'][ml_idx]
    cls.momentRateTableFaultBackgr.setItem(0, 2, QTableWidgetItem(QString(
        "%.2e" % mr_ml)))

    ## from geology (slip)
    cls.momentRateTableFaultBackgr.setItem(0, 3, QTableWidgetItem(QString(
        "%.2e" % moment_rates['slip'][1])))

def updateMomentRatePlotFaultBackgr(cls, moment_rates):

    window = plots.createPlotWindow(cls)

    # new moment rate plot
    cls.fig_moment_rate_comparison_fault = \
        plots.MomentRateComparisonPlotFault()
    cls.fig_moment_rate_comparison_fault = \
        cls.fig_moment_rate_comparison_fault.plot(imgfile=None, 
            data=moment_rates)

    cls.canvas_moment_rate_comparison_fault = plots.PlotCanvas(
        cls.fig_moment_rate_comparison_fault, 
        title="Seismic Moment Rates")
    cls.canvas_moment_rate_comparison_fault.draw()

    # plot widget
    window.layoutPlot.addWidget(
        cls.canvas_moment_rate_comparison_fault)
    cls.toolbar_moment_rate_comparison_fault = plots.createToolbar(
        cls.canvas_moment_rate_comparison_fault, 
        window)
    window.layoutPlot.addWidget(
        cls.toolbar_moment_rate_comparison_fault)
