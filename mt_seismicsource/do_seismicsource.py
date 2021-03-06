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
import qpfmd
import qpplot

from mt_seismicsource import attributes
from mt_seismicsource import data
from mt_seismicsource import display
from mt_seismicsource import engine
from mt_seismicsource import features

from mt_seismicsource import layers
from mt_seismicsource import plots
from mt_seismicsource import utils

from mt_seismicsource.algorithms import recurrence

from mt_seismicsource.engine import asz
from mt_seismicsource.engine import fbz
from mt_seismicsource.engine import fmd
from mt_seismicsource.engine import fsz

from mt_seismicsource.layers import areasource
from mt_seismicsource.layers import background
from mt_seismicsource.layers import eqcatalog
from mt_seismicsource.layers import faultsource
from mt_seismicsource.layers import faultbackground
from mt_seismicsource.layers import mapdata
from mt_seismicsource.layers import render
from mt_seismicsource.layers import tectonic

from ui_seismicsource import Ui_SeismicSource

class SeismicSource(QDialog, Ui_SeismicSource):
    """This class represents the main dialog widget of the plugin."""
    def __init__(self, iface):
        QDialog.__init__(self)
        self.iface = iface
        self.setupUi(self)

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

        # Button: compute parameters for area source zones
        QObject.connect(self.btnDataAreaCompute, SIGNAL("clicked()"), 
            self.computeASZ)

        # Button: show parameters for area source zones
        QObject.connect(self.btnDataAreaShow, SIGNAL("clicked()"), 
            self.showASZ)
            
        # Button: FMD plot for area source zones
        QObject.connect(self.btnDataAreaDisplayFMD, SIGNAL("clicked()"), 
            self.displayDataAreaFMD)
            
        # Button: Moment rate plot for area source zones
        QObject.connect(self.btnDataAreaDisplayMR, SIGNAL("clicked()"), 
            self.displayDataAreaMomentRates)
        
        # Button: compute parameters for fault background zones
        QObject.connect(self.btnDataFaultBackgrCompute, 
            SIGNAL("clicked()"), self.computeFBZ)
            
        # Button: show parameters for fault background zones
        QObject.connect(self.btnDataFaultBackgrShow, 
            SIGNAL("clicked()"), self.showFBZ)
            
        # Button: FMD plot for fault background zones
        QObject.connect(self.btnDataFaultBackgrDisplayFMD, 
            SIGNAL("clicked()"), self.displayDataFaultBackgrFMD)
        
        # Button: Moment rate plot for background zones
        QObject.connect(self.btnDataFaultBackgrDisplayMR, SIGNAL("clicked()"),
            self.displayDataFaultBackgrMomentRates)
            
        # Button: compute parameters for fault zones
        QObject.connect(self.btnDataFaultCompute, SIGNAL("clicked()"), 
            self.computeFSZ)

        # Button: show parameters for fault zones
        QObject.connect(self.btnDataFaultShow, SIGNAL("clicked()"), 
            self.showFSZ)
            
        # Button: recurrence FMD plot for fault zones
        QObject.connect(self.btnDataFaultDisplayRecurrence, 
            SIGNAL("clicked()"), self.displayRecurrence)

        # Button: Moment rate plot for fault source zones
        QObject.connect(self.btnDataFaultDisplayMR, SIGNAL("clicked()"), 
            self.displayDataFaultMomentRates)

        # list of all created plot window objects
        self.plot_windows = []
        
        # saved data from selected zones
        self.feature_data_area_source = {}
        self.feature_data_fault_source = {}
        self.feature_data_fault_background = {}

        # Non-layer datasets
        self.catalog = None
        self.catalog_time_span = None
        self.data = None
        
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
        
        ## Catalog filtering
        
        # self.checkBoxCatalogDepth
        self.spinboxCatDepthMin.setValue(eqcatalog.CUT_DEPTH_MIN)
        self.spinboxCatDepthMax.setValue(eqcatalog.CUT_DEPTH_MAX)
        
        ## FMD
       
        self.comboBoxMcMethod.addItems(fmd.MC_METHODS)
        self.spinboxFMDMcMethod.setValue(fmd.MC_DEFAULT)

        ## Fault Background Zone
        
        # spinbox threshold magnitude: init value
        self.spinboxFBZMThres.setValue(
            recurrence.FAULT_BACKGROUND_MAG_THRESHOLD)
        
        ## Fault Zone
        
        # combobox: Recurrence model
        self.comboBoxRecurrenceModel.addItems(
            recurrence.RECURRENCE_MODEL_NAMES)
            
        self.progressBarLoadData.setValue(0)

    def loadDataLayers(self):

        # get legend
        self.legend = self.iface.legendInterface()
        
        self.progressBarLoadData.setRange(0, 100)

        # additional datasets
        self.data = data.Datasets()
        
        self.progressBarLoadData.setValue(10)
        
        # load map layers
        mapdata.loadBackgroundLayer(self)
        
        self.progressBarLoadData.setValue(20)
        
        self.loadDefaultLayers()

        # display catalog properties
        cat_prop_txt = "Time Span: %s yr (%s-%s)" % (
            int(self.catalog_time_span[0]), self.catalog_time_span[1].year,
            self.catalog_time_span[2].year)
        self.labelCatTimeSpan.setText(cat_prop_txt)
        
        self.renderers = render.setRenderers(
            self.area_source_layer,
            self.fault_source_layer,
            self.fault_background_layer,
            self.catalog_layer,
            self.background_zone_layer,
            self.background_layer,
            self.tectonic_layer)
            
        # set map extent
        self.iface.mapCanvas().setExtent(QgsRectangle(render.EXTENT_LON_MIN, 
            render.EXTENT_LAT_MIN, render.EXTENT_LON_MAX, 
            render.EXTENT_LAT_MAX))
        self.iface.mapCanvas().refresh()
        self.progressBarLoadData.setValue(100)

        # TODO(fab): make area source layer the active layer

    def loadDefaultLayers(self):

        self.background_zone_layer = background.loadBackgroundZoneLayer(self)
        self.progressBarLoadData.setValue(30)
        self.area_source_layer = areasource.loadAreaSourceLayer(self)
        self.progressBarLoadData.setValue(40)
        self.fault_source_layer = faultsource.loadFaultSourceLayer(self)
        self.progressBarLoadData.setValue(50)
        self.fault_background_layer = \
            faultbackground.loadFaultBackgroundLayer(self)
        self.progressBarLoadData.setValue(60)
        self.catalog_layer = eqcatalog.loadEQCatalogLayer(self)
        self.progressBarLoadData.setValue(70)
        self.tectonic_layer = tectonic.loadTectonicRegimeLayer(self)
        self.progressBarLoadData.setValue(80)

    def showASZ(self):
        """Show parameter values from ASZ layer in panel."""
        
         # update zone ID display
        selected_feature = self.area_source_layer.selectedFeatures()[0]
        
        #self.feature_data_area_source['parameters'] = \
            #attributes.getAttributesFromASZ(self, selected_feature)
            
        # ---------------------------------------------------------------------

        self.feature_data_area_source['parameters'] = asz.updateDataArea(
            self, selected_feature)
        
        display.updateDisplaysArea(self, 
            self.feature_data_area_source['parameters'], selected_feature)
    
    def computeASZ(self):
        """Compute attributes for selected feature in ASZ layer. Only one
        feature can be selected."""

        if not utils.check_only_one_feature_selected(self.area_source_layer):
            return

        (mindepth, maxdepth) = eqcatalog.getMinMaxDepth(self)
        
        engine.computeASZ(self.area_source_layer, self.catalog, mindepth, 
            maxdepth, ui_mode=True)
            
        self.showASZ()
            
    def showFSZ(self):
        """Show parameter values from FSZ layer in panel."""
        
        # update zone ID display
        selected_feature = self.fault_source_layer.selectedFeatures()[0]
        
        self.feature_data_fault_source['parameters'] = fsz.updateDataFault(
            self, selected_feature, m_threshold=self.spinboxFBZMThres.value())
        
        display.updateDisplaysFault(self, 
            self.feature_data_fault_source['parameters'], selected_feature)
    
    def computeFSZ(self):
        """Compute attributes for selected feature in FSZ layer. Only one
        feature can be selected."""

        if not utils.check_only_one_feature_selected(self.fault_source_layer):
            return

        (mindepth, maxdepth) = eqcatalog.getMinMaxDepth(self)
        
        engine.computeFSZ(self.fault_source_layer, 
            self.fault_background_layer, self.background_zone_layer, 
            self.catalog, self.catalog_time_span[0],
            m_threshold=self.spinboxFBZMThres.value(), mindepth=mindepth,
            maxdepth=maxdepth, ui_mode=True)
            
        self.showFSZ()

    def showFBZ(self):
        """Show parameter values from FBZ layer in panel."""
        
        # update zone ID display
        selected_feature = \
            self.fault_background_layer.selectedFeatures()[0]

        self.feature_data_fault_background['parameters'] = \
            fbz.updateDataFaultBackgr(self, selected_feature, 
            m_threshold=self.spinboxFBZMThres.value())
            
        display.updateDisplaysFaultBackgr(self, 
            self.feature_data_fault_background['parameters'], 
            selected_feature)
    
    def computeFBZ(self):
        """Compute attributes for selected feature in FBZ layer. Only one
        feature can be selected."""

        if not utils.check_only_one_feature_selected(
            self.fault_background_layer):
            return

        (mindepth, maxdepth) = eqcatalog.getMinMaxDepth(self)
        
        engine.computeFBZ(self.fault_background_layer, self.catalog, mindepth,
            maxdepth, ui_mode=True)
            
        self.showFBZ()

    def displayDataAreaFMD(self):
        """Update FMD display for one selected area zone from
        area zone layer."""

        if 'fmd' in self.feature_data_area_source:
            self.feature_data_area_source['fmd_fig'] = fmd.plotZoneFMD(self, 
                self.feature_data_area_source)

    def displayDataAreaMomentRates(self):
        """Update moment rate display for one selected area zone from
        area zone layer."""

        if 'parameters' in self.feature_data_area_source:
            self.feature_data_area_source['mr_fig'] = \
                display.updatePlotMomentRateArea(self,
                    self.feature_data_area_source['parameters'])
        
    def displayDataFaultBackgrFMD(self):
        pass
    
    def displayDataFaultBackgrMomentRates(self):
        pass
    
    def displayRecurrence(self):
        """Update recurrence FMD display for one selected fault zone
        in fault zone layer."""

        if not utils.check_only_one_feature_selected(self.fault_source_layer):
            return

        selected_feature = self.fault_source_layer.selectedFeatures()[0]
        
        self.feature_data_fault_source['recurrence_fig'] = fmd.plotRecurrence(
            self, selected_feature, 
            self.feature_data_fault_source)

    def displayDataFaultMomentRates(self):
        if 'parameters' in self.feature_data_fault_source:
            self.feature_data_fault_source['mr_fig'] = \
                display.updatePlotMomentRateFault(self,
                    self.feature_data_fault_source['parameters'])

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
