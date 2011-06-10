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

    # cut catalog to feature
    polylist, vertices = utils.polygonsQGS2Shapely((feature,))
    poly = polylist[0]
    
    # cut catalog with selected polygons
    catalog_selected = QPCatalog.QPCatalog()
    catalog_selected.merge(cls.catalog)
    catalog_selected.cut(geometry=poly)

    return catalog_selected.getFmd(minEventsGR=MIN_EVENTS_FOR_GR)

def plotZoneFMD(cls, fmd, normalize=FMD_COMPUTE_ANNUAL_RATE):

    window = plots.createPlotWindow(cls)

    # new FMD plot 
    figure = fmd.plot(imgfile=None, fmdtype='cumulative', normalize=normalize)

    canvas = plots.PlotCanvas(figure, title="FMD")
    canvas.draw()

    # FMD plot window, re-populate layout
    window.layoutPlot.addWidget(canvas)
    toolbar = plots.createToolbar(canvas, window)
    window.layoutPlot.addWidget(toolbar)
    
    return figure

def getFMDValues(fmd, normalize=FMD_COMPUTE_ANNUAL_RATE):
    """Updates a, b, and Mc value display."""

    if normalize is True:
        aValue = fmd.GR['aValueNormalized']
    else:
        aValue = fmd.GR['aValue']

    return (aValue, fmd.GR['bValue'], fmd.GR['Mmin'])

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
    figure = plot.plot(imgfile=None, data=distrodata)

    canvas = plots.PlotCanvas(figure, title="Recurrence")
    canvas.draw()

    # FMD plot window, re-populate layout
    window.layoutPlot.addWidget(canvas)
    toolbar = plots.createToolbar(canvas, window)
    window.layoutPlot.addWidget(toolbar)
    
    return figure
