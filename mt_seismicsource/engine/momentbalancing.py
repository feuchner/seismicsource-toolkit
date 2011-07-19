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

from mt_seismicsource.engine import fmd

from mt_seismicsource.layers import areasource
from mt_seismicsource.layers import eqcatalog

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

    # zone ID and title
    (feature_id, feature_title, feature_name) = utils.getFeatureAttributes(
        cls.area_source_layer, feature, features.AREA_SOURCE_ATTRIBUTES_ID)
        
    if feature_title.toString() == '' and feature_name.toString() == '':
        zone_name_str = ""
    elif feature_title.toString() == '' and feature_name.toString() != '':
        zone_name_str = feature_name.toString()
    elif feature_title.toString() != '' and feature_name.toString() == '':
        zone_name_str = feature_title.toString()
    else:
        zone_name_str = "%s, %s" % (
            feature_title.toString(), feature_name.toString())
    
    parameters['plot_title_fmd'] = 'Zone %s, %s' % (
        feature_id.toInt()[0], zone_name_str)

    ## moment rate from EQs

    # get quakes from catalog (cut with polygon)
    poly_cat = QPCatalog.QPCatalog()
    poly_cat.merge(cls.catalog)
    poly_cat.cut(geometry=poly)
    
    # cut catalog with min/max depth according to UI spinboxes
    mindepth = eqcatalog.CUT_DEPTH_MIN
    maxdepth = eqcatalog.CUT_DEPTH_MAX
    if cls.checkBoxCatalogDepth.isChecked() is True:
        mindepth = cls.spinboxCatDepthMin.value()
        maxdepth = cls.spinboxCatDepthMax.value()
        
    poly_cat.cut(mindepth=mindepth, maxdepth=maxdepth)

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
    parameters['activity_mmin'] = atticivy.ATTICIVY_MMIN
    activity_a = [float(x) for x in activity_arr[1::3]]
    activity_b = [float(x) for x in activity_arr[2::3]]
    mmax = float(feature[attribute_mmax_idx].toDouble()[0])
    
    parameters['activity_a'] = activity_a
    parameters['activity_b'] = activity_b 
    parameters['mmax'] = mmax 

    ## Maximum likelihood a/b values
    cls.feature_data_area_source['fmd'] = fmd.computeZoneFMD(cls, feature, 
        poly_cat)
    (parameters['ml_a'], parameters['ml_b'], parameters['ml_mc']) = \
        fmd.getFMDValues(cls.feature_data_area_source['fmd'])

    ## moment rate from activity
    a_values = atticivy.activity2aValue(activity_a, activity_b, 
        parameters['activity_mmin'])
    momentrates_arr = numpy.array(momentrate.momentrateFromActivity(
        a_values, activity_b, mmax)) / eqcatalog.CATALOG_TIME_SPAN
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
    updateTextActivityArea(cls, parameters)
    updateTextMomentRateArea(cls, parameters)

def updateTextActivityArea(cls, parameters):
    
    central_A = utils.centralValueOfList(parameters['activity_a'])
    central_b = utils.centralValueOfList(parameters['activity_b'])
    
    text = ''
    text += "<b>Activity</b><br/>"
    text += "<b>(RM)</b> a: %.3f, b: %s, A: %s<br/>" % (
        atticivy.activity2aValue(central_A, central_b, 
            parameters['activity_mmin']), 
        central_b,
        central_A)
    text += "<b>(ML)</b> a: %.3f, b: %.3f (Mc %.1f)<br/>" % (
        parameters['ml_a'], 
        parameters['ml_b'],
        parameters['ml_mc'])
    text += "Mmin: %s, Mmax: %s, %s EQ in %s km<sup>2</sup> (area zone)" % (
        parameters['activity_mmin'],
        parameters['mmax'],
        parameters['eq_count'],
        int(parameters['area_sqkm']))
    cls.textActivityArea.setText(text)

def updateTextMomentRateArea(cls, parameters):
    text = ''
    text += "<b>Moment Rate</b><br/>"
    text += "[EQ] %.2e<br/>" % parameters['mr_eq']
    text += "[Act] %.2e<br/>" % (
        utils.centralValueOfList(parameters['mr_activity']))
    text += "[Strain (Bird)] %.2e<br/>" % parameters['mr_strain_bird']
    text += "[Strain (Barba)] %.2e" % parameters['mr_strain_barba']
    cls.textMomentRateArea.setText(text)

def updatePlotMomentRateArea(cls, parameters):

    window = plots.createPlotWindow(cls)

    # new moment rate plot
    plot = plots.MomentRateComparisonPlotArea()
    figure = plot.plot(imgfile=None, data=parameters)

    canvas = plots.PlotCanvas(figure, title=parameters['plot_title_fmd'])
    canvas.draw()

    # plot widget
    window.layoutPlot.addWidget(canvas)
    toolbar = plots.createToolbar(canvas, window)
    window.layoutPlot.addWidget(toolbar)
    
    return figure

# ----------------------------------------------------------------------------

def updateDataFault(cls, feature,
    m_threshold=recurrence.FAULT_BACKGROUND_MAG_THRESHOLD):
    """Update or compute moment rates for selected feature of fault source
    zone layer.

    Input:
        feature         QGis polygon feature from fault source layer

    Output:
        parameters      dict of computed parameters
    """

    provider = cls.fault_source_layer.dataProvider()
    provider_fault_back = cls.fault_background_layer.dataProvider()
    provider_back = cls.background_zone_layer.dataProvider()

    parameters = {}

    # zone ID and title
    (feature_id, feature_name) = utils.getFeatureAttributes(
        cls.fault_background_layer, feature, 
        features.FAULT_BACKGROUND_ATTRIBUTES_ID)

    if feature_name.toString() != '':
        zone_name_str = feature_name.toString()
    else:
        zone_name_str = ""
    
    parameters['plot_title_recurrence'] = 'Zone %s, %s' % (
        feature_id.toString(), zone_name_str)
        
    # get Shapely polygon from feature geometry
    polylist, vertices = utils.polygonsQGS2Shapely((feature,))
    fault_poly = polylist[0]

    # fault zone polygon area in square kilometres
    parameters['area_fault_sqkm'] = utils.polygonAreaFromWGS84(
        fault_poly) * 1.0e-6

    # get buffer zone around fault zone (convert buffer distance to degrees)
    (bz_poly, parameters['area_bz_sqkm']) = utils.computeBufferZone(
        fault_poly, momentrate.BUFFER_AROUND_FAULT_ZONE_KM)

    # find fault background zone in which centroid of fault zone lies
    # NOTE: this can yield a wrong background zone if the fault zone
    # is curved and at the edge of background zone.
    # TODO(fab): use GIS "within" function instead, but note that fault
    # zone can overlap several BG zones
    (fbz, fbz_poly, parameters['area_fbz_sqkm']) = utils.findBackgroundZone(
        fault_poly.centroid, provider_fault_back)

    recurrence_attributes = getAttributesFromRecurrence(provider, feature)
    parameters.update(recurrence_attributes)
    
    # get mmax and mcdist for FBZ from background zone
    (mcdist_qv, mmax_qv) = areasource.getAttributesFromBackgroundZones(
        fbz_poly.centroid, provider_back, areasource.MCDIST_MMAX_ATTRIBUTES)
        
    mmax = float(mmax_qv.toDouble()[0])
    mcdist = str(mcdist_qv.toString())
    
    parameters['mmax'] = mmax
    
    ## moment rate from EQs

    # get quakes from catalog (cut with fault background polygon)
    fbz_cat = QPCatalog.QPCatalog()
    fbz_cat.merge(cls.catalog)
    fbz_cat.cut(geometry=fbz_poly)
    
    # cut catalog with min/max depth according to UI spinboxes
    mindepth = eqcatalog.CUT_DEPTH_MIN
    maxdepth = eqcatalog.CUT_DEPTH_MAX
    if cls.checkBoxCatalogDepth.isChecked() is True:
        mindepth = cls.spinboxCatDepthMin.value()
        maxdepth = cls.spinboxCatDepthMax.value()
        
    fbz_cat.cut(mindepth=mindepth, maxdepth=maxdepth)
    
    bz_cat = QPCatalog.QPCatalog()
    bz_cat.merge(cls.catalog)
    bz_cat.cut(geometry=bz_poly)
    bz_cat.cut(mindepth=mindepth, maxdepth=maxdepth)
    
    parameters['eq_count_fbz'] = fbz_cat.size()
    parameters['eq_count_bz'] = bz_cat.size()
    
    # sum up moment from quakes (converted from Mw with Kanamori eq.)
    # use quakes in buffer zone
    magnitudes = []
    for ev in bz_cat.eventParameters.event:
        mag = ev.getPreferredMagnitude()
        magnitudes.append(mag.mag.value)

    moment = numpy.array(momentrate.magnitude2moment(magnitudes))

    # scale moment: per year and area (in km^2)
    # TODO(fab): compute real catalog time span
    parameters['mr_eq'] = moment.sum() / (
        parameters['area_bz_sqkm'] * eqcatalog.CATALOG_TIME_SPAN)

    ## moment rate from activity (RM)

    # moment rates from activity: use a and b values from buffer zone

    act_bz_arr = parameters['activity_bz'].strip().split()
    a_bz_arr = [float(x) for x in act_bz_arr[1::3]]
    b_bz_arr = [float(x) for x in act_bz_arr[2::3]]
    
    a_values = atticivy.activity2aValue(a_bz_arr, b_bz_arr)
    momentrates_arr = numpy.array(momentrate.momentrateFromActivity(
        a_values, b_bz_arr, mmax)) / eqcatalog.CATALOG_TIME_SPAN

    parameters['mr_activity'] = momentrates_arr.tolist()

    # moment rates from activity: use a and b values from FBZ 
    # (above threshold)

    act_fbz_at_arr = parameters['activity_fbz_at'].strip().split()
    a_fbz_at_arr = [float(x) for x in act_fbz_at_arr[1::3]]
    b_fbz_at_arr = [float(x) for x in act_fbz_at_arr[2::3]]
    
    a_values = atticivy.activity2aValue(a_fbz_at_arr, b_fbz_at_arr)
    momentrates_fbz_at_arr = numpy.array(momentrate.momentrateFromActivity(
        a_values, b_fbz_at_arr, mmax)) / eqcatalog.CATALOG_TIME_SPAN

    parameters['mr_activity_fbz_at'] = momentrates_fbz_at_arr.tolist()
    
    parameters['activity_m_threshold'] = m_threshold

    # FMD from quakes in FBZ
    cls.feature_data_fault_source['fmd'] = fmd.computeZoneFMD(cls, feature, 
        fbz_cat)
    (parameters['ml_a'], parameters['ml_b'], parameters['ml_mc']) = \
        fmd.getFMDValues(cls.feature_data_fault_source['fmd'])
        
    ## moment rate from slip rate

    # TODO(fab): check correct scaling of moment rate from slip rate
    (moment_rate_min, moment_rate_max) = \
        momentrate.momentrateFromSlipRate(parameters['sliprate_min'], 
            parameters['sliprate_max'], 
            parameters['area_fault_sqkm'] * 1.0e6)

    parameters['mr_slip'] = [moment_rate_min, moment_rate_max]
    
    return parameters

def updateDisplaysFault(cls, parameters):
    """Update UI with computed values for selected fault zone."""
    updateTextActivityFault(cls, parameters)
    updateTextMomentRateFault(cls, parameters)

def updateTextActivityFault(cls, parameters):

    text = ''
    text += "<b>Activity</b><br/>"
    text += "<b>(RM)</b> a: %.3f b: %.3f A: %.3f (%s km buffer)<br/>" % (
        atticivy.activity2aValue(parameters['activity_bz_a'], 
            parameters['activity_bz_b']), 
        parameters['activity_bz_b'], 
        parameters['activity_bz_a'],
        int(momentrate.BUFFER_AROUND_FAULT_ZONE_KM))
        
    text += "<b>(RM)</b> a: %.3f b: %.3f A: %.3f (FBZ, ID %s)<br/>" % (
        atticivy.activity2aValue(parameters['activity_fbz_a'], 
            parameters['activity_fbz_b']), 
        parameters['activity_fbz_b'], 
        parameters['activity_fbz_a'], 
        parameters['fbz_id'])
        
    text += "<b>(RM)</b> a: %.3f b: %.3f A: %.3f (FBZ, above M%s)<br/>" % (
        atticivy.activity2aValue(parameters['activity_fbz_at_a'], 
            parameters['activity_fbz_at_b']), 
        parameters['activity_fbz_at_b'],
        parameters['activity_fbz_at_a'], 
        parameters['activity_m_threshold'])
        
    text += \
        "<b>(from slip)</b> a: %.3f (min), %.3f (max), b: %.3f (FBZ)<br/>" % (
        parameters['activity_rec_a_min'],
        parameters['activity_rec_a_max'],
        parameters['activity_fbz_b'])
        
    text += "%s EQ in %s km<sup>2</sup> (buffer zone)<br/>" % (
        parameters['eq_count_bz'],
        int(parameters['area_bz_sqkm']))
        
    text += "%s EQ in %s km<sup>2</sup> (FBZ)<br/>" % (
        parameters['eq_count_fbz'],
        int(parameters['area_fbz_sqkm']))
        
    text += "Mmax: %s (background), %s (fault) " % (
        parameters['mmax'],
        parameters['mmax_fault'])
    cls.textActivityFault.setText(text)

def updateTextMomentRateFault(cls, parameters):

    text = ''
    text += "<b>Moment Rate</b><br/>"
    text += "[EQ] %.2e<br/>" % parameters['mr_eq']
    text += "[Act (buffer)] %.2e<br/>" % (
        utils.centralValueOfList(parameters['mr_activity']))
    text += "[Act (FBZ)] %.2e<br/>" % (
        utils.centralValueOfList(parameters['mr_activity_fbz_at']))
    text += "[Slip (min)] %.2e<br/>" %  parameters['mr_slip'][0]
    text += "[Slip (max)] %.2e" %  parameters['mr_slip'][1]
    cls.textMomentRateFault.setText(text)

def updatePlotMomentRateFault(cls, parameters):

    window = plots.createPlotWindow(cls)

    # new moment rate plot
    plot = plots.MomentRateComparisonPlotFault()
        
    figure = plot.plot(imgfile=None, data=parameters)

    canvas = plots.PlotCanvas(figure, 
        title=parameters['plot_title_recurrence'])
    canvas.draw()

    # plot widget
    window.layoutPlot.addWidget(canvas)
    toolbar = plots.createToolbar(canvas, window)
    window.layoutPlot.addWidget(toolbar)
    
    return figure

# ----------------------------------------------------------------------------

def updateDataFaultBackgr(cls, feature, 
    m_threshold=recurrence.FAULT_BACKGROUND_MAG_THRESHOLD):
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

    # get mmax and mcdist for FBZ from background zone
    (mcdist_qv, mmax_qv) = areasource.getAttributesFromBackgroundZones(
        poly.centroid, provider_back, areasource.MCDIST_MMAX_ATTRIBUTES)
        
    mmax = float(mmax_qv.toDouble()[0])
    mcdist = str(mcdist_qv.toString())

    parameters['mmax'] = mmax 
    
    ## moment rate from EQs

    # get quakes from catalog (cut with fault background zone polygon)
    poly_cat = QPCatalog.QPCatalog()
    poly_cat.merge(cls.catalog)
    poly_cat.cut(geometry=poly)
    
    # cut catalog with min/max depth according to UI spinboxes
    mindepth = eqcatalog.CUT_DEPTH_MIN
    maxdepth = eqcatalog.CUT_DEPTH_MAX
    if cls.checkBoxCatalogDepth.isChecked() is True:
        mindepth = cls.spinboxCatDepthMin.value()
        maxdepth = cls.spinboxCatDepthMax.value()
        
    poly_cat.cut(mindepth=mindepth, maxdepth=maxdepth)
    
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
    
    parameters['activity_mmin'] = atticivy.ATTICIVY_MMIN
    activity = atticivy.computeActivityAtticIvy(
        (poly, ), (mmax, ), (mcdist, ), cls.catalog, 
        mmin=parameters['activity_mmin'])
    
    # get RM (weight, a, b) values from feature attribute
    activity_str = activity[0][2]
    activity_arr = activity_str.strip().split()
    
    # ignore weights
    activity_a = [float(x) for x in activity_arr[1::3]]
    activity_b = [float(x) for x in activity_arr[2::3]]
    parameters['activity_a'] = activity_a
    parameters['activity_b'] = activity_b 
    
    a_values = atticivy.activity2aValue(activity_a, activity_b, 
        parameters['activity_mmin'])
    momentrates_arr = numpy.array(momentrate.momentrateFromActivity(
        a_values, activity_b, mmax)) / eqcatalog.CATALOG_TIME_SPAN
    parameters['mr_activity'] = momentrates_arr.tolist()
    
    # get separate catalogs below and above magnitude threshold
    cat_below_threshold = QPCatalog.QPCatalog()
    cat_below_threshold.merge(poly_cat)
    cat_below_threshold.cut(maxmag=m_threshold, maxmag_excl=True)
    parameters['eq_count_below'] = cat_below_threshold.size()
        
    cat_above_threshold = QPCatalog.QPCatalog()
    cat_above_threshold.merge(poly_cat)
    cat_above_threshold.cut(minmag=m_threshold, maxmag_excl=False)
    parameters['eq_count_above'] = cat_above_threshold.size()

    activity_below_threshold = atticivy.computeActivityAtticIvy(
        (poly,), (mmax,), (mcdist,), cat_below_threshold, 
        mmin=parameters['activity_mmin'])

    activity_above_threshold = atticivy.computeActivityAtticIvy(
        (poly,), (mmax,), (mcdist,), cat_above_threshold, 
        mmin=parameters['activity_mmin'])
        
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
    
    a_values_below = atticivy.activity2aValue(activity_below_a, 
        activity_below_b, parameters['activity_mmin'])
    momentrates_below_arr = numpy.array(momentrate.momentrateFromActivity(
        a_values_below, activity_below_b, mmax)) / eqcatalog.CATALOG_TIME_SPAN
            
    a_values_above = atticivy.activity2aValue(activity_above_a, 
        activity_above_b, parameters['activity_mmin'])
    momentrates_above_arr = numpy.array(momentrate.momentrateFromActivity(
        a_values_above, activity_above_b, mmax)) / eqcatalog.CATALOG_TIME_SPAN
            
    parameters['activity_below_a'] = activity_below_a
    parameters['activity_below_b'] = activity_below_b 
    
    parameters['activity_above_a'] = activity_above_a
    parameters['activity_above_b'] = activity_above_b 
    
    parameters['mr_activity_below'] = momentrates_below_arr.tolist()
    parameters['mr_activity_above'] = momentrates_above_arr.tolist()
    
    parameters['activity_m_threshold'] = m_threshold
    
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

def updateDisplaysFaultBackgr(cls, parameters):
    """Update UI with computed values for selected fault background zone."""
    updateTextActivityFaultBackgr(cls, parameters)
    updateTextMomentRateFaultBackgr(cls, parameters)

def updateTextActivityFaultBackgr(cls, parameters):
    
    central_A = utils.centralValueOfList(parameters['activity_a'])
    central_b = utils.centralValueOfList(parameters['activity_b'])
    
    central_A_below = utils.centralValueOfList(parameters['activity_below_a'])
    central_b_below = utils.centralValueOfList(parameters['activity_below_b'])
    
    central_A_above = utils.centralValueOfList(parameters['activity_above_a'])
    central_b_above = utils.centralValueOfList(parameters['activity_above_b'])

    text = ''
    text += "<b>Activity</b><br/>"
    text += "<b>(RM)</b> all EQ: a: %.3f, b: %s, A: %s (%s EQ)<br/>" % (
        atticivy.activity2aValue(central_A, central_b, 
            parameters['activity_mmin']), 
        central_b,
        central_A,
        parameters['eq_count'])
    text += "<b>(RM)</b> below M%s: a: %.3f, b: %s, A: %s (%s EQ)<br/>" % (
        parameters['activity_m_threshold'],
        atticivy.activity2aValue(central_A_below, central_b_below, 
            parameters['activity_mmin']), 
        central_b_below,
        central_A_below,
        parameters['eq_count_below'])
    text += "<b>(RM)</b> above M%s: a: %.3f, b: %s, A: %s (%s EQ)<br/>" % (
        parameters['activity_m_threshold'],
        atticivy.activity2aValue(central_A_above, central_b_above, 
            parameters['activity_mmin']), 
        central_b_above,
        central_A_above,
        parameters['eq_count_above'])
    text += "<b>(ML)</b> all EQ: a: %s, b: %s (%s EQ)<br/>" % (None, None, 
        parameters['eq_count'])
    text += "Mmin: %s, Mmax: %s, %s faults with area of %s km<sup>2</sup> in background zone of %s km<sup>2</sup>" % (
        parameters['activity_mmin'],
        parameters['mmax'], 
        parameters['fault_count'], 
        int(parameters['area_fault_sqkm']),
        int(parameters['area_background_sqkm']))
    cls.textActivityFaultBackgr.setText(text)

def updateTextMomentRateFaultBackgr(cls, parameters):
    text = ''
    text += "<b>Moment Rate</b><br/>"
    text += "[EQ] %.2e<br/>" % parameters['mr_eq']
    text += "[Act] %.2e<br/>" % (
        utils.centralValueOfList(parameters['mr_activity']))
    text += "[Act (below M%s)] %.2e<br/>" % (
        parameters['activity_m_threshold'],
        utils.centralValueOfList(parameters['mr_activity_below']))
    text += "[Act (above M%s)] %.2e<br/>" % (
        parameters['activity_m_threshold'],
        utils.centralValueOfList(parameters['mr_activity_above']))
    text += "[Slip (min)] %.2e<br/>" %  parameters['mr_slip'][0]
    text += "[Slip (max)] %.2e<br/>" %  parameters['mr_slip'][1]
    
    text += "[Strain (Bird)] %.2e<br/>" % parameters['mr_strain_bird']
    text += "[Strain (Barba)] %.2e" % parameters['mr_strain_barba']
    cls.textMomentRateFaultBackgr.setText(text)

# ----------------------------------------------------------------------------

def getAttributesFromRecurrence(provider, feature):
    """Read recurrence attributes from fault layer."""
    
    parameters = {}
    
    attribute_map_fault = utils.getAttributeIndex(provider, 
        features.FAULT_SOURCE_ATTRIBUTES_RECURRENCE, create=False)
        
    # get fault background zone ID
    id_name = features.FAULT_SOURCE_ATTR_ID_FBZ['name']
    parameters['fbz_id'] = str(
        feature[attribute_map_fault[id_name][0]].toString())
        
    # a and b value from FBZ (fault layer attributes)

    a_fbz_name = features.FAULT_SOURCE_ATTR_A_FBZ['name']
    b_fbz_name = features.FAULT_SOURCE_ATTR_B_FBZ['name']
    act_fbz_name = features.FAULT_SOURCE_ATTR_ACT_FBZ['name']

    parameters['activity_fbz_a'] = \
        feature[attribute_map_fault[a_fbz_name][0]].toDouble()[0]
    parameters['activity_fbz_b'] = \
        feature[attribute_map_fault[b_fbz_name][0]].toDouble()[0]
    parameters['activity_fbz'] = str(
        feature[attribute_map_fault[act_fbz_name][0]].toString())
    
    # a and b value from buffer zone (fault layer attributes)

    a_bz_name = features.FAULT_SOURCE_ATTR_A_BUF['name']
    b_bz_name = features.FAULT_SOURCE_ATTR_B_BUF['name']
    act_bz_name = features.FAULT_SOURCE_ATTR_ACT_BUF['name']

    parameters['activity_bz_a'] = \
        feature[attribute_map_fault[a_bz_name][0]].toDouble()[0]
    parameters['activity_bz_b'] = \
        feature[attribute_map_fault[b_bz_name][0]].toDouble()[0]
    parameters['activity_bz'] = str(
        feature[attribute_map_fault[act_bz_name][0]].toString())
    
    # a and b value from FBZ, above magnitude threshold

    a_fbz_at_name = features.FAULT_SOURCE_ATTR_A_FBZ_AT['name']
    b_fbz_at_name = features.FAULT_SOURCE_ATTR_B_FBZ_AT['name']
    act_fbz_at_name = features.FAULT_SOURCE_ATTR_ACT_FBZ_AT['name']

    parameters['activity_fbz_at_a'] = \
        feature[attribute_map_fault[a_fbz_at_name][0]].toDouble()[0]
    parameters['activity_fbz_at_b'] = \
        feature[attribute_map_fault[b_fbz_at_name][0]].toDouble()[0]
    parameters['activity_fbz_at'] = str(
        feature[attribute_map_fault[act_fbz_at_name][0]].toString())
    
    # a values from recurrence (fault layer attributes)
    
    a_rec_min_name = features.FAULT_SOURCE_ATTR_A_REC_MIN['name']
    a_rec_max_name = features.FAULT_SOURCE_ATTR_A_REC_MAX['name']
    
    parameters['activity_rec_a_min'] = \
        feature[attribute_map_fault[a_rec_min_name][0]].toDouble()[0]
    parameters['activity_rec_a_max'] = \
        feature[attribute_map_fault[a_rec_max_name][0]].toDouble()[0]
        
    sliprate_min_name = features.FAULT_SOURCE_ATTR_SLIPRATE_MIN['name']
    sliprate_max_name = features.FAULT_SOURCE_ATTR_SLIPRATE_MAX['name']
    mmax_fault_name = features.FAULT_SOURCE_ATTR_MAGNITUDE_MAX['name']
    
    parameters['sliprate_min'] = \
        feature[attribute_map_fault[sliprate_min_name][0]].toDouble()[0]
    parameters['sliprate_max'] = \
        feature[attribute_map_fault[sliprate_max_name][0]].toDouble()[0]
    parameters['mmax_fault'] = \
        feature[attribute_map_fault[mmax_fault_name][0]].toDouble()[0]

    return parameters
    