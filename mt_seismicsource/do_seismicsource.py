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

from PyQt4.QtCore import *
from PyQt4.QtGui import *

from qgis.core import *

import QPCatalog

from ui_seismicsource import Ui_SeismicSource

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')

BACKGROUND_FILE_DIR = 'misc'
BACKGROUND_FILE = 'world.shp'

ZONE_FILE_DIR = 'area_sources/GEM1'
ZONE_FILE = 'europe_source_model.shp'

FAULT_FILE_DIR = 'fault_sources/DISS'
FAULT_FILE = 'CSSTop_polyline.shp'

CATALOG_DIR = 'eq_catalog'
CATALOG_FILE = 'cenec-zmap.dat'
#CATALOG_FILE = 'SHARE_20110311.csv'

MIN_EVENTS_FOR_GR = 10

try:
    from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.backends.backend_qt4agg import NavigationToolbar2QTAgg as NavigationToolbar
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

        # Button: cumul distribution plot
        QObject.connect(self.btnDisplayCumulDist, SIGNAL("clicked()"), 
            self.updateCumulDist)

        # Button: FMD plot
        QObject.connect(self.btnDisplayFMD, SIGNAL("clicked()"), 
            self.updateFMD)

        # Checkbox: Normalize FMD plot
        QObject.connect(self.checkBoxGRAnnualRate, SIGNAL("stateChanged(int)"), 
            self._updateFMDDisplay)

        # init stuff
        self.background_layer = None
        self.area_source_layer = None
        self.fault_source_layer = None
        self.catalog_layer = None

        self.progressBarLoadData.setValue(0)
        self.labelCatalogEvents.setText("Catalog events: 0")
        self.labelSelectedZones.setText("Selected zones: 0")
        self.labelSelectedEvents.setText("Selected events: 0")

    def loadDataLayers(self):

        # remove default layers
        # QgsMapLayerRegistry.instance().removeMapLayer(layer_id)

        self.loadBackgroundLayer()
        self.progressBarLoadData.setValue(50)
        self.loadDefaultLayers()
        self.progressBarLoadData.setValue(100)

        # set zone layer to active layer

    def loadBackgroundLayer(self):
        if self.background_layer is None:
            background_path = os.path.join(DATA_DIR, BACKGROUND_FILE_DIR, 
                BACKGROUND_FILE)
            self.background_layer = QgsVectorLayer(background_path, 
                "Political Boundaries", "ogr")
            QgsMapLayerRegistry.instance().addMapLayer(self.background_layer)
        
    def loadDefaultLayers(self):
        self.loadAreaSourceLayer()
        self.loadFaultSourceLayer()
        self.loadCatalogLayer()

    def loadAreaSourceLayer(self):
        if self.area_source_layer is None:
            area_source_path = os.path.join(DATA_DIR, ZONE_FILE_DIR, ZONE_FILE)
            self.area_source_layer = QgsVectorLayer(area_source_path, "Area Sources", 
                "ogr")
            QgsMapLayerRegistry.instance().addMapLayer(self.area_source_layer)

    def loadFaultSourceLayer(self):
        if self.fault_source_layer is None:
            fault_source_path = os.path.join( DATA_DIR, FAULT_FILE_DIR, 
                FAULT_FILE )
            self.fault_source_layer = QgsVectorLayer(fault_source_path, 
                "Fault Sources", "ogr")
            QgsMapLayerRegistry.instance().addMapLayer(self.fault_source_layer)

    def loadCatalogLayer(self):
        if self.catalog_layer is None:
            catalog_path = os.path.join(DATA_DIR, CATALOG_DIR, CATALOG_FILE)

            self.catalog = QPCatalog.QPCatalog()
            self.catalog.importZMAP(catalog_path, minimumDataset=True)
            #self.catalog.importSHAREPotsdamCSV(catalog_path)

            # cut catalog to years > 1900 (because of datetime)
            # TODO(fab): change the datetime lib to mx.DateTime
            self.catalog.cut(mintime='1900-01-01', mintime_exclude=True)
            self.labelCatalogEvents.setText("Catalog events: %s" % self.catalog.size())

            # cut with selected polygons
            self.catalog_selected = QPCatalog.QPCatalog()
            self.catalog_selected.merge(self.catalog)
            self.labelSelectedEvents.setText("Selected events: %s" % self.catalog_selected.size())

            # create layer
            self.catalog_layer = QgsVectorLayer("Point", "CENEC catalog", "memory")
            pr = self.catalog_layer.dataProvider()

            # add fields
            pr.addAttributes([QgsField("magnitude", QVariant.Double),
                              QgsField("depth",  QVariant.Double)])

            # add EQs as features
            for curr_event in self.catalog_selected.eventParameters.event:
                curr_ori = curr_event.getPreferredOrigin()

                # skip events without magnitude
                try:
                    curr_mag = curr_event.getPreferredMagnitude()
                except IndexError:
                    continue

                curr_lon = curr_ori.longitude.value
                curr_lat = curr_ori.latitude.value
                magnitude = curr_mag.mag.value

                try:
                    depth = curr_ori.depth.value
                except Exception:
                    depth = numpy.nan

                f = QgsFeature()
                f.setGeometry( QgsGeometry.fromPoint( QgsPoint(
                    curr_lon,curr_lat) ) )
                f.setAttributeMap( { 0 : QVariant(magnitude),
                                     1 : QVariant(depth) } )
                pr.addFeatures( [ f ] )

            # update layer's extent when new features have been added
            # because change of extent in provider is not propagated to the layer
            self.catalog_layer.updateExtents()
            QgsMapLayerRegistry.instance().addMapLayer(self.catalog_layer)


    def updateCumulDist(self):
        self._filterEventsFromSelection()
        self._computeCumulDist()
        self._plotCumulDist()
        
    def _computeCumulDist(self):
        self.figures['cumuldist'] = {}
        self.figures['cumuldist']['fig'] = \
            self.catalog_selected.getCumulativeDistribution().plot(
                imgfile=None)

    def _plotCumulDist(self):

        self.figures['cumuldist']['axes'] = \
            self.figures['cumuldist']['fig'].add_subplot(111)
        self.figures['cumuldist']['fp'] = FontManager.FontProperties()

        self.figures['cumuldist']['fig'].suptitle('Cumulative Distribution',
            fontproperties=self.figures['cumuldist']['fp'])

        self.figures['cumuldist']['canvas'] = FigureCanvas(
            self.figures['cumuldist']['fig'])
        self.figures['cumuldist']['canvas'].draw()

        self.figures['cumuldist']['mpltoolbar'] = NavigationToolbar(
            self.figures['cumuldist']['canvas'], self.widgetPlotCumulDist)
        lstActions = self.figures['cumuldist']['mpltoolbar'].actions()
        self.figures['cumuldist']['mpltoolbar'].removeAction(lstActions[7])
        
        # check if widget already added to layout
        if self.layoutPlotCumulDist.isEmpty():
            self.layoutPlotCumulDist.addWidget(
                self.figures['cumuldist']['canvas'])
            self.layoutPlotCumulDist.addWidget(
                self.figures['cumuldist']['mpltoolbar'])

    def updateFMD(self):
        self._filterEventsFromSelection()
        self._computeFMD()
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
        self.lcdNumberAValue.display("%.2f" % aValue)
        self.lcdNumberBValue.display("%.2f" % self.figures['fmd']['fmd'].GR['bValue'])

    def _plotFMD(self):

        self.figures['fmd']['fig'] = self.figures['fmd']['fmd'].plot(imgfile=None, 
            fmdtype='cumulative', 
            normalize=self.checkBoxGRAnnualRate.isChecked())

        self.figures['fmd']['axes'] = \
            self.figures['fmd']['fig'].add_subplot(111)
        self.figures['fmd']['fp'] = FontManager.FontProperties()

        self.figures['fmd']['fig'].suptitle('FMD', 
            fontproperties=self.figures['fmd']['fp'])

        self.figures['fmd']['canvas'] = FigureCanvas(
            self.figures['fmd']['fig'])
        self.figures['fmd']['canvas'].draw()

        self.figures['fmd']['mpltoolbar'] = NavigationToolbar(
            self.figures['fmd']['canvas'], self.widgetPlotFMD)
        lstActions = self.figures['fmd']['mpltoolbar'].actions()
        self.figures['fmd']['mpltoolbar'].removeAction(lstActions[7])

        # check if widget already added to layout
        if self.layoutPlotFMD.isEmpty():
            self.layoutPlotFMD.addWidget(self.figures['fmd']['canvas'])
            self.layoutPlotFMD.addWidget(self.figures['fmd']['mpltoolbar'])

    def _filterEventsFromSelection(self):
        """Select events from EQ catalog that are within selected polygons
        from area source layer."""

        # get selected polygons from area source layer
        layer_to_select_from = self.area_source_layer
        features_selected = layer_to_select_from.selectedFeatures()

        selected_polygons = []
        for feature in features_selected:

            # yields list of QGSPoints
            # TODO(fab): if layer is not of Polygon type, complain
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
