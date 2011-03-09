# -*- coding: utf-8 -*-
"""
SHARE Seismic Source Toolkit

This is a toolkit for editing seismic source zones used in the
SHARE project.
It is realized as a Python plugin for Quantum GIS.

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

import os
import sys
import time

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *

import do_seismicsource

PLUGIN_TITLE = 'SHARE Seismic Source Toolkit'

class SeismicSourceToolkit(object):
    """Main class of the Seismic Source Toolkit plugin"""
    def __init__(self, iface):
        self.iface = iface
        self.mainWindow = self.iface.mainWindow
        self.seismicSourceDialog = None

    def initGui(self):
        self.seismicSource = QAction(PLUGIN_TITLE, self.mainWindow())
        QObject.connect(self.seismicSource, SIGNAL("triggered()"), 
            self.doSeismicSource)
        self.iface.addPluginToMenu(PLUGIN_TITLE, self.seismicSource)

    def unload(self):
        self.iface.removePluginMenu(PLUGIN_TITLE, self.seismicSource)

    def doSeismicSource(self):
        self.seismicSourceDialog = do_seismicsource.SeismicSource(self.iface)
        self.seismicSourceDialog.setModal(False)
        self.seismicSourceDialog.show()
        self.seismicSourceDialog.raise_()
