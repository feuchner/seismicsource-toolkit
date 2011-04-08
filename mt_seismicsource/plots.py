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

# import QPCatalog

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


class FMDCanvas(MCanvas):
    """Canvas for FMD plot."""

    def __init__(self, fig=None, *args, **kwargs):
        MCanvas.__init__(self, fig, *args, **kwargs)

        if fig is not None:
            self.update_figure(fig)

    def update_figure(self, fig):
        """Update canvas with plot of new FMD object."""

        fp = FontManager.FontProperties()
        self.fig.suptitle('FMD', fontproperties=fp)

        self.draw()
