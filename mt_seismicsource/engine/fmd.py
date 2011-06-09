# -*- coding: utf-8 -*-
"""
SHARE Seismic Source Toolkit

Computations for frequency-magnitude distribution (FMD).

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
import qpplot

from mt_seismicsource import plots
from mt_seismicsource import utils

MIN_EVENTS_FOR_GR = 50
FMD_COMPUTE_ANNUAL_RATE = True

def computeZoneFMD(cls, feature):
    """Compute FMD for selected feature."""

    cls.figures['fmd'] = {}

    # cut catalog to feature
    polylist, vertices = utils.polygonsQGS2Shapely((feature,))
    poly = polylist[0]
    
    # cut catalog with selected polygons
    catalog_selected = QPCatalog.QPCatalog()
    catalog_selected.merge(cls.catalog)
    catalog_selected.cut(geometry=poly)

    cls.figures['fmd']['fmd'] = catalog_selected.getFmd(
        minEventsGR=MIN_EVENTS_FOR_GR)
    return cls.figures['fmd']['fmd']

def updateFMDDisplay(cls):
    if 'fmd' in cls.figures:
        displayFMDValues(cls)
        plotFMD(cls)

def displayFMDValues(cls, normalize=FMD_COMPUTE_ANNUAL_RATE):
    """Updates a, b, and Mc value display."""

    if normalize is True:
        aValue = cls.figures['fmd']['fmd'].GR['aValueNormalized']
    else:
        aValue = cls.figures['fmd']['fmd'].GR['aValue']

    return (aValue, cls.figures['fmd']['fmd'].GR['bValue'],
        cls.figures['fmd']['fmd'].GR['Mmin'])

def plotFMD(cls, normalize=FMD_COMPUTE_ANNUAL_RATE):

    window = plots.createPlotWindow(cls)

    # new FMD plot (returns figure)
    cls.figures['fmd']['fig'] = cls.figures['fmd']['fmd'].plot(
        imgfile=None, fmdtype='cumulative', 
        normalize=normalize)

    cls.fmd_canvas = plots.PlotCanvas(cls.figures['fmd']['fig'], 
        title="FMD")
    cls.fmd_canvas.draw()

    # FMD plot window, re-populate layout
    window.layoutPlot.addWidget(cls.fmd_canvas)
    cls.fmd_toolbar = plots.createToolbar(cls.fmd_canvas, window)
    window.layoutPlot.addWidget(cls.fmd_toolbar)

def updateRecurrenceDisplay(cls, feature):
    cls.figures['recurrence'] = {}
    plotRecurrence(cls, feature)

def plotRecurrence(cls, feature):

    window = plots.createPlotWindow(cls)

    pr = cls.fault_source_layer.dataProvider()
    activity_min_idx = pr.fieldNameIndex('actrate_mi')
    activity_max_idx = pr.fieldNameIndex('actrate_ma')

    distrostring_min = str(feature[activity_min_idx].toString())
    distrostring_max = str(feature[activity_max_idx].toString())
    distrodata_min = utils.distrostring2plotdata(distrostring_min)
    distrodata_max = utils.distrostring2plotdata(distrostring_max)

    distrodata = numpy.vstack((distrodata_min, distrodata_max[1, :]))

    # new recurrence FMD plot (returns figure)
    plot = qpplot.FMDPlotRecurrence()
    cls.figures['recurrence']['fig'] = plot.plot(imgfile=None, 
        data=distrodata)

    cls.fmd_canvas = plots.PlotCanvas(cls.figures['recurrence']['fig'],
        title="Recurrence")
    cls.fmd_canvas.draw()

    # FMD plot window, re-populate layout
    window.layoutPlot.addWidget(cls.fmd_canvas)
    cls.fmd_toolbar = plots.createToolbar(cls.fmd_canvas, window)
    window.layoutPlot.addWidget(cls.fmd_toolbar)
