# -*- coding: utf-8 -*-
"""
SHARE Seismic Source Toolkit

This is the main dialog of the toolkit.

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
import time

from PyQt4.QtCore import *
from PyQt4.QtGui import *

from qgis.core import *

import QPCatalog
import qpplot

from algorithms import atticivy
from algorithms import recurrence
from algorithms import strain

from engine import fmd
from engine import momentbalancing

import layers
from layers import areasource
from layers import background
from layers import eqcatalog
from layers import faultsource
from layers import render

import plots
import utils

from ui_seismicsource import Ui_SeismicSource

BACKGROUND_FILE_DIR = 'misc'
BACKGROUND_FILE = 'world.shp'

(MOMENT_TABLE_EQ_IDX, MOMENT_TABLE_SEISMICITY_IDX,
    MOMENT_TABLE_STRAIN_IDX) = range(3)

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

class SeismicSource(QDialog, Ui_SeismicSource):
    """This class represents the main dialog widget of the plugin."""
    def __init__(self, iface):
        QDialog.__init__(self)
        self.iface = iface
        self.setupUi(self)

        self.figures = {}
        self.plot_windows = []

        # Button: load data
        QObject.connect(self.btnLoadData, SIGNAL("clicked()"), 
            self.loadDataLayers)

        # Button: compute moment rate of area zones
        QObject.connect(self.btnComputeMomentRateArea, SIGNAL("clicked()"), 
            self.updateMomentRateValuesArea)

        # Button: compute moment rate of fault zones
        QObject.connect(self.btnComputeMomentRateFault, SIGNAL("clicked()"), 
            self.updateMomentRateValuesFault)

        # Button: FMD plot
        QObject.connect(self.btnDisplayFMD, SIGNAL("clicked()"), 
            self.updateFMD)

        # Button: recurrence FMD plot
        QObject.connect(self.btnDisplayRecurrence, SIGNAL("clicked()"), 
            self.updateRecurrence)

        # Checkbox: Normalize FMD plot
        # TODO(fab): disabled, since results are not correct
        #QObject.connect(self.checkBoxGRAnnualRate, 
            #SIGNAL("stateChanged(int)"), self._updateFMDDisplay)

        # Button: compute activity (AtticIvy)
        QObject.connect(self.btnComputeAtticIvy, SIGNAL("clicked()"), 
            self.computeAtticIvy)

        # Button: compute recurrence
        QObject.connect(self.btnComputeRecurrence, SIGNAL("clicked()"), 
            self.computeRecurrence)

        # FMD plot window
        self.fmd_canvas = None
        self.fmd_toolbar = None

        # Moment rate per area zone comparison plot window
        self.fig_moment_rate_comparison_area = None
        self.canvas_moment_rate_comparison_area = None
        self.toolbar_moment_rate_comparison_area = None

        # Moment rate per fault zone comparison plot window
        self.fig_moment_rate_comparison_fault = None
        self.canvas_moment_rate_comparison_fault = None
        self.toolbar_moment_rate_comparison_fault = None

        # layers
        self.background_layer = None
        self.background_zone_layer = None
        self.area_source_layer = None
        self.fault_source_layer = None
        self.catalog_layer = None
        
        # additional datasets
        self.data_strain_rate = None

        # prepare data load combo boxes
        self.comboBoxZoneInput.addItems(areasource.ZONE_FILES)
        self.comboBoxFaultInput.addItems(faultsource.FAULT_FILES)
        self.comboBoxEQCatalogInput.addItems(eqcatalog.CATALOG_FILES)

        self.progressBarLoadData.setValue(0)

        self.labelCatalogEvents.setText("Catalog events: 0")
        self.labelSelectedZones.setText("Selected zones: 0")
        self.labelSelectedEvents.setText("Selected events: 0")

    def loadDataLayers(self):

        # remove default layers
        # QgsMapLayerRegistry.instance().removeMapLayer(layer_id)

        # "busy" progress bar
        self.progressBarLoadData.setRange(0, 0)

        self.loadBackgroundLayer()
        self.loadDefaultLayers()

        self.loadAdditionalData()

        self.renderers = render.setRenderers(self.area_source_layer,
            self.fault_source_layer,
            self.catalog_layer,
            self.background_zone_layer,
            self.background_layer)
        self.iface.mapCanvas().refresh()

        self.progressBarLoadData.setRange(0, 100)
        self.progressBarLoadData.setValue(100)

        # TODO(fab): make zone layer the active layer

    def loadBackgroundLayer(self):
        if self.background_layer is None:
            background_path = os.path.join(layers.DATA_DIR,
                BACKGROUND_FILE_DIR, BACKGROUND_FILE)

            if not os.path.isfile(background_path):
                utils.warning_box_missing_layer_file(background_path)
                return

            self.background_layer = QgsVectorLayer(background_path, 
                "Political Boundaries", "ogr")
            QgsMapLayerRegistry.instance().addMapLayer(self.background_layer)

    def loadDefaultLayers(self):

        self.background_zone_layer = background.loadBackgroundZoneLayer(self)
        self.area_source_layer = areasource.loadAreaSourceLayer(self)
        self.fault_source_layer = faultsource.loadFaultSourceLayer(self)
        self.catalog_layer = eqcatalog.loadEQCatalogLayer(self)

    def loadAdditionalData(self):
        self.data_strain_rate = strain.loadStrainRateData()

    def updateMomentRateValuesArea(self):
        """Update values in moment rate per area table/plot, if other 
        area zone has  been selected, or zone attributes have been changed."""

        if not utils.check_only_one_feature_selected(self.area_source_layer):
            return

        # TODO(fab): check if attribute values have been changed
        # so far, we always recompute
        self.computeAtticIvy()
        self.area_source_layer.commitChanges()

        selected_feature = self.area_source_layer.selectedFeatures()[0]

        moment_rates = momentbalancing.updateMomentRatesArea(self, 
            selected_feature)
        momentbalancing.updateMomentRateTableArea(self, moment_rates)
        momentbalancing.updateMomentRatePlotArea(self, moment_rates)

    def updateMomentRateValuesFault(self):
        """Update values in moment rate per fault table/plot, if other 
        area zone has been selected, or zone attributes have been changed."""

        if not utils.check_only_one_feature_selected(self.fault_source_layer):
            return

        # TODO(fab): check if attribute values have been changed
        # so far, we always recompute
        self.computeRecurrence()
        self.fault_source_layer.commitChanges()

        selected_feature = self.fault_source_layer.selectedFeatures()[0]

        moment_rates = momentbalancing.updateMomentRatesFault(self, 
            selected_feature)
        momentbalancing.updateMomentRateTableFault(self, moment_rates)
        momentbalancing.updateMomentRatePlotFault(self, moment_rates)

    def updateFMD(self):
        """Update FMD display for one selected area zone from
        area zone layer."""

        if not utils.check_only_one_feature_selected(self.area_source_layer):
            return

        selected_feature = self.area_source_layer.selectedFeatures()[0]
        fmd.computeZoneFMD(self, selected_feature)
        fmd.updateFMDDisplay(self)

    def updateRecurrence(self):
        """Update recurrence FMD display for one selected fault zone
        in fault zone layer."""

        if not utils.check_only_one_feature_selected(self.fault_source_layer):
            return

        selected_feature = self.fault_source_layer.selectedFeatures()[0]
        fmd.updateRecurrenceDisplay(self, selected_feature)

    def computeAtticIvy(self):
        """Compute activity with AtticIvy code."""

        if not utils.check_at_least_one_feature_selected(
            self.area_source_layer):
            return

        self.activityLED.setColor(QColor(255, 0, 0))
        self.activityLEDLabel.setText('Computing...')
        self.btnComputeAtticIvy.setEnabled(False)

        atticivy_result = atticivy.assignActivityAtticIvy(
            self.area_source_layer, self.catalog)

        self.activityLED.setColor(QColor(0, 255, 0))
        self.activityLEDLabel.setText('Idle')
        self.btnComputeAtticIvy.setEnabled(True)

    def computeRecurrence(self):
        """Compute recurrence with Bungum code."""

        if not utils.check_at_least_one_feature_selected(
            self.fault_source_layer):
            return

        self.recurrenceLED.setColor(QColor(255, 0, 0))
        self.recurrenceLEDLabel.setText('Computing...')
        self.btnComputeRecurrence.setEnabled(False)

        recurrence_result = recurrence.assignRecurrence(
            self.fault_source_layer, self.area_source_layer, self.catalog)

        self.recurrenceLED.setColor(QColor(0, 255, 0))
        self.recurrenceLEDLabel.setText('Idle')
        self.btnComputeRecurrence.setEnabled(True)
