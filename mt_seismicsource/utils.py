## -*- coding: utf-8 -*-
"""
SHARE Seismic Source Toolkit

This module holds utility functions.

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
import shutil
import stat
import subprocess
import tempfile
import time

from PyQt4.QtCore import *
from PyQt4.QtGui import *

from qgis.core import *

import features

ATTICIVY_MMIN = 3.5
ATTICIVY_EXECUTABLE = 'code/AtticIvy/AtticIvy'
ATTICIVY_ZONE_FILE = 'AtticIvy-Zone.inp'
ATTICIVY_CATALOG_FILE = 'AtticIvy-Catalog.dat'

# AtticIvy output file name convention:
# remove '.inp' extension of zone file name and add '_out.txt'
ATTICIVY_RESULT_FILE = '%s_out.txt' % ATTICIVY_ZONE_FILE[0:-4]

ATTICIVY_MISSING_ZONE_PARAMETERS = """# Mmax.....:  2
 5.5   0.5
 6.5   0.5
# Periods..:  4
 3.5 1970
 4.0 1750
 4.5 1700
 6.5 1300
A prior and weight
 0.0   0.0
B prior and weight
 1.0  50.0
"""

# maximum likelihood a- and b-values, as implemented in ZMAP

def assignActivityMaxLikelihood():
    pass

def computeActivityMaxLikelihood(zones, catalog):
    """Computes a-and b values using the maximum likelihood method for
    a set of source zone polygons.
    
    Input: 
        zones       iterable of polygon features in QGis format
        catalog     earthquake catalog as QuakePy object

    Output: list of (a, b) pairs
    """
    pass

# Roger Musson's AtticIvy

def assignActivityAtticIvy(layer, catalog):
    """Compute activity with Roger Musson's AtticIvy code and assign a and
    b values to each area source zone.

    Input:
        layer       polygon feature layer
        catalog     earthquake catalog as QuakePy object
    """

    provider = layer.dataProvider()
    provider.select()

    if not provider.capabilities() > 7:
        QMessageBox.warning(None, "Cannot add attributes", 
            "Cannot add attributes, code %s" % provider.capabilities())

    layer.blockSignals(True)
    layer.startEditing()
    if not layer.isEditable():
        QMessageBox.warning(None, "Layer not editable", "Layer not editable")

    # layer.pendingFields()

    #vlayer.beginEditCommand("Attribute added")
        #if not vlayer.addAttribute(newField):
            #print "Could not add the new field to the provider."
            #vlayer.destroyEditCommand()
            #if not wasEditing:
                #vlayer.rollBack()
            #return False
        #vlayer.endEditCommand()

    #if not vlayer.dataProvider().capabilities() > 7: # can't add attributes
        #print("Data provider does not support adding attributes: "
                #"Cannot add required geometry fields.")
        #vlayer.rollBack()
        #return False

    #vlayer.select(vlayer.pendingAllAttributesList(), QgsRectangle(), True, False)

    #vlayer.changeAttributeValue(feature.id(), id, attrs[i], False)

    #layer.blockSignals(False)
    #layer.setModified(True, False)

    #if not wasEditing:
        #layer.commitChanges()

    # get attribute indexes
    attribute_map = getAttributeIndex(provider, 
        features.AREA_SOURCE_ATTRIBUTES_AB_RM, create=True)
    activity = computeActivityAtticIvy(provider, catalog)
    for zone_idx, zone in walkValidPolygonFeatures(provider):
        for attr_idx, attr_dict in enumerate(
            features.AREA_SOURCE_ATTRIBUTES_AB_RM):
            (curr_idx, curr_type) = attribute_map[attr_dict['name']]
            try:
                zone[curr_idx] = QVariant(activity[zone_idx][attr_idx])
            except Exception:
                error_str = "curr_idx: %s, zone_idx: %s, attr_idx: %s" % (
                    curr_idx, zone_idx, attr_idx)
                raise RuntimeError, error_str

    layer.blockSignals(False)
    layer.setModified(True, False)
    layer.commitChanges()

    QMessageBox.information(None, "Activity", "%s" % activity)

def computeActivityAtticIvy(zones, catalog, Mmin=ATTICIVY_MMIN):
    """Computes a-and b values using Roger Musson's AtticIvy code for
    a set of source zone polygons.
    
    Input: 
        zones       iterable of zone features in QGis format 
        catalog     earthquake catalog as QuakePy object

    Output: 
        list of (a, b) pairs
    """
    
    # create temp dir for computation
    temp_dir_base = os.path.dirname(__file__)
    temp_dir = tempfile.mkdtemp(dir=temp_dir_base)

    # NOTE: cannot use full file names, since they can be only 30 chars long
    # write zone data to temp file in AtticIvy format
    zone_file_path = os.path.join(temp_dir, ATTICIVY_ZONE_FILE)
    writeZones2AtticIvy(zones, zone_file_path, Mmin)

    # write catalog to temp file in AtticIvy format
    catalog_file_path = os.path.join(temp_dir, ATTICIVY_CATALOG_FILE)
    catalog.exportAtticIvy(catalog_file_path)

    # start AtticIvy computation (subprocess)
    exec_path_full = os.path.join(os.path.dirname(__file__), 
        ATTICIVY_EXECUTABLE)
    exec_file = os.path.basename(exec_path_full)

    # copy executable to temp dir, set executable permissions
    shutil.copy(exec_path_full, temp_dir)
    os.chmod(os.path.join(temp_dir, exec_file), stat.S_IXUSR)

    retcode = subprocess.call([exec_file, ATTICIVY_ZONE_FILE, 
        ATTICIVY_CATALOG_FILE], cwd=temp_dir)
    
    if retcode != 0:
        QMessageBox.warning(None, "AtticIvy Error", 
            "AtticIvy return value: %s" % retcode)

    # read results from AtticIvy output file
    result_file_path = os.path.join(temp_dir, ATTICIVY_RESULT_FILE)
    activity_list = activityFromAtticIvy(result_file_path)

    # remove temp file directory
    shutil.rmtree(temp_dir)

    return activity_list

def writeZones2AtticIvy(zones, path, Mmin):
    """Write AtticIvy zone file.

    Input:
        zones   Iterable of polygon features in QGis format
    """

    # open file for writing
    with open(path, 'w') as fh:

        # write header
        fh.write('Mmin.......:%3.1f\n' % ATTICIVY_MMIN)
        fh.write('# zones....:%3i\n' % featureCount(zones, 
            checkGeometry=True))
        
        # loop over zones
        for curr_zone_idx, curr_zone in enumerate(zones):

            # get geometry
            vertices = verticesOuterFromQGSPolygon(curr_zone)
            if vertices is None:
                continue
            
            fh.write('%04i , %s\n' % (curr_zone_idx, len(vertices)))
            for vertex in vertices:
                fh.write('%s , %s\n' % (vertex[1], vertex[0]))

            # TODO(fab): use real parameters
            fh.write(ATTICIVY_MISSING_ZONE_PARAMETERS)

def activityFromAtticIvy(path):
    """Read output from AtticIvy program. Returns list of 
    [a, b, activity_string] value triples.
    a: activity
    b: b-value
    activity_string: string of all [weight, a, b] triples per zone, in a row,
                     separated by white space
    """
    result_values = []
    with open(path, 'r') as fh:

        zoneStartMode = True
        dataLengthMode = False
        dataLineMode = False

        # loop over zones
        for line in fh:
        
            # ignore blank lines
            if len(line.strip()) == 0:
                continue

            elif zoneStartMode is True:
                # reading zone ID from file not required, we rely on 
                # order of zones in file
                zone_data = []
                zone_data_string = ""
                dataLengthMode = True
                zoneStartMode = False

            elif dataLengthMode is True:
                data_line_count = int(line.strip())
                data_line_idx = 0
                dataLineMode = True
                dataLengthMode = False

            elif dataLineMode is True:
                # don't use first value (weight) value from result file
                # second value: a (activity), third value: b
                (weight, activity, b_value) = line.strip().split()
                zone_data.append([float(activity), float(b_value)])

                # append new line to zone data string
                zone_data_string = "%s %s %s %s" % (
                    zone_data_string, weight, activity, b_value)
                data_line_idx += 1

                # all lines read
                if data_line_idx == data_line_count:

                    # get proper (middle) line and append zone data string
                    zone_values = zone_data[data_line_count / 2]
                    zone_values.append(zone_data_string.lstrip())
                    result_values.append(zone_values)
                    
                    zoneStartMode = True
                    dataLineMode = False

    return result_values

# Misc. QGis/Shapely featutes

def featureCount(layer_provider, checkGeometry=False):
    if checkGeometry is False:
        return layer_provider.featureCount()
    else:
        counter = 0
        layer_provider.rewind()
        for feature in layer_provider:
            if verticesOuterFromQGSPolygon(feature) is not None:
                counter += 1
        return counter

def walkValidPolygonFeatures(provider):
    """Generator that yields index and feature for polygon layer, skips
    features with invalid geometry.
    """
    feature_idx = 0
    provider.rewind()
    for feature in provider:
        if verticesOuterFromQGSPolygon(feature) is None:
            continue
        else:
            feature_idx += 1
            yield(feature_idx-1, feature)

def verticesOuterFromQGSPolygon(feature):
    geom = feature.geometry().asPolygon()
    if len(geom) == 0:
        return None
    else:
        # skip last vertex is it's a duplicate of first one
        vertices = [(x.x(), x.y()) for x in geom[0][0:-1]]
        if len(vertices) == 0:
            return None
    return vertices

def polygonsQGS2Shapely(polygons, getVertices=False):
    """Convert feature geometry of QGis polygon iterable to list of Shapely
    polygons. Polygons can be a list of QGis features, or a data provider."""

    polygons_shapely = []
    vertices_shapely = []

    for feature in polygons:

        vertices = utils.verticesOuterFromQGSPolygon(feature)
        if vertices is None:
            continue

        shapely_polygon = shapely.geometry.Polygon(vertices)
        polygons_shapely.append(shapely_polygon)

        if getVertices is True:
            for vertex in vertices:
                vertices_shapely.append(shapely.geometry.Point(vertex))

    return (polygons_shapely, vertices_shapely)

def getSelectedRefZoneIndices(reference_zones):
    """Get indices of selected zones from list of all source zones.
    reference_zones is list of selected QGis features."""
    return []

def getAttributeIndex(provider, attributes, create=True):
    """Get indices of attributes in QGis layer. 

    Input:
        provider    layer provider
        attributes  iterable of dicts with attributes 'name', 'type', e.g.
                    (('name': 'a_rm', 'type': QVariant.Double), 
                     ('name': 'b_rm', 'type': QVariant.Double)).
        create      if True, missing attributes will be added to the layer.

    Output:
        return value is a dictionary with attribute name as keys, and 
        (index, type) pais as values
    """
    
    attribute_map = {}

    for attr_dict in attributes:
        attr_index = provider.fieldNameIndex(attr_dict['name'])

        # if attribute not existing (return value -1), create it,
        # if create is True
        if attr_index == -1 and create is True:
            provider.addAttributes([QgsField(attr_dict['name'], 
                attr_dict['type'])])
            attr_index = provider.fieldNameIndex(attr_dict['name'])

        attribute_map[attr_dict['name']] = (attr_index, attr_dict['type'])

    return attribute_map


