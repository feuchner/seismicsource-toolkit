# -*- coding: utf-8 -*-
"""
SHARE Seismic Source Toolkit

Dialog for results of zone analysis.

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
#import os
#import shapely.geometry
#import shapely.ops
#import sys

from PyQt4.QtCore import *
from PyQt4.QtGui import *

from qgis.core import *

from ui_zone_analysis import Ui_ZoneAnalysis

MIN_SLIVER_DISTANCE = 10
NEIGHBOR_COUNT = 3

class ZoneAnalysis(QDialog, Ui_ZoneAnalysis):
    """This class represents the zone analysis dialog."""

    def __init__(self, iface, zone_layer):
        QDialog.__init__(self)
        self.iface = iface
        self.setupUi(self)

        self.zone_layer = zone_layer
        self._analyze()

    def _analyze(self):
        """Brute-force nearest neighbor analysis."""

        # point array
        # 0 - point ID
        # 1 - zone ID
        # 2 - lon
        # 3 - lat
        points = []

        # make point layer from polygons
        prz = self.zone_layer.dataProvider()
        prz.select()

        #QMessageBox.warning(None, "Features", 
            #"Zone layer has %s features" % prz.featureCount())

        feature_cnt = 0
        point_cnt = 0
        feature = QgsFeature()
        while prz.nextFeature(feature):

            if feature_cnt > 2:
                break

            geom = feature.geometry().asPolygon()

            if len(geom) > 0:
                for vertex in geom[0]:
                    points.append([float(point_cnt), float(feature.id()), 
                        vertex.x(), vertex.y()])
                    point_cnt += 1

            feature_cnt += 1

        points_arr = numpy.array(points, dtype=float)
        del points

        #QMessageBox.information(None, "Point layer", 
            #"Point layer has %s features, %s array rows" % (point_cnt, points_arr.shape[0]))

        # get nearest neighbors
        # neighbors array holds (9 cols):
        #  0: distance
        #  1: first point id
        #  2: polygon id
        #  3: first point lon
        #  4: first point lat
        #  5: second point id
        #  6: polygon id
        #  7: second point lon
        #  8: second point lat

        neighbor_cnt = 0
        neighbors = numpy.ones((point_cnt * (point_cnt-1) / 2, 9), dtype=float) * numpy.nan

        for reference_point_idx in xrange(points_arr.shape[0]):
            for test_point_idx in xrange(reference_point_idx+1, points_arr.shape[0]):

                # check if points are in same polygon
                if points_arr[reference_point_idx, 1] == points_arr[test_point_idx, 1]:
                    continue

                # get distance
                distArea = QgsDistanceArea()
                distance = float(distArea.measureLine(
                    QgsPoint(points_arr[reference_point_idx, 2], points_arr[reference_point_idx, 3]), 
                    QgsPoint(points_arr[test_point_idx, 2], points_arr[test_point_idx, 3])))

                # QMessageBox.information(None, "Distance", "%s" % distance)

                # if distance is greater than the margin, ignore
                if distance > MIN_SLIVER_DISTANCE:
                    continue

                neighbors[neighbor_cnt, 0] = distance
                neighbors[neighbor_cnt, 1] = reference_point_idx
                neighbors[neighbor_cnt, 2] = points_arr[reference_point_idx, 1]
                neighbors[neighbor_cnt, 3] = points_arr[reference_point_idx, 2]
                neighbors[neighbor_cnt, 4] = points_arr[reference_point_idx, 3]
                neighbors[neighbor_cnt, 5] = test_point_idx
                neighbors[neighbor_cnt, 6] = points_arr[test_point_idx, 1]
                neighbors[neighbor_cnt, 7] = points_arr[test_point_idx, 2]
                neighbors[neighbor_cnt, 8] = points_arr[test_point_idx, 3]

                neighbor_cnt += 1

        del points_arr

        # reshape array
        neighbors_trunc = neighbors[0:neighbor_cnt, :]

        #QMessageBox.information(None, "Neighbors", "%s" % neighbors_trunc)
        #QMessageBox.information(None, "Neighbors Dist", "%s" % neighbors_trunc[:, 0])

        # sort array (distance)
        dist_indices = numpy.argsort(neighbors_trunc[:, 0], axis=0)

        #QMessageBox.information(None, "Indices", "%s" % dist_indices)

        neighbors_trunc = neighbors_trunc[dist_indices.T]

        # write to table
        self._display_table(neighbors_trunc)

        #self.table.clearContents()
        #self.table.setRowCount(neighbor_cnt)
        #self.table.setColumnCount(neighbors_trunc.shape[1])
        
        #for row in xrange(neighbor_cnt):
            #for col in xrange(neighbors_trunc.shape[1]):

                #if neighbors_trunc[row, col] == int(neighbors_trunc[row, col]):
                    #display_value = int(neighbors_trunc[row, col])
                #else:
                    #display_value = neighbors_trunc[row, col]

                #self.table.setItem(row, col, 
                    #QTableWidgetItem(QString("%s" % display_value)))

    def _display_table(self, neighbors_trunc):
        """Write computed values to table cells."""
        
        neighbor_cnt = neighbors_trunc.shape[0]
        self.table.clearContents()
        self.table.setRowCount(neighbor_cnt)
        self.table.setColumnCount(neighbors_trunc.shape[1])

        for row in xrange(neighbor_cnt):
            for col in xrange(neighbors_trunc.shape[1]):

                if neighbors_trunc[row, col] == int(neighbors_trunc[row, col]):
                    display_str = "%s" % int(neighbors_trunc[row, col])
                else:
                    display_str = "%.3f" % neighbors_trunc[row, col]

                self.table.setItem(row, col, QTableWidgetItem(
                    QString(display_str)))

    #def _analyze_with_index(self):
        #"""Analyze nearest neighbors with geospatial index.
        #Work in progress."""

        ## create point layer
        #point_layer = QgsVectorLayer("Point", "Zone points", "memory")
        #pr = point_layer.dataProvider()

        ## spatial index for point layer
        #point_index = QgsSpatialIndex()

        ##QMessageBox.warning(None, "Features", 
            ##"Zone layer has %s features" % prz.featureCount())

        ## make point layer from polygons
        #prz = self.zone_layer.dataProvider()
        #prz.select()

        #feature_cnt = 0
        #feature = QgsFeature()
        #while prz.nextFeature(feature):

            #feature_cnt += 1
            #geom = feature.geometry().asPolygon()

            #if len(geom) > 0:
                #for vertex in geom[0]:
                    #f = QgsFeature()
                    #f.setGeometry(QgsGeometry.fromPoint(vertex))
                    #pr.addFeatures([f])
                    #point_index.insertFeature(f)

            ##else:
                ### feature 433 has no ring
                ##QMessageBox.warning(None, "No ring", 
                    ##"Feature %s has no ring" % feature_cnt)

        #point_layer.updateExtents()

        ## get nearest neighbors
        ## second pass: get distances

        ## NOTE: how to access spatial index?
        ## pr.createSpatialIndex()

        ##QMessageBox.information(None, "Provider", "%s" % pr.__dict__)

        ## returns array of feature IDs of five nearest features
        ## nearest = point_index.nearestNeighbor(QgsPoint(25.4, 12.7), 5)

        ## neighbors array holds (9 cols):
        ##  0: distance
        ##  1: first point id
        ##  2: polygon id
        ##  3: first point lon
        ##  4: first point lat
        ##  5: second point id
        ##  6: polygon id
        ##  7: second point lon
        ##  8: second point lat

        ## - polygon numbers (only for vertices not in same polygon)
        #point_count = pr.featureCount()
        #QMessageBox.information(None, "Point layer", 
            #"Point layer has %s features" % point_count)

        #neighbors = numpy.ones((point_count * 3, 9), dtype=float) * numpy.nan

        ## create mapping from feature id to index
        ## self.feature_map = {}

        #neighbor_ctr = 0
        #feature = QgsFeature()
        #neighbor_feature = QgsFeature()
        #pr.select()
        #pr.rewind()

        #pr_neighbors = point_layer.dataProvider()
        #pr_neighbors.select()
        #while pr.nextFeature(feature):
            
            #pr_neighbors.rewind()
            #reference_id = float(feature.id())
            #reference_lon = feature.geometry().asPoint().x()
            #reference_lat = feature.geometry().asPoint().y()

            ## get 3 nearest neighbors, list of feature ids
            #nearest = point_index.nearestNeighbor(
                #feature.geometry().asPoint(), NEIGHBOR_COUNT)

            #QMessageBox.information(None, "Nearest", 
                #"Found %s neighbors, IDs: %s" % (len(nearest), nearest))

            #for neighbor_id in nearest:

                ## get feature from id
                #pr_neighbors.featureAtId(int(neighbor_id), neighbor_feature, True)

                #QMessageBox.information(None, "Neighbor", 
                    #"neighbor with ID: %s" % neighbor_id)

                #if neighbor_feature is not None and \
                    #neighbor_feature.geometry() is not None:

                    #distArea = QgsDistanceArea()
                    #dist = float(distArea.measureLine(
                        #feature.geometry().asPoint(), 
                        #neighbor_feature.geometry().asPoint()))

                    #neighbors[neighbor_ctr, 0] = reference_id
                    #neighbors[neighbor_ctr, 2] = reference_lon
                    #neighbors[neighbor_ctr, 3] = reference_lat

                    #neighbors[neighbor_ctr, 4] = float(neighbor_feature.id())
                    #neighbors[neighbor_ctr, 6] = neighbor_feature.geometry().asPoint().x()
                    #neighbors[neighbor_ctr, 7] = neighbor_feature.geometry().asPoint().y()

                    #neighbors[neighbor_ctr, 8] = dist

                    #neighbor_ctr += 1

            ##QMessageBox.information(None, "Point layer", 
                ##"point no %s, id: %s, geom: %s" % (feature_idx, feature.id(),
                    ##feature.geometry().asPoint()))


        ## write to table
        #self.table.clearContents()
        #self.table.setRowCount(neighbor_ctr)
        #self.table.setColumnCount(neighbors.shape[1])
        
        #for row in xrange(neighbor_ctr):
            #for col in xrange(neighbors.shape[1]):
                #self.table.setItem(row, col, 
                    #QTableWidgetItem(QString("%s" % neighbors[row, col])))
