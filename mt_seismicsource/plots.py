# -*- coding: utf-8 -*-
"""
SHARE Seismic Source Toolkit

This module holds classes for matplotlib plots.

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
import shapely.geometry
import shapely.ops
import sys

from PyQt4.QtCore import *
from PyQt4.QtGui import *

from qgis.core import *

import qpplot

try:
    from matplotlib.backends.backend_qt4agg \
        import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.backends.backend_qt4agg \
        import NavigationToolbar2QTAgg as NavigationToolbar
    from matplotlib.figure import Figure
    import matplotlib.font_manager as FontManager
except ImportError:
    error_msg = "Couldn't import matplotlib"
    QMessageBox.warning(None, "Error", error_msg)

class MCanvas(FigureCanvas):
    """Base class for matplotlib canvases."""
    def __init__(self, fig=None, parent=None, width=5, height=4, dpi=100):

        if fig is None:
            self.fig = Figure(figsize = (width, height), dpi=dpi)
            self.compute_initial_figure()
        else:
            self.fig = fig

        self.ax = self.fig.add_subplot(111)
        self.ax.hold(False)

        FigureCanvas.__init__(self, self.fig)
        self.setParent(parent)

        # Expanding, Minimum, Fixed
        FigureCanvas.setSizePolicy(self,
                                   QSizePolicy.Fixed,
                                   QSizePolicy.Fixed)
        FigureCanvas.updateGeometry(self)

    def compute_initial_figure(self):
        pass

class PlotCanvas(MCanvas):
    """Canvas for 2-d plots."""

    def __init__(self, fig=None, title=None, *args, **kwargs):
        MCanvas.__init__(self, fig, *args, **kwargs)

        if fig is not None:
            self.update_figure(fig, title)

    def update_figure(self, fig, title=None):
        """Update canvas with plot of new FMD object."""

        fp = FontManager.FontProperties()

        if title is not None:
            self.fig.suptitle(title, fontproperties=fp)

        self.draw()

class MomentRateComparisonPlot(qpplot.QPPlot):
    """Plot for comparing several computations of seismic moment rate."""

    def plot( self, imgfile, data, **kwargs ):
        """Plot cumulative occurrence rate vs. magnitude.

        Input:
            data        dict of abscissa values (or lists of abscissa values)
                        key 'eq': from EQs
                        key 'activity': from activity (RM code, AtticIvy)
                        key 'strain': from strain
        """
        if 'backend' in kwargs and kwargs['backend'] != self.backend:
            self.__init__(backend=kwargs['backend'])
    
        self.pyplot.clf()
        
        symbol_style = 'ks' # black solid square
        
        ax = self.figure.add_subplot(111)

        for key_idx, key in enumerate(('eq', 'activity', 'strain')):

            if isinstance(data[key], list):
                ordinate_length = len(data[key])
                abscissa = data[key]
            else:
                ordinate_length = 1
                abscissa = [data[key], ]

            ordinate = [key_idx+1] * ordinate_length
            self.pyplot.plot( abscissa, ordinate, symbol_style )

        # TODO(fab): set x, y axis range
        self.pyplot.ylim(0, key_idx+1)

        # TODO(fab): formatting of y axis labels/caption
        self.pyplot.xlabel( 'Annual Seismic Moment Rate' )
        #self.pyplot.ylabel( '' )

        return self.return_image(imgfile)

def createToolbar(canvas, widget):
    toolbar = NavigationToolbar(canvas, widget)
    lstActions = toolbar.actions()
    toolbar.removeAction(lstActions[7])
    return toolbar