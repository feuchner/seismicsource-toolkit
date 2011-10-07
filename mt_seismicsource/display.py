# -*- coding: utf-8 -*-
"""
SHARE Seismic Source Toolkit

This module holds functions for displaying parameters in the UI.

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

from mt_seismicsource import features
from mt_seismicsource import plots
from mt_seismicsource import utils

from mt_seismicsource.algorithms import atticivy
from mt_seismicsource.algorithms import momentrate

def updateDisplaysArea(cls, parameters, feature):
    """Update UI with computed values for selected area zone."""
    updateLabelZoneIDArea(cls, parameters, feature)
    updateTextActivityArea(cls, parameters)
    updateTextMomentRateArea(cls, parameters)

def updateLabelZoneIDArea(cls, parameters, feature):
    """Update UI with ID and name of selected ASZ."""
    
    id_name = features.AREA_SOURCE_ATTR_ID['name']
    title_name = features.AREA_SOURCE_ATTR_TITLE['name']
    name_name = features.AREA_SOURCE_ATTR_NAME['name']
    
    cls.labelMomentRateAreaID.setText("ID: %s Title: %s Name: %s (%s)" % (
        parameters[id_name], parameters[title_name], parameters[name_name], 
        feature.id()))
        
def updateTextActivityArea(cls, parameters):
    
    rm_a_name = features.AREA_SOURCE_ATTR_A_RM['name']
    rm_b_name = features.AREA_SOURCE_ATTR_B_RM['name']
    ml_a_name = features.AREA_SOURCE_ATTR_A_ML['name']
    ml_b_name = features.AREA_SOURCE_ATTR_B_ML['name']
    ml_mc_name = features.AREA_SOURCE_ATTR_MC['name']
    mmax_name = features.AREA_SOURCE_ATTR_MMAX['name']
    eq_count_name = features.AREA_SOURCE_ATTR_EQ_CNT['name']
    ml_magctr_name = features.AREA_SOURCE_ATTR_MAGCTR_ML['name']
    area_sqkm_name = features.AREA_SOURCE_ATTR_AREA['name']
    
    text = ''
    text += "<b>Activity</b><br/>"
    text += "<b>(RM)</b> a: %.3f, b: %s, A: %.3f (Mmin %.1f)<br/>" % (
        parameters[rm_a_name],
        parameters[rm_b_name],
        atticivy.aValue2activity(parameters[rm_a_name], parameters[rm_b_name],
            parameters[atticivy.ATTICIVY_MMIN_KEY_NAME]), 
        parameters[atticivy.ATTICIVY_MMIN_KEY_NAME])
    text += "<b>(ML)</b> a: %.3f, b: %.3f (Mc %.1f)<br/>" % (
        parameters[ml_a_name], 
        parameters[ml_b_name],
        parameters[ml_mc_name])
    text += "Mmax: %s, %s EQ (%s above Mc) in %s km<sup>2</sup> "\
            "(area zone)" % (
        parameters[mmax_name],
        parameters[eq_count_name],
        parameters[ml_magctr_name],
        int(parameters[area_sqkm_name]))
    cls.textActivityArea.setText(text)

def updateTextMomentRateArea(cls, parameters):
    
    mr_eq_name = features.AREA_SOURCE_ATTR_MR_EQ['name']
    mr_activity_name = features.AREA_SOURCE_ATTR_MR_ACTIVITY['name']
    mr_strain_bird_name = features.AREA_SOURCE_ATTR_MR_STRAIN_BIRD['name']
    mr_strain_barba_name = features.AREA_SOURCE_ATTR_MR_STRAIN_BARBA['name']
    
    text = ''
    text += "<b>Moment Rate</b><br/>"
    text += "[EQ] %.2e<br/>" % parameters[mr_eq_name]
    text += "[Act] %.2e<br/>" % (
        utils.centralValueOfList(
        [float(x) for x in parameters[mr_activity_name].split()]))
    text += "[Strain (Bird)] %.2e<br/>" % parameters[mr_strain_bird_name]
    text += "[Strain (Barba)] %.2e" % parameters[mr_strain_barba_name]
    cls.textMomentRateArea.setText(text)

def updatePlotMomentRateArea(cls, parameters):

    window = plots.createPlotWindow(cls)

    # new moment rate plot
    plot = plots.MomentRateComparisonPlotArea()
    figure = plot.plot(imgfile=None, data=parameters)

    canvas = plots.PlotCanvas(figure, 
        title=parameters[plots.PLOT_TITLE_FMD_NAME])
    canvas.draw()

    # plot widget
    window.layoutPlot.addWidget(canvas)
    toolbar = plots.createToolbar(canvas, window)
    window.layoutPlot.addWidget(toolbar)
    
    return figure

# ----------------------------------------------------------------------------

def updateDisplaysFault(cls, parameters, feature):
    """Update UI with computed values for selected fault zone."""
    
    if parameters is None:
        return
    else:
        updateLabelZoneIDFault(cls, parameters, feature)
        updateTextActivityFault(cls, parameters)
        updateTextMomentRateFault(cls, parameters)

def updateLabelZoneIDFault(cls, parameters, feature):
    """Update UI with ID and name of selected FSZ."""

    id_name = features.FAULT_SOURCE_ATTR_ID['name']
    name_name = features.FAULT_SOURCE_ATTR_NAME['name']
    
    cls.labelMomentRateFaultID.setText("ID: %s Name: %s (%s)" % (
        parameters[id_name], parameters[name_name], feature.id()))

def updateTextActivityFault(cls, parameters):

    bz_a_name = features.FAULT_SOURCE_ATTR_A_BUF['name']
    bz_b_name = features.FAULT_SOURCE_ATTR_B_BUF['name']
    fbz_a_name = features.FAULT_SOURCE_ATTR_A_FBZ['name']
    fbz_b_name = features.FAULT_SOURCE_ATTR_B_FBZ['name']
    fbz_id_name = features.FAULT_SOURCE_ATTR_ID_FBZ['name']
    fbz_at_a_name = features.FAULT_SOURCE_ATTR_A_FBZ_AT['name']
    fbz_at_b_name = features.FAULT_SOURCE_ATTR_B_FBZ_AT['name']
    m_threshold_name = features.FAULT_SOURCE_ATTR_M_THRES['name']
    rec_a_min_name = features.FAULT_SOURCE_ATTR_A_REC_MIN['name']
    rec_a_max_name = features.FAULT_SOURCE_ATTR_A_REC_MAX['name']
    
    ml_a_name = features.FAULT_SOURCE_ATTR_A_ML['name']
    ml_b_name = features.FAULT_SOURCE_ATTR_B_ML['name']
    ml_mc_name = features.FAULT_SOURCE_ATTR_MC_ML['name']
    ml_magctr_name = features.FAULT_SOURCE_ATTR_MAGCTR_ML['name']
    
    mmax_name = features.FAULT_SOURCE_ATTR_MMAX_BG['name']
    mmax_fault_name = features.FAULT_SOURCE_ATTR_MAGNITUDE_MAX['name']
    
    eq_count_fbz_name = features.FAULT_SOURCE_ATTR_EQ_CNT_FBZ['name']
    area_fbz_sqkm_name = features.FAULT_SOURCE_ATTR_AREA_FBZ['name']
    eq_count_bz_name = features.FAULT_SOURCE_ATTR_EQ_CNT_BZ['name']
    area_bz_sqkm_name = features.FAULT_SOURCE_ATTR_AREA_BZ['name']
    
    text = ''
    text += "<b>Activity</b><br/>"
    text += "<b>(RM)</b> a: %.3f b: %.3f A: %.3f (%s km buffer)<br/>" % (
        parameters[bz_a_name],
        parameters[bz_b_name], 
        atticivy.aValue2activity(parameters[bz_a_name], 
            parameters[bz_b_name]), 
        int(momentrate.BUFFER_AROUND_FAULT_ZONE_KM))
        
    text += "<b>(RM)</b> a: %.3f b: %.3f A: %.3f (FBZ, ID %s)<br/>" % (
        parameters[fbz_a_name], 
        parameters[fbz_b_name], 
        atticivy.aValue2activity(parameters[fbz_a_name], 
            parameters[fbz_b_name]), 
        parameters[fbz_id_name])
        
    text += "<b>(RM)</b> a: %.3f b: %.3f A: %.3f (FBZ, above M%s)<br/>" % (
        parameters[fbz_at_a_name],  
        parameters[fbz_at_b_name],
        atticivy.aValue2activity(parameters[fbz_at_a_name], 
            parameters[fbz_at_b_name]),
        parameters[m_threshold_name])
        
    text += \
        "<b>(from slip)</b> a: %.3f (min), %.3f (max), b: %.3f (FBZ)<br/>" % (
        parameters[rec_a_min_name],
        parameters[rec_a_max_name],
        parameters[fbz_b_name])
    
    try:
        area_fbz_sqkm = int(parameters[area_fbz_sqkm_name])
    except TypeError:
        area_fbz_sqkm = parameters[area_fbz_sqkm_name]
        
    text += \
        "<b>(ML)</b> a: %.3f, b: %.3f (%s EQ, %s above Mc %.1f, in "\
        "%s km<sup>2</sup> FBZ)<br/>" % (
            parameters[ml_a_name], 
            parameters[ml_b_name], 
            parameters[eq_count_fbz_name],
            parameters[ml_magctr_name],
            parameters[ml_mc_name],
            area_fbz_sqkm)
    
    try:
        area_bz_sqkm = int(parameters[area_bz_sqkm_name])
    except TypeError:
        area_bz_sqkm = parameters[area_bz_sqkm_name]
        
    text += "%s EQ in %s km<sup>2</sup> (buffer zone)<br/>" % (
        parameters[eq_count_bz_name],
        area_bz_sqkm)
        
    text += "Mmax: %s (background), %s (fault) " % (
        parameters[mmax_name],
        parameters[mmax_fault_name])
    cls.textActivityFault.setText(text)

def updateTextMomentRateFault(cls, parameters):

    mr_eq_name = features.FAULT_SOURCE_ATTR_MR_EQ['name']
    mr_activity_buf_name = features.FAULT_SOURCE_ATTR_MR_ACTIVITY_BUF['name']
    mr_activity_fbz_at_name = features.FAULT_SOURCE_ATTR_MR_ACTIVITY_FBZ['name']
    mr_slip_min_name = features.FAULT_SOURCE_ATTR_MOMENTRATE_MIN['name']
    mr_slip_max_name = features.FAULT_SOURCE_ATTR_MOMENTRATE_MAX['name']
    
    try:
        mr_act_buf = utils.centralValueOfList(
            [float(x) for x in parameters[mr_activity_buf_name].split()])
    except (IndexError, KeyError, ValueError):
        mr_act_buf = numpy.nan
    
    try:
        mr_act_fbz_at = utils.centralValueOfList(
            [float(x) for x in parameters[mr_activity_fbz_at_name].split()])
    except (IndexError, KeyError, ValueError):
        mr_act_fbz_at = numpy.nan
        
    text = ''
    text += "<b>Moment Rate</b><br/>"
    text += "[EQ] %.2e<br/>" % parameters[mr_eq_name]
    text += "[Act (buffer)] %.2e<br/>" % (mr_act_buf)
    text += "[Act (FBZ)] %.2e<br/>" % (mr_act_fbz_at)
    text += "[Slip (min)] %.2e<br/>" % parameters[mr_slip_min_name]
    text += "[Slip (max)] %.2e" % parameters[mr_slip_max_name]
    cls.textMomentRateFault.setText(text)
    
def updatePlotMomentRateFault(cls, parameters):

    window = plots.createPlotWindow(cls)

    # new moment rate plot
    plot = plots.MomentRateComparisonPlotFault()

    # add moment rate from slip data field for plot
    parameters[plots.MOMENT_RATE_FROM_SLIP_KEY_NAME] = [
        float(parameters[features.FAULT_SOURCE_ATTR_MOMENTRATE_MIN['name']]), 
        float(parameters[features.FAULT_SOURCE_ATTR_MOMENTRATE_MAX['name']])]
    
    figure = plot.plot(imgfile=None, data=parameters)

    canvas = plots.PlotCanvas(figure, 
        title=parameters[plots.PLOT_TITLE_RECURRENCE_NAME])
    canvas.draw()

    # plot widget
    window.layoutPlot.addWidget(canvas)
    toolbar = plots.createToolbar(canvas, window)
    window.layoutPlot.addWidget(toolbar)
    
    return figure

# ----------------------------------------------------------------------------

def updateDisplaysFaultBackgr(cls, parameters, feature):
    """Update UI with computed values for selected fault background zone."""
    updateLabelZoneIDFaultBackgr(cls, feature)
    updateTextActivityFaultBackgr(cls, parameters)
    updateTextMomentRateFaultBackgr(cls, parameters)

def updateLabelZoneIDFaultBackgr(cls, feature):
    """Update UI with ID and name of selected FBZ."""
    (feature_id, feature_name) = utils.getFeatureAttributes(
        cls.fault_background_layer, feature, 
        features.FAULT_BACKGROUND_ATTRIBUTES_ID)
    
    cls.labelMomentRateFaultBackgrID.setText("ID: %s Name: %s (%s)" % (
        int(feature_id.toDouble()[0]), feature_name.toString(), feature.id()))

def updateTextActivityFaultBackgr(cls, parameters):
    
    central_A = utils.centralValueOfList(parameters['activity_a'])
    central_b = utils.centralValueOfList(parameters['activity_b'])
    
    central_A_below = utils.centralValueOfList(parameters['activity_below_a'])
    central_b_below = utils.centralValueOfList(parameters['activity_below_b'])
    
    central_A_above = utils.centralValueOfList(parameters['activity_above_a'])
    central_b_above = utils.centralValueOfList(parameters['activity_above_b'])

    text = ''
    text += "<b>Activity</b><br/>"
    text += "<b>(RM)</b> all EQ: a: %.3f, b: %s, A: %.3f (%s EQ)<br/>" % (
        central_A,
        central_b,
        atticivy.aValue2activity(central_A, central_b, 
            parameters['activity_mmin']), 
        parameters['eq_count'])
    text += "<b>(RM)</b> below M%s: a: %.3f, b: %s, A: %.3f (%s EQ)<br/>" % (
        parameters['activity_m_threshold'],
        central_A_below,
        central_b_below,
        atticivy.aValue2activity(central_A_below, central_b_below, 
            parameters['activity_mmin']), 
        parameters['eq_count_below'])
    text += "<b>(RM)</b> above M%s: a: %.3f, b: %s, A: %.3f (%s EQ)<br/>" % (
        parameters['activity_m_threshold'],
        central_A_above,
        central_b_above,
        atticivy.aValue2activity(central_A_above, central_b_above, 
            parameters['activity_mmin']), 
        parameters['eq_count_above'])
        
    text += \
        "<b>(ML)</b> all EQ: a: %.3f, b: %.3f (%s EQ, %s above "\
        "Mc %.1f)<br/>" % (
            parameters['ml_a'], 
            parameters['ml_b'], 
            parameters['eq_count'],
            parameters['ml_magctr'],
            parameters['ml_mc'])
    text += "Mmin: %s, Mmax: %s, %s faults with area of %s km<sup>2</sup> in "\
    "background zone of %s km<sup>2</sup>" % (
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

