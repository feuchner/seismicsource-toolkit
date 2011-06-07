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
        
# ----------------------------------------------------------------------------

def updateDataArea(cls, feature):
    """Update or compute moment rates for selected feature of area source
    zone layer.

    Input:
        feature         QGis polygon feature from area source layer

    Output:
        parameters      dict of computed parameters
    """

    provider = cls.area_source_layer.dataProvider()
    parameters = {}

    # get Shapely polygon from feature geometry
    polylist, vertices = utils.polygonsQGS2Shapely((feature,))
    poly = polylist[0]
    
    # get polygon area in square kilometres
    parameters['area_sqkm'] = utils.polygonAreaFromWGS84(poly) * 1.0e-6

    ## moment rate from EQs

    # get quakes from catalog (cut with polygon)
    poly_cat = QPCatalog.QPCatalog()
    poly_cat.merge(cls.catalog)
    poly_cat.cut(geometry=poly)

    parameters['eq_count'] = poly_cat.size()
    
    # sum up moment from quakes (converted from Mw with Kanamori eq.)
    magnitudes = []
    for ev in poly_cat.eventParameters.event:
        mag = ev.getPreferredMagnitude()
        magnitudes.append(mag.mag.value)

    moment = numpy.array(momentrate.magnitude2moment(magnitudes))

    # scale moment: per year and area (in km^2)
    # TODO(fab): compute real catalog time span
    parameters['mr_eq'] = moment.sum() / (
        parameters['area_sqkm'] * eqcatalog.CATALOG_TIME_SPAN)

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
        activity_a, activity_b, mmax)) * parameters['area_sqkm'] / (
            eqcatalog.CATALOG_TIME_SPAN)

    parameters['activity_a'] = activity_a
    parameters['activity_b'] = activity_b 
    parameters['mmax'] = mmax 
    
    parameters['mr_activity'] = momentrates_arr.tolist()

    ## moment rate from geodesy (strain)
    momentrate_strain_barba = momentrate.momentrateFromStrainRateBarba(
        poly, cls.data.strain_rate_barba, 
        cls.data.deformation_regimes_bird)
    parameters['mr_strain_barba'] = momentrate_strain_barba / (
        eqcatalog.CATALOG_TIME_SPAN)

    momentrate_strain_bird = momentrate.momentrateFromStrainRateBird(poly, 
        cls.data.strain_rate_bird, cls.data.deformation_regimes_bird)
    parameters['mr_strain_bird'] = momentrate_strain_bird / (
        eqcatalog.CATALOG_TIME_SPAN)

    return parameters

def updateDisplaysArea(cls, parameters):
    """Update UI with computed values for selected area zone."""
    updateTextArea(cls, parameters)
    updateMomentRateTableArea(cls, parameters)
    updateMomentRatePlotArea(cls, parameters)

def updateTextArea(cls, parameters):
    text = ''
    text += "<b>Activity</b><br/>"
    text += "(RM) a: %s, b: %s<br/>" % (
        utils.centralValueOfList(parameters['activity_a']), 
        utils.centralValueOfList(parameters['activity_b']))
    text += "(ML) a: %s, b: %s<br/>" % (None, None)
    text += "Mmax: %s, %s EQ in %s km^2 (area zone)" % (
        parameters['mmax'],
        parameters['eq_count'],
        int(parameters['area_sqkm']))
    cls.textAreaActivity.setText(text)

def updateMomentRateTableArea(cls, parameters):
    cls.momentRateTableArea.clearContents()

    ## from EQs
    cls.momentRateTableArea.setItem(0, 0, QTableWidgetItem(QString(
        "%.2e" % parameters['mr_eq'])))

    ## from activity (RM)

    # get maximum likelihood value from central line of table
    cls.momentRateTableArea.setItem(0, 1, QTableWidgetItem(QString(
        "%.2e" % utils.centralValueOfList(parameters['mr_activity']))))

    ## from geodesy (strain)
    cls.momentRateTableArea.setItem(0, 2, QTableWidgetItem(QString(
        "%.2e" % parameters['mr_strain_barba'])))

    cls.momentRateTableArea.setItem(0, 3, QTableWidgetItem(QString(
        "%.2e" % parameters['mr_strain_bird'])))

def updateMomentRatePlotArea(cls, parameters):

    window = plots.createPlotWindow(cls)

    # new moment rate plot
    cls.fig_moment_rate_comparison_area = \
        plots.MomentRateComparisonPlotArea()
    cls.fig_moment_rate_comparison_area = \
        cls.fig_moment_rate_comparison_area.plot(imgfile=None, 
            data=parameters)

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

# ----------------------------------------------------------------------------

def updateDataFault(cls, feature):
    """Update or compute moment rates for selected feature of fault source
    zone layer.

    Input:
        feature         QGis polygon feature from fault source layer

    Output:
        parameters      dict of computed parameters
    """

    provider = cls.fault_source_layer.dataProvider()
    provider_area = cls.area_source_layer.dataProvider()
    provider_back = cls.background_zone_layer.dataProvider()

    parameters = {}

    # get Shapely polygon from feature geometry
    polylist, vertices = utils.polygonsQGS2Shapely((feature,))
    poly = polylist[0]

    # get polygon area in square kilometres
    parameters['area_sqkm'] = utils.polygonAreaFromWGS84(poly) * 1.0e-6

    # get buffer polygon with 30 km extension and its area in square km
    buffer_deg = 360.0 * (recurrence.BUFFER_AROUND_FAULT_POLYGONS / \
        utils.EARTH_CIRCUMFERENCE_EQUATORIAL_KM)
    buffer_poly = poly.buffer(buffer_deg)
    parameters['buffer_area_sqkm'] = utils.polygonAreaFromWGS84(buffer_poly) * 1.0e-6

    # get mmax and mcdist for buffer zone from background zone
    (mmax_qv, mcdist_qv) = areasource.getAttributesFromBackgroundZones(
        buffer_poly.centroid, provider_back)
    mmax = float(mmax_qv.toDouble()[0])
    mcdist = str(mcdist_qv.toString())

    ## moment rate from EQs

    # get quakes from catalog (cut with buffer polygon)
    poly_cat = QPCatalog.QPCatalog()
    poly_cat.merge(cls.catalog)
    poly_cat.cut(geometry=buffer_poly)
    
    parameters['eq_count'] = poly_cat.size()

    # sum up moment from quakes (converted from Mw with Kanamori eq.)
    magnitudes = []
    for ev in poly_cat.eventParameters.event:
        mag = ev.getPreferredMagnitude()
        magnitudes.append(mag.mag.value)

    moment = numpy.array(momentrate.magnitude2moment(magnitudes))

    # scale moment: per year and area (in km^2)
    # TODO(fab): compute real catalog time span
    parameters['mr_eq'] = moment.sum() / (
        parameters['buffer_area_sqkm'] * eqcatalog.CATALOG_TIME_SPAN)

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
        activity_a, activity_b, mmax)) * parameters['buffer_area_sqkm'] / (
            eqcatalog.CATALOG_TIME_SPAN)

    parameters['activity_a'] = activity_a
    parameters['activity_b'] = activity_b 
    parameters['mmax'] = mmax 
    
    parameters['mr_activity'] = momentrates_arr.tolist()

    ## moment rate from slip rate
    
    attribute_map = utils.getAttributeIndex(provider, 
        (features.FAULT_SOURCE_ATTR_SLIPRATE_MIN,
         features.FAULT_SOURCE_ATTR_SLIPRATE_MAX), create=False)
        
    sliprate_min_name = features.FAULT_SOURCE_ATTR_SLIPRATE_MIN['name']
    sliprate_max_name = features.FAULT_SOURCE_ATTR_SLIPRATE_MAX['name']
    
    sliprate_min = feature[attribute_map[sliprate_min_name][0]].toDouble()[0]
    sliprate_max = feature[attribute_map[sliprate_max_name][0]].toDouble()[0]
            
    # TODO(fab): correct scaling of moment rate from slip rate
    (moment_rate_min, moment_rate_max) = \
        momentrate.momentrateFromSlipRate(sliprate_min, sliprate_max, 
            parameters['area_sqkm'] * 1.0e6)

    parameters['mr_slip'] = [moment_rate_min, moment_rate_max]

    return parameters

def updateDisplaysFault(cls, parameters):
    """Update UI with computed values for selected fault zone."""
    updateTextFault(cls, parameters)
    updateMomentRateTableFault(cls, parameters)
    updateMomentRatePlotFault(cls, parameters)

def updateTextFault(cls, parameters):

    text = ''
    text += "<b>Activity</b><br/>"
    text += "(RM) a: %s, b: %s<br/>" % (
        utils.centralValueOfList(parameters['activity_a']), 
        utils.centralValueOfList(parameters['activity_b']))
    text += "(ML) a: %s, b: %s<br/>" % (None, None)
    text += "Mmax: %s, %s EQ in %s km^2 (buffer zone)" % (
        parameters['mmax'],
        parameters['eq_count'],
        int(parameters['buffer_area_sqkm']))
    cls.textFaultActivity.setText(text)

def updateMomentRateTableFault(cls, parameters):
    cls.momentRateTableFault.clearContents()

    ## from EQs
    cls.momentRateTableFault.setItem(0, 0, QTableWidgetItem(QString(
        "%.2e" % parameters['mr_eq'])))

    ## from activity (RM)
    # get maximum likelihood value from central line of table
    cls.momentRateTableFault.setItem(0, 1, QTableWidgetItem(QString(
        "%.2e" % utils.centralValueOfList(parameters['mr_activity']))))

    ## from geology (slip)
    cls.momentRateTableFault.setItem(0, 2, QTableWidgetItem(QString(
        "%.2e" % parameters['mr_slip'][1])))

def updateMomentRatePlotFault(cls, parameters):

    window = plots.createPlotWindow(cls)

    # new moment rate plot
    cls.fig_moment_rate_comparison_fault = \
        plots.MomentRateComparisonPlotFault()
    cls.fig_moment_rate_comparison_fault = \
        cls.fig_moment_rate_comparison_fault.plot(imgfile=None, 
            data=parameters)

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

# ----------------------------------------------------------------------------

def updateDataFaultBackgr(cls, feature):
    """Update or compute moment rates for selected feature of fault background
    zone layer.

    Input:
        feature         QGis polygon feature from fault background zone layer

    Output:
        parameters      dict of computed parameters
    """

    provider = cls.fault_background_layer.dataProvider()
    provider_fault = cls.fault_source_layer.dataProvider()
    provider_area = cls.area_source_layer.dataProvider()
    provider_back = cls.background_zone_layer.dataProvider()

    parameters = {}

    # get Shapely polygon from feature geometry
    polylist, vertices = utils.polygonsQGS2Shapely((feature,))
    poly = polylist[0]

    # get polygon area in square kilometres
    parameters['area_background_sqkm'] = \
        utils.polygonAreaFromWGS84(poly) * 1.0e-6

    # get mmax and mcdist for buffer zone from background zone
    (mmax_qv, mcdist_qv) = areasource.getAttributesFromBackgroundZones(
        poly.centroid, provider_back)
    mmax = float(mmax_qv.toDouble()[0])
    mcdist = str(mcdist_qv.toString())

    ## moment rate from EQs

    # get quakes from catalog (cut with fault background zone polygon)
    poly_cat = QPCatalog.QPCatalog()
    poly_cat.merge(cls.catalog)
    poly_cat.cut(geometry=poly)
    
    parameters['eq_count'] = poly_cat.size()

    # sum up moment from quakes (converted from Mw with Kanamori eq.)
    magnitudes = []
    for ev in poly_cat.eventParameters.event:
        mag = ev.getPreferredMagnitude()
        magnitudes.append(mag.mag.value)

    moment = numpy.array(momentrate.magnitude2moment(magnitudes))

    # scale moment: per year and area (in km^2)
    # TODO(fab): compute real catalog time span
    parameters['mr_eq'] = moment.sum() / (
        parameters['area_background_sqkm'] * eqcatalog.CATALOG_TIME_SPAN)

    ## moment rate from activity (RM)
    
    activity = atticivy.computeActivityAtticIvy(
        (poly, ), (mmax, ), (mcdist, ), cls.catalog)
    
    # get RM (weight, a, b) values from feature attribute
    activity_str = activity[0][2]
    activity_arr = activity_str.strip().split()
    
    # ignore weights
    activity_a = [float(x) for x in activity_arr[1::3]]
    activity_b = [float(x) for x in activity_arr[2::3]]
    
    # multiply computed value with area in square kilometres
    momentrates_arr = numpy.array(momentrate.momentrateFromActivity(
        activity_a, activity_b, mmax)) * parameters['area_background_sqkm'] / (
            eqcatalog.CATALOG_TIME_SPAN)

    parameters['activity_a'] = activity_a
    parameters['activity_b'] = activity_b 
    parameters['mr_activity'] = momentrates_arr.tolist()
    
    # get separate catalogs below and above magnitude threshold
    cat_below_threshold = QPCatalog.QPCatalog()
    cat_below_threshold.merge(poly_cat)
    cat_below_threshold.cut(maxmag=FAULT_BACKGROUND_MAG_THRESHOLD, 
        maxmag_excl=True)
    parameters['eq_count_below'] = cat_below_threshold.size()
        
    cat_above_threshold = QPCatalog.QPCatalog()
    cat_above_threshold.merge(poly_cat)
    cat_above_threshold.cut(minmag=FAULT_BACKGROUND_MAG_THRESHOLD, 
        maxmag_excl=False)
    parameters['eq_count_above'] = cat_above_threshold.size()

    activity_below_threshold = atticivy.computeActivityAtticIvy(
        (poly, ), (mmax, ), (mcdist, ), cat_below_threshold)

    activity_above_threshold = atticivy.computeActivityAtticIvy(
        (poly, ), (mmax, ), (mcdist, ), cat_above_threshold)
        
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
        activity_below_a, activity_below_b, mmax)) * \
            parameters['area_background_sqkm'] / eqcatalog.CATALOG_TIME_SPAN
            
    momentrates_above_arr = numpy.array(momentrate.momentrateFromActivity(
        activity_above_a, activity_above_b, mmax)) * \
            parameters['area_background_sqkm'] / eqcatalog.CATALOG_TIME_SPAN

    parameters['activity_below_a'] = activity_below_a
    parameters['activity_below_b'] = activity_below_b 
    
    parameters['activity_above_a'] = activity_above_a
    parameters['activity_above_b'] = activity_above_b 
    
    parameters['mr_activity_below'] = momentrates_below_arr.tolist()
    parameters['mr_activity_above'] = momentrates_above_arr.tolist()
    
    parameters['mmax'] = mmax 
    
    ## moment rate from slip rate

    sliprate_min_name = features.FAULT_SOURCE_ATTR_SLIPRATE_MIN['name']
    sliprate_max_name = features.FAULT_SOURCE_ATTR_SLIPRATE_MAX['name']

    attribute_map = utils.getAttributeIndex(provider_fault, 
        (features.FAULT_SOURCE_ATTR_SLIPRATE_MIN,
         features.FAULT_SOURCE_ATTR_SLIPRATE_MAX), create=False)
    
    moment_rate_min = 0.0
    moment_rate_max = 0.0
    parameters['area_fault_sqkm'] = 0.0
    parameters['fault_count'] = 0
    
    provider_fault.rewind()
    for fault in provider_fault:
        
        fault_poly, vertices = utils.polygonsQGS2Shapely((fault,))
        if fault_poly[0].intersects(poly):
            
            parameters['fault_count'] += 1
            
            # QMessageBox.information(None, "Attributes", "%s" % fault.attributeMap())
            sliprate_min = \
                fault[attribute_map[sliprate_min_name][0]].toDouble()[0]
            sliprate_max = \
                fault[attribute_map[sliprate_max_name][0]].toDouble()[0]
            area_fault = utils.polygonAreaFromWGS84(fault_poly[0])
            
            # TODO(fab): correct scaling of moment rate from slip rate
            (rate_min, rate_max) = momentrate.momentrateFromSlipRate(
                sliprate_min, sliprate_max, area_fault)
            
            moment_rate_min += rate_min
            moment_rate_max += rate_max
            parameters['area_fault_sqkm'] += area_fault
            
    moment_rate_min /= eqcatalog.CATALOG_TIME_SPAN
    moment_rate_max /= eqcatalog.CATALOG_TIME_SPAN
            
    parameters['mr_slip'] = [moment_rate_min, moment_rate_max]
    parameters['area_fault_sqkm'] *= 1.0e-6

    return parameters

def updateDisplaysFaultBackgr(cls, parameters):
    """Update UI with computed values for selected fault background zone."""
    updateTextFaultBackgr(cls, parameters)
    updateMomentRateTableFaultBackgr(cls, parameters)
    #updateMomentRatePlotFaultBackgr(cls, parameters)

def updateTextFaultBackgr(cls, parameters):
    text = ''
    text += "<b>Activity</b><br/>"
    text += "(RM) all EQ: a: %s, b: %s (%s EQ)<br/>" % (
        utils.centralValueOfList(parameters['activity_a']), 
        utils.centralValueOfList(parameters['activity_b']),
        parameters['eq_count'])
    text += "(RM) below M%s: a: %s, b: %s (%s EQ)<br/>" % (
        FAULT_BACKGROUND_MAG_THRESHOLD,
        utils.centralValueOfList(parameters['activity_below_a']), 
        utils.centralValueOfList(parameters['activity_below_b']),
        parameters['eq_count_below'])
    text += "(RM) above M%s: a: %s, b: %s (%s EQ)<br/>" % (
        FAULT_BACKGROUND_MAG_THRESHOLD,
        utils.centralValueOfList(parameters['activity_above_a']), 
        utils.centralValueOfList(parameters['activity_above_b']),
        parameters['eq_count_above'])
    text += "(ML) all EQ: a: %s, b: %s (%s EQ)<br/>" % (None, None, 
        parameters['eq_count'])
    text += "Mmax: %s, %s faults with area of %s km^2 in background zone of %s km^2" % (
        parameters['mmax'], 
        parameters['fault_count'], 
        int(parameters['area_fault_sqkm']),
        int(parameters['area_background_sqkm']))
    cls.textFaultBackgrActivity.setText(text)

def updateMomentRateTableFaultBackgr(cls, parameters):
    cls.momentRateTableFault.clearContents()

    ## from EQs
    cls.momentRateTableFaultBackgr.setItem(0, 0, QTableWidgetItem(QString(
        "%.2e" % parameters['mr_eq'])))

    ## from activity (RM)
    
    # get maximum likelihood value from central line of table
    cls.momentRateTableFaultBackgr.setItem(0, 1, QTableWidgetItem(QString(
        "%.2e" % utils.centralValueOfList(parameters['mr_activity_below']))))
        
    cls.momentRateTableFaultBackgr.setItem(0, 2, QTableWidgetItem(QString(
        "%.2e" % utils.centralValueOfList(parameters['mr_activity_above']))))

    ## from geology (slip)
    cls.momentRateTableFaultBackgr.setItem(0, 3, QTableWidgetItem(QString(
        "%.2e" % parameters['mr_slip'][1])))

def updateMomentRatePlotFaultBackgr(cls, parameters):

    window = plots.createPlotWindow(cls)

    # new moment rate plot
    cls.fig_moment_rate_comparison_fault = \
        plots.MomentRateComparisonPlotFault()
    cls.fig_moment_rate_comparison_fault = \
        cls.fig_moment_rate_comparison_fault.plot(imgfile=None, 
            data=parameters)

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
