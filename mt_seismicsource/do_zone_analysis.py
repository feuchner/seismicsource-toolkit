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
import shapely.geometry
# import shapely.ops

from PyQt4.QtCore import *
from PyQt4.QtGui import *

from qgis.core import *

from ui_zone_analysis import Ui_ZoneAnalysis

MIN_SLIVER_DISTANCE = 0.1
ZONE_BUFFER_DISTANCE = 0.5

NEIGHBORING_ZONE_COUNT = 10
NEIGHBOR_COUNT = 3

ANALYSIS_TABLE_COLUMN_COUNT = 9

SLIVER_ANALYSIS_LAYER_ID = "Sliver Analysis"

class ZoneAnalysis(QDialog, Ui_ZoneAnalysis):
    """This class represents the zone analysis dialog."""

    def __init__(self, iface, zone_layer, min_distance=MIN_SLIVER_DISTANCE,
        zone_buffer=ZONE_BUFFER_DISTANCE):
        QDialog.__init__(self)
        self.iface = iface
        self.setupUi(self)

        self.zone_layer = zone_layer
        self.min_distance = min_distance
        self.zone_buffer = zone_buffer
        self.analysis_layer = None
        self.distance_matrix = None

        self._analyze_buffer_based()
        # self._analyze_distance_based()

    def _analyze_buffer_based(self):
        """Almost brute-force nearest neighbor analysis, using
        buffer around reference zones."""

        if len(self.zone_layer.selectedFeatures()) == 0:
            QMessageBox.warning(None, "No source zone selected", 
                "Please select at least one source zone")
            return

        # get feature IDs for selected source zone polygons
        selected_zones_ids = [feature.id() for feature in \
            self.zone_layer.selectedFeatures()]

        # convert all QGis polygons of source zone layer to Shapely
        source_zones_shapely = []
        selected_zones_indices = []

        prz = self.zone_layer.dataProvider()
        prz.select()

        feature_cnt = 0
        for feature in prz:

            qgis_geometry_aspolygon = feature.geometry().asPolygon()
            if len(qgis_geometry_aspolygon) == 0:
                continue
            else:
                vertices = [(x.x(), x.y()) for x in qgis_geometry_aspolygon[0]]
                if len(vertices) == 0:
                    continue

            if feature.id() in selected_zones_ids:
                selected_zones_indices.append(feature_cnt)

            shapely_polygon = shapely.geometry.Polygon(vertices)
            source_zones_shapely.append(shapely_polygon)

            feature_cnt += 1

        # get neighboring zones for each reference zone
        # - add margin ("buffer") to zone outline
        # - select zones that overlap with that larger zone
        test_zone_indices = []
        for ref_zone_idx in selected_zones_indices:

            # build buffer around zone
            buffered_zone = source_zones_shapely[ref_zone_idx].buffer(
                self.zone_buffer)

            for test_zone_idx, test_zone in enumerate(source_zones_shapely):

                if ref_zone_idx == test_zone_idx:
                    continue

                if buffered_zone.intersects(test_zone):
                    test_zone_indices.append(test_zone_idx)
            
        # remove duplicates in test_zone_indices
        test_zone_indices = list(set(test_zone_indices))

        #QMessageBox.information(None, "Neighboring zones", "%s" % (test_zone_indices))

        # get vertices for reference zone and neighboring zones

        # point array
        # 0 - point ID
        # 1 - zone ID
        # 2 - lon
        # 3 - lat
        points = []
        reference_vertex_indices = []

        # extract vertices from reference and test source polygons
        point_cnt = 0
        involved_zones_indices = selected_zones_indices
        involved_zones_indices.extend(test_zone_indices)
        involved_zones_indices = list(set(involved_zones_indices))

        #QMessageBox.information(None, "Involved zones", "%s" % (involved_zones_indices))

        for curr_zone_idx, curr_zone in enumerate(source_zones_shapely):

            if curr_zone_idx in involved_zones_indices: 
                coords = curr_zone.exterior.coords

                #QMessageBox.information(None, "Coords", 
                    #"Zone: %s, coords: %s" % (curr_zone_idx, coords))

                if curr_zone_idx in selected_zones_indices:
                    addRefZone = True
                else:
                    addRefZone = False

                if len(coords) > 3:
                    for (vertex_lon, vertex_lat) in list(coords)[0:-1]:
                        points.append([float(point_cnt), float(curr_zone_idx),
                            vertex_lon, vertex_lat])

                        if addRefZone:
                            reference_vertex_indices.append(point_cnt)

                        point_cnt += 1

        points_arr = numpy.array(points, dtype=float)
        del points
        
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

        maxNeighborCount = len(reference_vertex_indices) * point_cnt

        neighbor_cnt = 0
        neighbors = numpy.ones((maxNeighborCount, 
            ANALYSIS_TABLE_COLUMN_COUNT), dtype=float) * numpy.nan

        self._replaceAnalysisLayer()
        pra = self.analysis_layer.dataProvider()
        for reference_point_idx in reference_vertex_indices:

            reference_point = shapely.geometry.Point(
                (points_arr[reference_point_idx, 2], 
                 points_arr[reference_point_idx, 3]))

            for test_point_idx in xrange(points_arr.shape[0]):

                # skip, if same point or points are in same polygon
                if reference_point_idx == test_point_idx or \
                    points_arr[reference_point_idx, 1] == \
                        points_arr[test_point_idx, 1]:
                    continue

                # get distance
                test_point = shapely.geometry.Point(
                    (points_arr[test_point_idx, 2], 
                     points_arr[test_point_idx, 3]))

                distance = reference_point.distance(test_point)

                # if points are the same, distance is zero, or distance is greater
                # than the margin, ignore
                if reference_point == test_point or \
                    distance == 0.0 or \
                    distance > self.min_distance:
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
 
                # add point pair to analysis layer
                if test_point_idx == 0:
                    pra.addFeatures([self._new_point_feature_from_coord(
                        points_arr[reference_point_idx, 2], 
                        points_arr[reference_point_idx, 3])])

                pra.addFeatures([self._new_point_feature_from_coord(
                    points_arr[test_point_idx, 2], 
                    points_arr[test_point_idx, 3])])

                neighbor_cnt += 1

        del points_arr

        # reshape array
        neighbors_trunc = neighbors[0:neighbor_cnt, :]

        # sort array (distance)
        dist_indices = numpy.argsort(neighbors_trunc[:, 0], axis=0)

        neighbors_trunc = neighbors_trunc[dist_indices.T]

        # write to table
        self._display_table(neighbors_trunc)

    def _analyze_distance_based(self):
        """Almost brute-force nearest neighbor analysis, using distance matrix
        computed for zones."""

        if len(self.zone_layer.selectedFeatures()) == 0:
            QMessageBox.warning(None, "No source zone selected", 
                "Please select at least one source zone")
            return

        # get feature IDs for selected source zone polygons
        selected_zones_ids = [feature.id() for feature in \
            self.zone_layer.selectedFeatures()]

        # convert all QGis polygons of source zone layer to Shapely
        source_zones_shapely = []
        selected_zones_indices = []

        prz = self.zone_layer.dataProvider()
        prz.select()

        feature_cnt = 0
        for feature in prz:

            qgis_geometry_aspolygon = feature.geometry().asPolygon()
            if len(qgis_geometry_aspolygon) == 0:
                continue
            else:
                vertices = [(x.x(), x.y()) for x in qgis_geometry_aspolygon[0]]
                if len(vertices) == 0:
                    continue

            if feature.id() in selected_zones_ids:
                selected_zones_indices.append(feature_cnt)

            shapely_polygon = shapely.geometry.Polygon(vertices)
            source_zones_shapely.append(shapely_polygon)

            feature_cnt += 1

        # build distance matrix
        # TODO(fab): we don't need full distance matrix!
        self._compute_distance_matrix(source_zones_shapely)

        # get neighboring zones for each selected reference zone
        # - select NEIGHBORING_ZONE_COUNT neighboring zones from distance matrix
        test_zone_indices = []
        for ref_zone_idx in selected_zones_indices:
            test_zone_distances = self._get_distance_list(ref_zone_idx)

            # first index in closest zone list is reference zone itself
            # start at index 1
            test_zone_indices.extend(self._get_closest_zone_indices(
                test_zone_distances)[1:NEIGHBORING_ZONE_COUNT+1].tolist())
            
        # remove duplicates in test_zone_indices
        test_zone_indices = list(set(test_zone_indices))

        #QMessageBox.information(None, "Neighboring zones", "%s" % (test_zone_indices))

        # get vertices for reference zone and neighboring zones

        # point array
        # 0 - point ID
        # 1 - zone ID
        # 2 - lon
        # 3 - lat
        points = []
        reference_vertex_indices = []

        # extract vertices from reference and test source polygons
        point_cnt = 0
        involved_zones_indices = selected_zones_indices
        involved_zones_indices.extend(test_zone_indices)
        involved_zones_indices = list(set(involved_zones_indices))

        #QMessageBox.information(None, "Involved zones", "%s" % (involved_zones_indices))

        for curr_zone_idx, curr_zone in enumerate(source_zones_shapely):

            if curr_zone_idx in involved_zones_indices: 
                coords = curr_zone.exterior.coords

                #QMessageBox.information(None, "Coords", 
                    #"Zone: %s, coords: %s" % (curr_zone_idx, coords))

                if curr_zone_idx in selected_zones_indices:
                    addRefZone = True
                else:
                    addRefZone = False

                if len(coords) > 3:
                    for (vertex_lon, vertex_lat) in list(coords)[0:-1]:
                        points.append([float(point_cnt), float(curr_zone_idx),
                            vertex_lon, vertex_lat])

                        if addRefZone:
                            reference_vertex_indices.append(point_cnt)

                        point_cnt += 1

        points_arr = numpy.array(points, dtype=float)
        del points
        
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

        maxNeighborCount = len(reference_vertex_indices) * point_cnt

        neighbor_cnt = 0
        neighbors = numpy.ones((maxNeighborCount, 
            ANALYSIS_TABLE_COLUMN_COUNT), dtype=float) * numpy.nan

        self._replaceAnalysisLayer()
        pra = self.analysis_layer.dataProvider()
        for reference_point_idx in reference_vertex_indices:

            reference_point = shapely.geometry.Point(
                (points_arr[reference_point_idx, 2], 
                 points_arr[reference_point_idx, 3]))

            for test_point_idx in xrange(points_arr.shape[0]):

                # skip, if same point or points are in same polygon
                if reference_point_idx == test_point_idx or \
                    points_arr[reference_point_idx, 1] == \
                        points_arr[test_point_idx, 1]:
                    continue

                # get distance
                test_point = shapely.geometry.Point(
                    (points_arr[test_point_idx, 2], 
                     points_arr[test_point_idx, 3]))

                distance = reference_point.distance(test_point)

                # if points are the same, distance is zero, or distance is greater
                # than the margin, ignore
                if reference_point == test_point or \
                    distance == 0.0 or \
                    distance > self.min_distance:
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
 
                # add point pair to analysis layer
                if test_point_idx == 0:
                    pra.addFeatures([self._new_point_feature_from_coord(
                        points_arr[reference_point_idx, 2], 
                        points_arr[reference_point_idx, 3])])

                pra.addFeatures([self._new_point_feature_from_coord(
                    points_arr[test_point_idx, 2], 
                    points_arr[test_point_idx, 3])])

                neighbor_cnt += 1

        del points_arr

        # reshape array
        neighbors_trunc = neighbors[0:neighbor_cnt, :]

        # sort array (distance)
        dist_indices = numpy.argsort(neighbors_trunc[:, 0], axis=0)

        neighbors_trunc = neighbors_trunc[dist_indices.T]

        # write to table
        self._display_table(neighbors_trunc)

    def _analyze_brute(self):
        """Almost brute-force nearest neighbor analysis."""

        # get feature IDs for selected source zone polygons
        selected_zones_ids = [feature.id() for feature in \
            self.zone_layer.selectedFeatures()]

        if len(selected_zones_ids) == 0:
            QMessageBox.warning(None, "No source zone selected", 
                "Please select at least one source zone")
            return

        # get neighboring zones for each reference zone
        # - add margin ("buffer") to zone outline
        # - select zones that overlap with that larger zone
        # get vertices for reference zone and neighboring zones
        # - ref zone goes first
        
        # point array
        # 0 - point ID
        # 1 - zone ID
        # 2 - lon
        # 3 - lat
        points = []
        reference_vertex_indices = []

        # extract vertices from source zone polygon layer
        prz = self.zone_layer.dataProvider()
        pra = self.analysis_layer.dataProvider()
        prz.select()

        feature_cnt = 0
        point_cnt = 0
        for feature in prz:

            geom = feature.geometry().asPolygon()

            if feature.id() in selected_zones_ids:
                addToRefVertices = True
            else:
                addToRefVertices = False

            if len(geom) > 0:
                for vertex in geom[0]:
                    points.append([float(point_cnt), float(feature.id()),
                        vertex.x(), vertex.y()])
                    if addToRefVertices:
                        reference_vertex_indices.append(point_cnt)
                    point_cnt += 1

            feature_cnt += 1

        points_arr = numpy.array(points, dtype=float)
        del points
        
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

        #maxNeighborCount = point_cnt * (point_cnt-1) / 2 # all zones selected
        maxNeighborCount = point_cnt * len(reference_vertex_indices)

        neighbor_cnt = 0
        neighbors = numpy.ones((maxNeighborCount, 
            ANALYSIS_TABLE_COLUMN_COUNT), dtype=float) * numpy.nan

        # all zones selected
        # outer loop: xrange(points_arr.shape[0])
        # inner loop: xrange(reference_point_idx+1, points_arr.shape[0])
        for reference_point_idx in reference_vertex_indices:
            for test_point_idx in xrange(points_arr.shape[0]):

                # skip, if same point or points are in same polygon
                if reference_point_idx == test_point_idx or \
                    points_arr[reference_point_idx, 1] == points_arr[test_point_idx, 1]:
                    continue

                # get distance
                distArea = QgsDistanceArea()

                reference_point = QgsPoint(
                    points_arr[reference_point_idx, 2], 
                    points_arr[reference_point_idx, 3])
                test_point = QgsPoint(points_arr[test_point_idx, 2], 
                    points_arr[test_point_idx, 3])

                distance = float(distArea.measureLine(reference_point, 
                    test_point))

                # if points are the same or distance is greater than the margin, ignore
                if reference_point == test_point or \
                    distance > self.min_distance:
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
 
                # add point pair to analysis layer
                if test_point_idx == 0:
                    pra.addFeatures([self._new_point_feature(reference_point)])
                pra.addFeatures([self._new_point_feature(test_point)])

                neighbor_cnt += 1

        del points_arr

        # reshape array
        neighbors_trunc = neighbors[0:neighbor_cnt, :]

        # sort array (distance)
        dist_indices = numpy.argsort(neighbors_trunc[:, 0], axis=0)

        neighbors_trunc = neighbors_trunc[dist_indices.T]

        # write to table
        self._display_table(neighbors_trunc)

    def _compute_distance_matrix(self, zones_shapely):
        """Compute distance matrix for zone polygons, using Shapely
        distance function."""
        dim = len(zones_shapely)
        self.distance_matrix = numpy.ones((dim, dim), dtype=float) * numpy.nan

        for curr_ref_idx in xrange(dim):
            ref_zone = zones_shapely[curr_ref_idx]

            for curr_test_idx in xrange(curr_ref_idx+1, dim):
                test_zone = zones_shapely[curr_test_idx]
                self.distance_matrix[curr_ref_idx, curr_test_idx] = \
                    ref_zone.distance(test_zone)

    def _get_distance(self, ref_idx, test_idx):
        if ref_idx == test_idx:
            return 0.0
        elif ref_idx < test_idx:
            return self.distance_matrix[ref_idx, test_idx]
        else:
            return self.distance_matrix[test_idx, ref_idx]

    def _get_distance_list(self, zone_idx):
        distances = [self._get_distance(zone_idx, idx) for idx in xrange(
            self.distance_matrix.shape[0])]
        return distances

    def _get_closest_zone_indices(self, distances):
        """distances is a list."""
        return numpy.argsort(numpy.array(distances, dtype=float))
            
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
                elif col == 0:
                    # first column with distances, these can be << 1
                    display_str = "%.6f" % neighbors_trunc[row, col]
                else:
                    display_str = "%.3f" % neighbors_trunc[row, col]

                self.table.setItem(row, col, QTableWidgetItem(
                    QString(display_str)))

    def _replaceAnalysisLayer(self):
        """Create new point layer for sliver analysis."""

        # remove old analysis layer from registry
        # TODO(fab): does not work
        if self.analysis_layer is not None:
            QgsMapLayerRegistry.instance().removeMapLayer(SLIVER_ANALYSIS_LAYER_ID)

        # init empty point layer in memory
        self.analysis_layer = QgsVectorLayer("Point", SLIVER_ANALYSIS_LAYER_ID, 
            "memory")
        QgsMapLayerRegistry.instance().addMapLayer(self.analysis_layer)

    def _new_point_feature(self, point):
        f = QgsFeature()
        f.setGeometry(QgsGeometry.fromPoint(point))
        return f

    def _new_point_feature_from_coord(self, lon, lat):
        point = QgsPoint(lon, lat)
        return self._new_point_feature(point)

