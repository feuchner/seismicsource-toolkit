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
import sys
import time

from PyQt4.QtCore import *
from PyQt4.QtGui import *

from qgis.core import *

import QPCatalog
import qpplot

from algorithms import atticivy
from algorithms import momentrate
from algorithms import recurrence
from algorithms import strain

import do_plotwindow
import layers

from layers import areasource
from layers import background
from layers import eqcatalog
from layers import faultsource
from layers import render

import features
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

        # Button: compute moment rate of area zones
        QObject.connect(self.btnComputeMomentRateArea, SIGNAL("clicked()"), 
            self.updateMomentRateValuesArea)

        # Button: compute moment rate of fault zones
        QObject.connect(self.btnComputeMomentRateFault, SIGNAL("clicked()"), 
            self.updateMomentRateValuesFault)

        # TODO(fab): use selected zone in layer
        # Button: display fault zone values
        #QObject.connect(self.btnComputeFaultZoneValues, SIGNAL("clicked()"), 
            #self.updateFaultZoneValues)

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

        selected_feature = self.area_source_layer.selectedFeatures()[0]

        moment_rates = self._updateMomentRatesArea(selected_feature)
        self._updateMomentRateTableArea(moment_rates)
        self._updateMomentRatePlotArea(moment_rates)

    def updateMomentRateValuesFault(self):
        """Update values in moment rate per fault table/plot, if other 
        area zone has been selected, or zone attributes have been changed."""

        if not utils.check_only_one_feature_selected(self.fault_source_layer):
            return

        selected_feature = self.fault_source_layer.selectedFeatures()[0]

        moment_rates = self._updateMomentRatesFault(selected_feature)
        self._updateMomentRateTableFault(moment_rates)
        self._updateMomentRatePlotFault(moment_rates)

    def updateFMD(self):
        """Update FMD display for one selected area zone from
        area zone layer."""

        # selected_features = self.zoneAreaTable.selectedItems()
        if not utils.check_only_one_feature_selected(self.area_source_layer):
            return

        selected_feature = self.area_source_layer.selectedFeatures()[0]

        # get feature index of first selected row
        #feature_id = str(selected_features[AREA_ZONE_TABLE_ID_IDX].text())
        #feature_idx = self.area_zone_feature_map[feature_id]
        #feature = self.area_source_layer.selectedFeatures()[feature_idx]

        self._computeZoneFMD(selected_feature)
        self._updateFMDDisplay()

    def updateRecurrence(self):
        """Update recurrence FMD display for one selected fault zone
        in fault zone layer."""

        if not utils.check_only_one_feature_selected(self.fault_source_layer):
            return

        selected_feature = self.fault_source_layer.selectedFeatures()[0]

        moment_rates = self._updateMomentRatesArea(selected_feature)
        self._updateMomentRateTableArea(moment_rates)
        self._updateMomentRatePlotArea(moment_rates)

        self._updateRecurrenceDisplay(selected_feature)

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

        self.fmd_canvas = plots.PlotCanvas(self.figures['fmd']['fig'], 
            title="FMD")
        self.fmd_canvas.draw()

        # FMD plot window, re-populate layout
        window.layoutPlot.addWidget(self.fmd_canvas)
        self.fmd_toolbar = plots.createToolbar(self.fmd_canvas, window)
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

        self.fmd_canvas = plots.PlotCanvas(self.figures['recurrence']['fig'],
            title="Recurrence")
        self.fmd_canvas.draw()

        # FMD plot window, re-populate layout
        window.layoutPlot.addWidget(self.fmd_canvas)
        self.fmd_toolbar = plots.createToolbar(self.fmd_canvas, window)
        window.layoutPlot.addWidget(self.fmd_toolbar)
        
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

    def _updateMomentRatesArea(self, feature):
        """Update or compute moment rates for selected feature of area source
        zone layer.

        Input:
            feature     QGis polygon feature from area source layer
        
        Output:
            moment_rates    dict of computed moment rates
        """

        provider = self.area_source_layer.dataProvider()
        moment_rates = {}

        # get Shapely polygon from feature geometry
        poly, vertices = utils.polygonsQGS2Shapely((feature,))

        # get polygon area in square kilometres
        area_sqkm = utils.polygonAreaFromWGS84(poly[0]) * 1.0e-6

        ## moment rate from EQs

        # get quakes from catalog (cut with polygon)
        curr_cat = QPCatalog.QPCatalog()
        curr_cat.merge(self.catalog)
        curr_cat.cut(geometry=poly[0])

        # sum up moment from quakes (converted from Mw with Kanamori eq.)
        magnitudes = []
        for ev in curr_cat.eventParameters.event:
            mag = ev.getPreferredMagnitude()
            magnitudes.append(mag.mag.value)

        moment = numpy.array(momentrate.magnitude2moment(magnitudes))

        # scale moment: per year and area (in km^2)
        # TODO(fab): compute real catalog time span
        moment_rates['eq'] = moment.sum() / (
            area_sqkm * eqcatalog.CATALOG_TIME_SPAN)

        ## moment rate from activity (RM)

        # get attribute index of AtticIvy result
        attribute_map = utils.getAttributeIndex(provider, 
            (features.AREA_SOURCE_ATTR_ACTIVITY_RM, 
             features.AREA_SOURCE_ATTR_MMAX))
        attribute_act_name = features.AREA_SOURCE_ATTR_ACTIVITY_RM['name']
        attribute_act_idx = attribute_map[attribute_act_name][0]
        attribute_mmax_name = features.AREA_SOURCE_ATTR_MMAX['name']
        attribute_mmax_idx = attribute_map[attribute_mmax_name][0]

        # get RM (weight, a, b) values from feature attribute
        activity_str = str(feature[attribute_act_idx].toString())
        activity_arr = activity_str.strip().split()

        # ignore weights
        activity_a = [float(x) for x in activity_arr[1::3]]
        activity_b = [float(x) for x in activity_arr[2::3]]
        mmax = float(feature[attribute_mmax_idx].toDouble()[0])

        # multiply computed value with area in square kilometres
        momentrates_arr = numpy.array(momentrate.momentrateFromActivity(
            activity_a, activity_b, mmax)) * area_sqkm / (
                eqcatalog.CATALOG_TIME_SPAN)

        moment_rates['activity'] = momentrates_arr.tolist()

        ## moment rate from geodesy (strain)
        momentrate_strain = momentrate.momentrateFromStrainRate(poly[0], 
            self.data_strain_rate)
        moment_rates['strain'] = momentrate_strain / (
            eqcatalog.CATALOG_TIME_SPAN)

        return moment_rates

    def _updateMomentRateTableArea(self, moment_rates):
        self.momentRateTableArea.clearContents()

        ## from EQs
        self.momentRateTableArea.setItem(0, 0, QTableWidgetItem(QString(
            "%.2e" % moment_rates['eq'])))

        ## from activity (RM)
        
        # get maximum likelihood value from central line of table
        ml_idx = len(moment_rates['activity']) / 2
        mr_ml = moment_rates['activity'][ml_idx]
        self.momentRateTableArea.setItem(0, 1, QTableWidgetItem(QString(
            "%.2e" % mr_ml)))

        ## from geodesy (strain)
        self.momentRateTableArea.setItem(0, 2, QTableWidgetItem(QString(
            "%.2e" % moment_rates['strain'])))

    def _updateMomentRatePlotArea(self, moment_rates):

        window = self.createPlotWindow()

        # new moment rate plot
        self.fig_moment_rate_comparison_area = \
            plots.MomentRateComparisonPlotArea()
        self.fig_moment_rate_comparison_area = \
            self.fig_moment_rate_comparison_area.plot(imgfile=None, 
                data=moment_rates)

        self.canvas_moment_rate_comparison_area = plots.PlotCanvas(
            self.fig_moment_rate_comparison_area, 
            title="Seismic Moment Rates")
        self.canvas_moment_rate_comparison_area.draw()

        # plot widget
        window.layoutPlot.addWidget(
            self.canvas_moment_rate_comparison_area)
        self.toolbar_moment_rate_comparison_area = plots.createToolbar(
            self.canvas_moment_rate_comparison_area, 
            window)
        window.layoutPlot.addWidget(
            self.toolbar_moment_rate_comparison_area)

    def _updateMomentRatesFault(self, feature):
        """Update or compute moment rates for selected feature of fault source
        zone layer.

        Input:
            feature     QGis polygon feature from area source layer
        
        Output:
            moment_rates    dict of computed moment rates
        """

        provider = self.fault_source_layer.dataProvider()
        provider_area = self.area_source_layer.dataProvider()

        attribute_map = utils.getAttributeIndex(provider, 
            (features.FAULT_SOURCE_ATTR_MOMENTRATE_MIN,
             features.FAULT_SOURCE_ATTR_MOMENTRATE_MAX))

        moment_rates = {}

        # get Shapely polygon from feature geometry
        poly, vertices = utils.polygonsQGS2Shapely((feature,))

        # get polygon area in square kilometres
        area_sqkm = utils.polygonAreaFromWGS84(poly[0]) * 1.0e-6

        # get buffer polygon with 30 km extension and its area in square km
        buffer_deg = 360.0 * (recurrence.BUFFER_AROUND_FAULT_POLYGONS / \
            utils.EARTH_CIRCUMFERENCE_EQUATORIAL_KM)
        buffer_poly = poly[0].buffer(buffer_deg)
        buffer_area_sqkm = utils.polygonAreaFromWGS84(buffer_poly) * 1.0e-6

        ## moment rate from EQs

        # get quakes from catalog (cut with buffer polygon)
        curr_cat = QPCatalog.QPCatalog()
        curr_cat.merge(self.catalog)
        curr_cat.cut(geometry=buffer_poly)

        # sum up moment from quakes (converted from Mw with Kanamori eq.)
        magnitudes = []
        for ev in curr_cat.eventParameters.event:
            mag = ev.getPreferredMagnitude()
            magnitudes.append(mag.mag.value)

        moment = numpy.array(momentrate.magnitude2moment(magnitudes))

        # scale moment: per year and area (in km^2)
        # TODO(fab): compute real catalog time span
        moment_rates['eq'] = moment.sum() / (
            area_sqkm * eqcatalog.CATALOG_TIME_SPAN)

        ## moment rate from activity (RM)
        ## TODO(fab): get real mmax and mcdist from background zone
        mmax = 7.0
        mcdist = "4.0 1700 8.5 1200"
        activity = atticivy.computeActivityAtticIvy((buffer_poly, ), (mmax, ), 
            (mcdist, ), self.catalog)
        
        # get RM (weight, a, b) values from feature attribute
        activity_str = activity[0][2]
        activity_arr = activity_str.strip().split()

        # ignore weights
        activity_a = [float(x) for x in activity_arr[1::3]]
        activity_b = [float(x) for x in activity_arr[2::3]]

        # multiply computed value with area in square kilometres
        momentrates_arr = numpy.array(momentrate.momentrateFromActivity(
            activity_a, activity_b, mmax)) * area_sqkm / (
                eqcatalog.CATALOG_TIME_SPAN)

        moment_rates['activity'] = momentrates_arr.tolist()

        ## moment rate from slip rate

        # TODO(fab): correct scaling of moment rate from slip rate
        momrate_min_name = features.FAULT_SOURCE_ATTR_MOMENTRATE_MIN['name']
        momrate_max_name = features.FAULT_SOURCE_ATTR_MOMENTRATE_MAX['name']
        momentrate_min = \
            feature[attribute_map[momrate_min_name][0]].toDouble()[0] / (
                eqcatalog.CATALOG_TIME_SPAN)
        momentrate_max = \
            feature[attribute_map[momrate_max_name][0]].toDouble()[0] / (
                eqcatalog.CATALOG_TIME_SPAN)
        moment_rates['slip'] = [momentrate_min, momentrate_max]

        return moment_rates

    def _updateMomentRateTableFault(self, moment_rates):
        self.momentRateTableFault.clearContents()

        ## from EQs
        self.momentRateTableFault.setItem(0, 0, QTableWidgetItem(QString(
            "%.2e" % moment_rates['eq'])))

        ## from activity (RM)
        # get maximum likelihood value from central line of table
        ml_idx = len(moment_rates['activity']) / 2
        mr_ml = moment_rates['activity'][ml_idx]
        self.momentRateTableFault.setItem(0, 1, QTableWidgetItem(QString(
            "%.2e" % mr_ml)))

        ## from geology (slip)
        self.momentRateTableFault.setItem(0, 2, QTableWidgetItem(QString(
            "%.2e" % moment_rates['slip'][1])))

    def _updateMomentRatePlotFault(self, moment_rates):

        window = self.createPlotWindow()

        # new moment rate plot
        self.fig_moment_rate_comparison_fault = \
            plots.MomentRateComparisonPlotFault()
        self.fig_moment_rate_comparison_fault = \
            self.fig_moment_rate_comparison_fault.plot(imgfile=None, 
                data=moment_rates)

        self.canvas_moment_rate_comparison_fault = plots.PlotCanvas(
            self.fig_moment_rate_comparison_fault, 
            title="Seismic Moment Rates")
        self.canvas_moment_rate_comparison_fault.draw()

        # plot widget
        window.layoutPlot.addWidget(
            self.canvas_moment_rate_comparison_fault)
        self.toolbar_moment_rate_comparison_fault = plots.createToolbar(
            self.canvas_moment_rate_comparison_fault, 
            window)
        window.layoutPlot.addWidget(
            self.toolbar_moment_rate_comparison_fault)

    def createPlotWindow(self):
        """Create new plot window dialog."""
 
        plot_window = do_plotwindow.PlotWindow(self.iface)
        plot_window.setModal(False)
        plot_window.show()
        plot_window.raise_()
        self.plot_windows.append(plot_window)
        return plot_window