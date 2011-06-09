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
import sys
import time

from PyQt4.QtCore import *
from PyQt4.QtGui import *

from qgis.core import *

import QPCatalog
import qpplot

from algorithms import atticivy
from algorithms import recurrence

import data

from engine import fmd
from engine import momentbalancing

import layers
from layers import areasource
from layers import background
from layers import eqcatalog
from layers import faultsource
from layers import faultbackground
from layers import mapdata
from layers import render
from layers import tectonic

import plots
import utils

from ui_seismicsource import Ui_SeismicSource

class SeismicSource(QDialog, Ui_SeismicSource):
    """This class represents the main dialog widget of the plugin."""
    def __init__(self, iface):
        QDialog.__init__(self)
        self.iface = iface
        self.setupUi(self)

        self.figures = {}
        self.plot_windows = []

        ## Input data controls
        
        # Button: browse Area Source Zone files
        QObject.connect(self.btnBrowseZone, SIGNAL("clicked()"), 
            self.browseAreaZoneFiles)
            
        # Button: browse Fault Source Zone files
        QObject.connect(self.btnBrowseFault, SIGNAL("clicked()"), 
            self.browseFaultZoneFiles)
            
        # Button: browse Fault Background Zone files
        QObject.connect(self.btnBrowseFaultBackgr, SIGNAL("clicked()"), 
            self.browseFaultBackgrZoneFiles)
            
        # Button: browse EQ catalog files
        QObject.connect(self.btnBrowseEQCatalog, SIGNAL("clicked()"), 
            self.browseEQCatalogFiles)
            
        # Button: load data
        QObject.connect(self.btnLoadData, SIGNAL("clicked()"), 
            self.loadDataLayers)

        # Button: compute parameters for area zones
        QObject.connect(self.btnComputeDataArea, SIGNAL("clicked()"), 
            self.updateDataArea)

        # Button: compute parameters for fault zones
        QObject.connect(self.btnComputeDataFault, SIGNAL("clicked()"), 
            self.updateDataFault)

        # Button: compute parameters for fault background zones
        QObject.connect(self.btnComputeDataFaultBackgr, 
            SIGNAL("clicked()"), self.updateDataFaultBackgr)
            
        # Button: FMD plot
        QObject.connect(self.btnDisplayFMD, SIGNAL("clicked()"), 
            self.updateFMD)

        # Button: recurrence FMD plot
        QObject.connect(self.btnDisplayRecurrence, SIGNAL("clicked()"), 
            self.updateRecurrence)
        
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
        self.fault_background_layer = None
        self.catalog_layer = None
        self.tectonic_layer = None

        # prepare data load combo boxes
        self.comboBoxAreaZoneInput.addItems(areasource.ZONE_FILES)
        self.comboBoxFaultZoneInput.addItems(faultsource.FAULT_FILES)
        self.comboBoxFaultBackgrZoneInput.addItems(
            faultbackground.FAULT_BACKGROUND_FILES)
        self.comboBoxEQCatalogInput.addItems(eqcatalog.CATALOG_FILES)
        
        # Spinbox AtticIvy: init value
        self.spinboxAtticIvyMmin.setValue(atticivy.ATTICIVY_MMIN)
        
        self.progressBarLoadData.setValue(0)

    def loadDataLayers(self):

        # remove default layers
        # QgsMapLayerRegistry.instance().removeMapLayer(layer_id)

        self.progressBarLoadData.setRange(0, 100)

        # additional datasets
        self.data = data.Datasets()
        
        self.progressBarLoadData.setValue(10)
        
        # load map layers
        mapdata.loadBackgroundLayer(self)
        
        self.progressBarLoadData.setValue(20)
        
        self.loadDefaultLayers()

        self.renderers = render.setRenderers(
            self.area_source_layer,
            self.fault_source_layer,
            self.fault_background_layer,
            self.catalog_layer,
            self.background_zone_layer,
            self.background_layer,
            self.tectonic_layer)
        self.iface.mapCanvas().refresh()

        self.progressBarLoadData.setValue(100)

        # TODO(fab): make zone layer the active layer

    def loadDefaultLayers(self):

        self.background_zone_layer = background.loadBackgroundZoneLayer(self)
        
        self.progressBarLoadData.setValue(30)
        
        self.area_source_layer = areasource.loadAreaSourceLayer(self)
        
        self.progressBarLoadData.setValue(40)
        
        self.fault_source_layer = faultsource.loadFaultSourceLayer(self)
        
        self.progressBarLoadData.setValue(50)
        
        self.fault_background_layer = faultbackground.loadFaultBackgroundLayer(self)
        
        self.progressBarLoadData.setValue(60)
        
        self.catalog_layer = eqcatalog.loadEQCatalogLayer(self)
        
        self.progressBarLoadData.setValue(70)
        
        self.tectonic_layer = tectonic.loadTectonicRegimeLayer(self)
        
        self.progressBarLoadData.setValue(80)

    def updateDataArea(self):
        """Update values in moment rate per area table, if other 
        area zone has  been selected, or zone attributes have been changed."""

        if not utils.check_only_one_feature_selected(self.area_source_layer):
            return

        # TODO(fab): check if attribute values have been changed
        # so far, we always recompute
        self.computeAtticIvy()
        
        self.area_source_layer.commitChanges()

        selected_feature = self.area_source_layer.selectedFeatures()[0]

        parameters = momentbalancing.updateDataArea(self, selected_feature)
        momentbalancing.updateDisplaysArea(self, parameters)

    def updateDataFault(self):
        """Update values in moment rate per fault table."""

        if not utils.check_only_one_feature_selected(self.fault_source_layer):
            return

        # TODO(fab): check if attribute values have been changed
        # so far, we always recompute
        self.computeRecurrence()
        self.fault_source_layer.commitChanges()

        selected_feature = self.fault_source_layer.selectedFeatures()[0]

        parameters = momentbalancing.updateDataFault(self, selected_feature)
        momentbalancing.updateDisplaysFault(self, parameters)

    def updateDataFaultBackgr(self):
        """Update values in moment rate per fault background zone table."""

        if not utils.check_only_one_feature_selected(
            self.fault_background_layer):
            return

        selected_feature = \
            self.fault_background_layer.selectedFeatures()[0]

        parameters = momentbalancing.updateDataFaultBackgr(self, 
            selected_feature, m_threshold=self.spinboxFBZMThres.value())
        momentbalancing.updateDisplaysFaultBackgr(self, parameters)

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

        atticivy_result = atticivy.assignActivityAtticIvy(
            self.area_source_layer, self.catalog, 
            mmin=self.spinboxAtticIvyMmin.value())

    def computeRecurrence(self):
        """Compute recurrence with Bungum code."""

        if not utils.check_at_least_one_feature_selected(
            self.fault_source_layer):
            return

        recurrence_result = recurrence.assignRecurrence(
            self.fault_source_layer, self.area_source_layer, self.catalog)

    def browseAreaZoneFiles(self):
        """Show Open File dialog for Area Source Zone files."""
        
        title = "Open Area Source Zone file"
        directory = os.path.join(layers.DATA_DIR, areasource.ZONE_FILE_DIR)
        file_filter = layers.SHAPEFILE_FILTER
        combobox = self.comboBoxAreaZoneInput
        self.selectInputFile(combobox, title, directory, file_filter)
    
    def browseFaultZoneFiles(self):
        """Show Open File dialog for Fault Source files."""
        
        title = "Open Fault Source file"
        directory = os.path.join(layers.DATA_DIR, faultsource.FAULT_FILE_DIR)
        file_filter = layers.SHAPEFILE_FILTER
        combobox = self.comboBoxFaultZoneInput
        self.selectInputFile(combobox, title, directory, file_filter)
    
    def browseFaultBackgrZoneFiles(self):
        """Show Open File dialog for Fault Background Zone files."""
        
        title = "Open Fault Background Zone file"
        directory = os.path.join(layers.DATA_DIR, 
            faultbackground.FAULT_BACKGROUND_FILE_DIR)
        file_filter = layers.SHAPEFILE_FILTER
        combobox = self.comboBoxFaultBackgrZoneInput
        self.selectInputFile(combobox, title, directory, file_filter)
    
    def browseEQCatalogFiles(self):
        """Show Open File dialog for EQ catalog files."""
        
        title = "Open EQ catalog file"
        directory = os.path.join(layers.DATA_DIR, eqcatalog.CATALOG_DIR)
        file_filter = layers.EQ_CATALOG_FILTER
        combobox = self.comboBoxEQCatalogInput
        self.selectInputFile(combobox, title, directory, file_filter)
        
    def selectInputFile(self, widget, title='', directory=layers.DATA_DIR, 
        file_filter=""):
        """Open File dialog for unspecified input file type and add selected
        file name to specified widget (combobox)."""
        
        path = QFileDialog.getOpenFileName(self, title, directory, 
            file_filter)
        widget.insertItem(0, os.path.basename(str(path)))
        widget.setCurrentIndex(0)
