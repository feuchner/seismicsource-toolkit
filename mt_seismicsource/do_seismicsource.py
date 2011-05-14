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
#from algorithms import momentrate
from algorithms import recurrence
import do_plotwindow
import layers
from layers import areasource
from layers import background
from layers import faultsource
from layers import eqcatalog
import plots
import utils

from ui_seismicsource import Ui_SeismicSource

BACKGROUND_FILE_DIR = 'misc'
BACKGROUND_FILE = 'world.shp'

MIN_EVENTS_FOR_GR = 10

(MOMENT_TABLE_EQ_IDX, MOMENT_TABLE_SEISMICITY_IDX,
    MOMENT_TABLE_STRAIN_IDX) = range(3)

(FAULT_ZONE_TABLE_ID_IDX, FAULT_ZONE_TABLE_NAME_IDX, 
    FAULT_ZONE_TABLE_ACTIVITY_MIN_IDX, 
    FAULT_ZONE_TABLE_ACTIVITY_MAX_IDX, 
    FAULT_ZONE_TABLE_MOMENTRATE_MIN_IDX,
    FAULT_ZONE_TABLE_MOMENTRATE_MAX_IDX) = range(6)

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

        # Button: compute moment rate
        QObject.connect(self.btnComputeMomentRate, SIGNAL("clicked()"), 
            self.updateMomentRateValues)

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

        self.background_zone_layer = None
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

        self.background_zone_layer = background.loadBackgroundZoneLayer(self)
        self.area_source_layer = areasource.loadAreaSourceLayer(self)
        self.fault_source_layer = faultsource.loadFaultSourceLayer(self)
        self.catalog_layer = eqcatalog.loadEQCatalogLayer(self)

    def updateMomentRateValues(self):
        """Update values in moment rate table/plot, if other area zone has
        been selected, or zone attributes have been changed."""
        pass

    def updateFaultZoneValues(self):
        """Update table display for selected fault zones."""

        self._updateFaultZoneTable()

    def updateFMD(self):
        """Update FMD display for one selected area zone in zone table."""

        # selected_features = self.zoneAreaTable.selectedItems()

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
        activity_min_idx = pr.fieldNameIndex('actrate_mi')
        activity_max_idx = pr.fieldNameIndex('actrate_ma')

        distrostring_min = str(feature[activity_min_idx].toString())
        distrostring_max = str(feature[activity_max_idx].toString())
        distrodata_min = utils.distrostring2plotdata(distrostring_min)
        distrodata_max = utils.distrostring2plotdata(distrostring_max)

        distrodata = numpy.vstack((distrodata_min, distrodata_max[1, :]))

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

    def _updateFaultZoneTable(self):
        """Update table of fault zones."""

        # reset table rows to number of zones
        feature_count = len(self.fault_source_layer.selectedFeatures())
        self.zoneFaultTable.clearContents()

        if feature_count > 0:
            self.zoneFaultTable.setRowCount(feature_count)

            # get attribute indexes
            attr_idx = {'IDSOURCE': None, 'actrate_mi': None, 
                'actrate_ma': None, 'momrate_mi': None,
                'momrate_ma': None}
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

                if attr_idx['actrate_mi'] != -1:
                    feature_actrate_mi = \
                feature.attributeMap()[attr_idx['actrate_mi']].toString()
                else:
                    feature_actrate_mi = "-"

                if attr_idx['actrate_ma'] != -1:
                    feature_actrate_ma = \
                feature.attributeMap()[attr_idx['actrate_ma']].toString()
                else:
                    feature_actrate_ma = "-"

                if attr_idx['momrate_mi'] != -1:
                    feature_momrate_mi = \
                feature.attributeMap()[attr_idx['momrate_mi']].toString()
                else:
                    feature_momrate_mi = "-"

                if attr_idx['momrate_ma'] != -1:
                    feature_momrate_ma = \
                feature.attributeMap()[attr_idx['momrate_ma']].toString()
                else:
                    feature_momrate_ma = "-"

                self.zoneFaultTable.setItem(feature_idx, 
                    FAULT_ZONE_TABLE_ID_IDX,
                    QTableWidgetItem(QString("%s" % feature_id)))

                self.zoneFaultTable.setItem(feature_idx, 
                    FAULT_ZONE_TABLE_NAME_IDX, 
                    QTableWidgetItem(QString("%s" % feature_idsource)))

                self.zoneFaultTable.setItem(feature_idx, 
                    FAULT_ZONE_TABLE_ACTIVITY_MIN_IDX,
                    QTableWidgetItem(QString("%s" % feature_actrate_mi)))

                self.zoneFaultTable.setItem(feature_idx, 
                    FAULT_ZONE_TABLE_ACTIVITY_MAX_IDX, 
                    QTableWidgetItem(QString("%s" % feature_actrate_mi)))

                self.zoneFaultTable.setItem(feature_idx, 
                    FAULT_ZONE_TABLE_MOMENTRATE_MIN_IDX,
                    QTableWidgetItem(QString("%s" % feature_momrate_mi)))

                self.zoneFaultTable.setItem(feature_idx, 
                    FAULT_ZONE_TABLE_MOMENTRATE_MAX_IDX,
                    QTableWidgetItem(QString("%s" % feature_momrate_ma)))

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

        if not utils.check_at_least_one_feature_selected(
            self.area_source_layer):
            return

        self.activityLED.setColor(QColor(255, 0, 0))
        self.activityLEDLabel.setText('Computing...')
        self.btnAtticIvy.setEnabled(False)

        atticivy_result = atticivy.assignActivityAtticIvy(
            self.area_source_layer, self.catalog)

        self.activityLED.setColor(QColor(0, 255, 0))
        self.activityLEDLabel.setText('Idle')
        self.btnAtticIvy.setEnabled(True)

    def computeRecurrence(self):
        """Compute recurrence with Bungum code."""

        if not utils.check_at_least_one_feature_selected(
            self.fault_source_layer):
            return

        self.recurrenceLED.setColor(QColor(255, 0, 0))
        self.recurrenceLEDLabel.setText('Computing...')
        self.btnRecurrence.setEnabled(False)

        pr = self.fault_source_layer.dataProvider()
        pr.select()
        recurrence_result = recurrence.assignRecurrence(pr)

        self.labelTotalMoment.setText(
            "Total moment release rate:\n %.2e (min) %.2e (max) " % (
            recurrence_result))
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