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
import qpplot

from algorithms import atticivy
from algorithms import recurrence
import do_plotwindow
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

(AREA_ZONE_TABLE_ID_IDX, AREA_ZONE_TABLE_NAME_IDX, AREA_ZONE_TABLE_EQCTR_IDX, 
    AREA_ZONE_TABLE_BVALDEF_IDX, AREA_ZONE_TABLE_BVAL_IDX, 
    AREA_ZONE_TABLE_AVAL_IDX) = range(6)

(FAULT_ZONE_TABLE_ID_IDX, FAULT_ZONE_TABLE_NAME_IDX, 
    FAULT_ZONE_TABLE_SLIPRATE_IDX, 
    FAULT_ZONE_TABLE_ACTIVITY_IDX, 
    FAULT_ZONE_TABLE_MOMENTRATE_IDX) = range(5)

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

        # Button: display area zone values
        QObject.connect(self.btnComputeAreaZoneValues, SIGNAL("clicked()"), 
            self.updateAreaZoneValues)

        # Button: display fault zone values
        QObject.connect(self.btnComputeFaultZoneValues, SIGNAL("clicked()"), 
            self.updateFaultZoneValues)

        # Button: FMD plot
        QObject.connect(self.btnDisplayFMD, SIGNAL("clicked()"), 
            self.updateFMD)

        # Button: recurrence FMD plot
        QObject.connect(self.btnDisplayRecurrence, SIGNAL("clicked()"), 
            self.updateRecurrence)

        # Checkbox: Normalize FMD plot
        QObject.connect(self.checkBoxGRAnnualRate, 
            SIGNAL("stateChanged(int)"), self._updateFMDDisplay)

        # Button: compute activity (AtticIvy)
        QObject.connect(self.btnAtticIvy, SIGNAL("clicked()"), 
            self.computeAtticIvy)

        # Button: compute recurrence
        QObject.connect(self.btnRecurrence, SIGNAL("clicked()"), 
            self.computeRecurrence)

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

    def updateAreaZoneValues(self):
        """Update a and b values for selected area zones."""

        # self._filterEventsFromSelection()
        self._updateAreaZoneTable()

    def updateFaultZoneValues(self):
        """Update table display for selected fault zones."""

        self._updateFaultZoneTable()

    def updateFMD(self):
        """Update FMD display for one selected area zone in zone table."""

        selected_features = self.zoneAreaTable.selectedItems()

        if len(selected_features) == 0:
            QMessageBox.warning(None, "No zone selected", 
                "Please select one zone in the area zone table")

        # get feature index of first selected row
        feature_id = str(selected_features[AREA_ZONE_TABLE_ID_IDX].text())
        feature_idx = self.area_zone_feature_map[feature_id]
        feature = self.area_source_layer.selectedFeatures()[feature_idx]

        self._computeZoneFMD(feature)
        self._updateFMDDisplay()

    def updateRecurrence(self):
        """Update recurrence FMD display for one selected fault zone
        in zone table."""

        selected_features = self.zoneFaultTable.selectedItems()

        if len(selected_features) == 0:
            QMessageBox.warning(None, "No zone selected", 
                "Please select one zone in the fault zone table")

        # get feature index of first selected row
        feature_id = str(selected_features[FAULT_ZONE_TABLE_ID_IDX].text())
        feature_idx = self.fault_zone_feature_map[feature_id]
        feature = self.fault_source_layer.selectedFeatures()[feature_idx]

        self._updateRecurrenceDisplay(feature)

    def _updateFMDDisplay(self):
        if 'fmd' in self.figures:
            self._displayValues()
            self._plotFMD()

    def _updateRecurrenceDisplay(self, feature):
        self.figures['recurrence'] = {}
        self._plotRecurrence(feature)

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
        self.inputAValue.setValue(aValue)
        self.inputBValue.setValue(self.figures['fmd']['fmd'].GR['bValue'])

    def _plotFMD(self):

        window = self.createPlotWindow()

        # new FMD plot (returns figure)
        self.figures['fmd']['fig'] = self.figures['fmd']['fmd'].plot(
            imgfile=None, fmdtype='cumulative', 
            normalize=self.checkBoxGRAnnualRate.isChecked())

        self.fmd_canvas = plots.FMDCanvas(self.figures['fmd']['fig'])
        self.fmd_canvas.draw()

        # FMD plot window, re-populate layout
        window.layoutPlot.addWidget(self.fmd_canvas)
        self.fmd_toolbar = self._createFMDToolbar(self.fmd_canvas, window)
        window.layoutPlot.addWidget(self.fmd_toolbar)

    def _plotRecurrence(self, feature):

        window = self.createPlotWindow()

        pr = self.fault_source_layer.dataProvider()
        activity_idx = pr.fieldNameIndex('activirate')

        distrostring = str(feature[activity_idx].toString())
        distrodata = utils.distrostring2plotdata(distrostring)

        # new recurrence FMD plot (returns figure)
        plot = qpplot.FMDPlotRecurrence()
        self.figures['recurrence']['fig'] = plot.plot(imgfile=None, 
            data=distrodata)

        self.fmd_canvas = plots.RecurrenceCanvas(
            self.figures['recurrence']['fig'])
        self.fmd_canvas.draw()

        # FMD plot window, re-populate layout
        window.layoutPlot.addWidget(self.fmd_canvas)
        self.fmd_toolbar = self._createFMDToolbar(self.fmd_canvas, window)
        window.layoutPlot.addWidget(self.fmd_toolbar)

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

        self.labelSelectedAreaZones.setText(
            "Selected area zones: %s" % len(features_selected))
        self.labelSelectedEvents.setText(
            "Selected events: %s" % self.catalog_selected.size())

    def _updateAreaZoneTable(self):
        """Update table of area source zones with computed values."""

        # reset table rows to number of zones
        feature_count = len(self.area_source_layer.selectedFeatures())
        self.zoneAreaTable.clearContents()

        if feature_count > 0:
            self.zoneAreaTable.setRowCount(feature_count)

            # get attribute indexes
            attr_idx = {'ssid': None, 'ssshortnam': None, 'ssmfdvalb': None}
            pr = self.area_source_layer.dataProvider()
        
            # if attribute name is not found, -1 is returned
            for curr_attr in attr_idx:
                attr_idx[curr_attr] = pr.fieldNameIndex(curr_attr)

            # create mapping from feature id to index
            self.area_zone_feature_map = {}

            for feature_idx, feature in enumerate(
                self.area_source_layer.selectedFeatures()):

                fmd = self._computeZoneFMD(feature)

                if attr_idx['ssid'] != -1:
                    feature_id = \
                        str(feature.attributeMap()[attr_idx['ssid']].toString())
                else:
                    feature_id = str(feature.id())

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

                self.zoneAreaTable.setItem(feature_idx, 
                    AREA_ZONE_TABLE_ID_IDX,
                    QTableWidgetItem(QString("%s" % feature_id)))

                self.zoneAreaTable.setItem(feature_idx, 
                    AREA_ZONE_TABLE_NAME_IDX, 
                    QTableWidgetItem(QString("%s" % feature_name)))

                self.zoneAreaTable.setItem(feature_idx, 
                    AREA_ZONE_TABLE_EQCTR_IDX,
                    QTableWidgetItem(QString("%s" % fmd.GR['magCtr'])))

                self.zoneAreaTable.setItem(feature_idx, 
                    AREA_ZONE_TABLE_BVALDEF_IDX,
                    QTableWidgetItem(QString("%s" % feature_bdef)))

                self.zoneAreaTable.setItem(feature_idx, 
                    AREA_ZONE_TABLE_BVAL_IDX,
                    QTableWidgetItem(QString("%.2f" % fmd.GR['bValue'])))

                self.zoneAreaTable.setItem(feature_idx, 
                    AREA_ZONE_TABLE_AVAL_IDX,
                    QTableWidgetItem(QString("%.2f" % fmd.GR['aValue'])))

                self.area_zone_feature_map[feature_id] = feature_idx


    def _updateFaultZoneTable(self):
        """Update table of fault zones."""

        # reset table rows to number of zones
        feature_count = len(self.fault_source_layer.selectedFeatures())
        self.zoneFaultTable.clearContents()

        if feature_count > 0:
            self.zoneFaultTable.setRowCount(feature_count)

            # get attribute indexes
            attr_idx = {'IDSOURCE': None, 'SLIPRATEMA': None, 
                'activirate': None, 'momentrate': None}
            pr = self.fault_source_layer.dataProvider()
        
            # if attribute name is not found, -1 is returned
            for curr_attr in attr_idx:
                attr_idx[curr_attr] = pr.fieldNameIndex(curr_attr)

            # create mapping from feature id to index
            self.fault_zone_feature_map = {}

            for feature_idx, feature in enumerate(
                self.fault_source_layer.selectedFeatures()):

                feature_id = str(feature.id())

                if attr_idx['IDSOURCE'] != -1:
                    feature_idsource = \
                feature.attributeMap()[attr_idx['IDSOURCE']].toString()
                else:
                    feature_idsource = "-"

                if attr_idx['SLIPRATEMA'] != -1:
                    feature_slipratema = \
                feature.attributeMap()[attr_idx['SLIPRATEMA']].toString()
                else:
                    feature_slipratema = "-"

                if attr_idx['activirate'] != -1:
                    feature_activirate = \
                feature.attributeMap()[attr_idx['activirate']].toString()
                else:
                    feature_activirate = "-"

                if attr_idx['momentrate'] != -1:
                    feature_momentrate = \
                feature.attributeMap()[attr_idx['momentrate']].toString()
                else:
                    feature_momentrate = "-"

                self.zoneFaultTable.setItem(feature_idx, 
                    FAULT_ZONE_TABLE_ID_IDX,
                    QTableWidgetItem(QString("%s" % feature_id)))

                self.zoneFaultTable.setItem(feature_idx, 
                    FAULT_ZONE_TABLE_NAME_IDX, 
                    QTableWidgetItem(QString("%s" % feature_idsource)))

                self.zoneFaultTable.setItem(feature_idx, 
                    FAULT_ZONE_TABLE_SLIPRATE_IDX,
                    QTableWidgetItem(QString("%s" % feature_slipratema)))

                self.zoneFaultTable.setItem(feature_idx, 
                    FAULT_ZONE_TABLE_ACTIVITY_IDX, 
                    QTableWidgetItem(QString("%s" % feature_activirate)))

                self.zoneFaultTable.setItem(feature_idx, 
                    FAULT_ZONE_TABLE_MOMENTRATE_IDX,
                    QTableWidgetItem(QString("%s" % feature_momentrate)))

                self.fault_zone_feature_map[feature_id] = feature_idx

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

        pr = self.area_source_layer.dataProvider()
        pr.select()
        atticivy_result = atticivy.assignActivityAtticIvy(pr, self.catalog)

        self.activityLED.setColor(QColor(0, 255, 0))
        self.activityLEDLabel.setText('Idle')
        self.btnAtticIvy.setEnabled(True)

    def computeRecurrence(self):
        """Compute recurrence with Bungum code."""

        self.recurrenceLED.setColor(QColor(255, 0, 0))
        self.recurrenceLEDLabel.setText('Computing...')
        self.btnRecurrence.setEnabled(False)

        pr = self.fault_source_layer.dataProvider()
        pr.select()
        recurrence_result = recurrence.assignRecurrence(pr)

        self.labelTotalMoment.setText(
            "Total moment release rate: %.2e" % recurrence_result)
        self.recurrenceLED.setColor(QColor(0, 255, 0))
        self.recurrenceLEDLabel.setText('Idle')
        self.btnRecurrence.setEnabled(True)

    def createPlotWindow(self):
        """Create new plot window dialog."""
 
        plot_window = do_plotwindow.PlotWindow(self.iface)
        plot_window.setModal(False)
        plot_window.show()
        plot_window.raise_()
        self.plot_windows.append(plot_window)
        return plot_window