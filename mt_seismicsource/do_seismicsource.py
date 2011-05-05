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
# import shapely.ops
import sys
import time

from PyQt4.QtCore import *
from PyQt4.QtGui import *

from qgis.core import *

import QPCatalog

from algorithms import atticivy
import layers
from layers import areasource
from layers import faultsource
from layers import eqcatalog
import plots
import utils

from ui_seismicsource import Ui_SeismicSource

BACKGROUND_FILE_DIR = 'misc'
BACKGROUND_FILE = 'world.shp'

MIN_EVENTS_FOR_GR = 10

(ZONE_TABLE_ID_IDX, ZONE_TABLE_NAME_IDX, ZONE_TABLE_EQCTR_IDX, 
    ZONE_TABLE_BVALDEF_IDX, ZONE_TABLE_BVAL_IDX, 
    ZONE_TABLE_AVAL_IDX) = range(6)

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

        # Button: load data
        QObject.connect(self.btnLoadData, SIGNAL("clicked()"), 
            self.loadDataLayers)

        # Button: compute zone values
        QObject.connect(self.btnComputeZoneValues, SIGNAL("clicked()"), 
            self.updateZoneValues)

        # Button: FMD plot
        QObject.connect(self.btnDisplayFMD, SIGNAL("clicked()"), 
            self.updateFMD)

        # Checkbox: Normalize FMD plot
        QObject.connect(self.checkBoxGRAnnualRate, 
            SIGNAL("stateChanged(int)"), self._updateFMDDisplay)

        # Button: compute activity (AtticIvy)
        QObject.connect(self.btnAtticIvy, SIGNAL("clicked()"), 
            self.computeAtticIvy)

        # FMD plot window
        self.fmd_canvas = None
        self.fmd_toolbar = None

        # layers
        self.background_layer = None
        self.area_source_layer = None
        self.fault_source_layer = None
        self.catalog_layer = None

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

        self.area_source_layer = areasource.loadAreaSourceLayer(self)
        self.fault_source_layer = faultsource.loadFaultSourceLayer(self)
        self.catalog_layer = eqcatalog.loadEQCatalogLayer(self)

    def updateZoneValues(self):
        """Update a and b values for selected zones."""

        # self._filterEventsFromSelection()
        self._updateZoneTable()

    def updateFMD(self):
        """Update FMD display for one selected zone in zone table."""

        selected_features = self.zoneTable.selectedItems()

        if len(selected_features) == 0:
            QMessageBox.warning(None, "No zone selected", 
                "Please select one zone in the zone table")

        # get feature index of first selected row
        feature_id = selected_features[ZONE_TABLE_ID_IDX].text()
        feature_idx = self.feature_map[feature_id]
        feature = self.area_source_layer.selectedFeatures()[feature_idx]

        self._computeZoneFMD(feature)
        self._updateFMDDisplay()

    def _updateFMDDisplay(self):
        if 'fmd' in self.figures:
            self._displayValues()
            self._plotFMD()

    def _computeFMD(self):
        self.figures['fmd'] = {}
        self.figures['fmd']['fmd'] = self.catalog_selected.getFmd(
            minEventsGR=MIN_EVENTS_FOR_GR)

    def _displayValues(self):
        """Updates a and b value display."""

        if self.checkBoxGRAnnualRate.isChecked():
            aValue = self.figures['fmd']['fmd'].GR['aValueNormalized']
        else:
            aValue = self.figures['fmd']['fmd'].GR['aValue']
        # %.2f
        self.inputAValue.setValue(aValue)
        self.inputBValue.setValue(self.figures['fmd']['fmd'].GR['bValue'])

    def _plotFMD(self):

        # remove widgets from layout
        self.layoutPlotFMD.removeWidget(self.fmd_toolbar)
        self.layoutPlotFMD.removeWidget(self.fmd_canvas)
        del self.fmd_canvas
        del self.fmd_toolbar

        # new FMD plot (returns figure)
        self.figures['fmd']['fig'] = self.figures['fmd']['fmd'].plot(
            imgfile=None, fmdtype='cumulative', 
            normalize=self.checkBoxGRAnnualRate.isChecked())

        self.fmd_canvas = plots.FMDCanvas(self.figures['fmd']['fig'])
        self.fmd_canvas.draw()

        # FMD plot window, re-populate layout
        self.layoutPlotFMD.addWidget(self.fmd_canvas)
        self.fmd_toolbar = self._createFMDToolbar(self.fmd_canvas, 
            self.widgetPlotFMD)
        self.layoutPlotFMD.addWidget(self.fmd_toolbar)

    def _createFMDToolbar(self, canvas, widget):
        toolbar = NavigationToolbar(canvas, widget)
        lstActions = toolbar.actions()
        toolbar.removeAction(lstActions[7])
        return toolbar
        
    def _filterEventsFromSelection(self):
        """Select events from EQ catalog that are within selected polygons
        from area source layer."""

        # get selected polygons from area source layer
        layer_to_select_from = self.area_source_layer
        features_selected = layer_to_select_from.selectedFeatures()

        selected_polygons = []
        for feature in features_selected:

            # yields list of QGSPoints
            qgis_geometry_aspolygon = feature.geometry().asPolygon()
            if len(qgis_geometry_aspolygon) == 0:
                QMessageBox.warning(None, "Error", 
                    "illegal empty polygon, ID: %s" % feature.id())
                continue
            else:
                vertices = [(x.x(), x.y()) for x in qgis_geometry_aspolygon[0]]
                if len(vertices) == 0:
                    QMessageBox.warning(None, "Error", 
                        "illegal empty vertices, ID: %s" % feature.id())
                    continue

            shapely_polygon = shapely.geometry.Polygon(vertices)
            selected_polygons.append(shapely_polygon)

        geometry = shapely.ops.cascaded_union(selected_polygons)

        # cut catalog with selected polygons
        self.catalog_selected = QPCatalog.QPCatalog()
        self.catalog_selected.merge(self.catalog)
        self.catalog_selected.cut(geometry=geometry)

        self.labelSelectedZones.setText(
            "Selected zones: %s" % len(features_selected))
        self.labelSelectedEvents.setText(
            "Selected events: %s" % self.catalog_selected.size())

    def _updateZoneTable(self):
        """Update table of source zones with computed values."""

        # reset table rows to number of zones
        feature_count = len(self.area_source_layer.selectedFeatures())
        self.zoneTable.clearContents()

        if feature_count > 0:
            self.zoneTable.setRowCount(feature_count)

            # get attribute indexes
            attr_idx = {'ssid': None, 'ssshortnam': None, 'ssmfdvalb': None}
            pr = self.area_source_layer.dataProvider()
        
            # if attribute name is not found, -1 is returned
            for curr_attr in attr_idx:
                attr_idx[curr_attr] = pr.fieldNameIndex(curr_attr)

            # create mapping from feature id to index
            self.feature_map = {}

            for feature_idx, feature in enumerate(
                self.area_source_layer.selectedFeatures()):

                fmd = self._computeZoneFMD(feature)

                if attr_idx['ssid'] != -1:
                    feature_id = \
                        feature.attributeMap()[attr_idx['ssid']].toString()
                else:
                    feature_id = feature.id()

                if attr_idx['ssshortnam'] != -1:
                    feature_name = \
                        feature.attributeMap()[attr_idx['ssshortnam']].toString()
                else:
                    feature_name = "-"

                if attr_idx['ssmfdvalb'] != -1:
                    feature_bdef = \
                        feature.attributeMap()[attr_idx['ssmfdvalb']].toString()
                else:
                    feature_bdef = "-"

                self.zoneTable.setItem(feature_idx, ZONE_TABLE_ID_IDX, 
                    QTableWidgetItem(QString("%s" % feature_id)))

                self.zoneTable.setItem(feature_idx, ZONE_TABLE_NAME_IDX, 
                    QTableWidgetItem(QString("%s" % feature_name)))

                self.zoneTable.setItem(feature_idx, ZONE_TABLE_EQCTR_IDX,
                    QTableWidgetItem(QString("%s" % fmd.GR['magCtr'])))

                self.zoneTable.setItem(feature_idx, ZONE_TABLE_BVALDEF_IDX, 
                    QTableWidgetItem(QString("%s" % feature_bdef)))

                self.zoneTable.setItem(feature_idx, ZONE_TABLE_BVAL_IDX,
                    QTableWidgetItem(QString("%.2f" % fmd.GR['bValue'])))

                self.zoneTable.setItem(feature_idx, ZONE_TABLE_AVAL_IDX,
                    QTableWidgetItem(QString("%.2f" % fmd.GR['aValue'])))

                self.feature_map[feature_id] = feature_idx


    def _computeZoneFMD(self, feature):
        """Compute FMD for selected feature."""

        self.figures['fmd'] = {}

        # cut catalog to feature
        qgis_geometry_aspolygon = feature.geometry().asPolygon()
        vertices = [(x.x(), x.y()) for x in qgis_geometry_aspolygon[0]]
        geometry = shapely.geometry.Polygon(vertices)

        # cut catalog with selected polygons
        catalog_selected = QPCatalog.QPCatalog()
        catalog_selected.merge(self.catalog)
        catalog_selected.cut(geometry=geometry)

        self.figures['fmd']['fmd'] = catalog_selected.getFmd(
            minEventsGR=MIN_EVENTS_FOR_GR)
        return self.figures['fmd']['fmd']

    def computeAtticIvy(self):
        """Compute activity with AtticIvy code."""

        self.activityLED.setColor(QColor(255, 0, 0))
        self.activityLEDLabel.setText('Computing...')
        self.btnAtticIvy.setEnabled(False)

        self.area_source_layer.blockSignals(True)
        self.area_source_layer.startEditing()

        pr = self.area_source_layer.dataProvider()
        pr.select()
        atticivy.assignActivityAtticIvy(pr, self.catalog)

        self.area_source_layer.blockSignals(False)
        self.area_source_layer.setModified(True, False)
        self.area_source_layer.commitChanges()
        
        self.activityLED.setColor(QColor(0, 255, 0))
        self.activityLEDLabel.setText('Idle')
        self.btnAtticIvy.setEnabled(True)

        # QCoreApplication.processEvents()


    