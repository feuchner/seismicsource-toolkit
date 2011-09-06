# -*- coding: utf-8 -*-
"""
SHARE Seismic Source Toolkit

Loader for background zone layer.

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

import csv
import os

from PyQt4.QtCore import *
from PyQt4.QtGui import *

from qgis.core import *

import QPCatalog

from mt_seismicsource import layers
from mt_seismicsource import utils

from mt_seismicsource.layers import render

BACKGROUND_DIR = 'background_zones'
BACKGROUND_ZONES_MMAX_FILE = 'background-zones-mmax.dat'
BACKGROUND_ZONES_COMPLETENESS_FILE = 'background-zones-completeness.dat'

TEMP_FILENAME = 'background-zones.shp'

def loadBackgroundZoneLayer(cls):
    """Load layer of background zones with completeness history and
    Mmax from ASCII files. 
    """
    background_mmax_path = os.path.join(layers.DATA_DIR, BACKGROUND_DIR, 
        BACKGROUND_ZONES_MMAX_FILE)

    if not os.path.isfile(background_mmax_path):
        utils.warning_missing_layer_file(background_mmax_path)
        return None

    background_completeness_path = os.path.join(layers.DATA_DIR, 
        BACKGROUND_DIR, BACKGROUND_ZONES_COMPLETENESS_FILE)

    if not os.path.isfile(background_completeness_path):
        utils.warning_missing_layer_file(background_completeness_path)
        return None

    save_path = os.path.join(layers.DATA_DIR, BACKGROUND_DIR, TEMP_FILENAME)
    layer = loadBackgroundZoneFromFile(background_mmax_path, 
        background_completeness_path, save_path, layer2file=False)

    # update layer's extent when new features have been added
    # because change of extent in provider is not 
    # propagated to the layer
    layer.updateExtents()
    QgsMapLayerRegistry.instance().addMapLayer(layer)
    
    # set layer as not visible
    cls.legend.setLayerVisible(layer, False)
    
    # set layer visibility
    cls.legend.setLayerVisible(layer, 
        render.BACKGROUND_ZONE_LAYER_STYLE['visible'])
    
    return layer

def loadBackgroundZoneFromFile(background_mmax_path, 
    background_completeness_path, filename_out=None, layer2file=False,
    ui_mode=True):
    """Load layer of background zones with completeness history and
    Mmax from ASCII files, independent of QGis UI. 
    """
    
    # read data dicts from files (coordinates from mmax file)
    background_mmax = readBackgroundMmax(background_mmax_path, ui_mode=ui_mode)
    #QMessageBox.information(None, "Mmax", "%s" % background_mmax)

    background_completeness = readBackgroundCompleteness(
        background_completeness_path, ui_mode=ui_mode)
    #QMessageBox.information(None, "Mc", "%s" % background_completeness)
   
    # PostGIS SRID 4326 is allocated for WGS84
    crs = QgsCoordinateReferenceSystem(4326, 
        QgsCoordinateReferenceSystem.PostgisCrsId)

    # create layer
    layer = QgsVectorLayer("Polygon", "Background Zones", "memory")
    layer.setCrs(crs) 
    pr = layer.dataProvider()

    # add attributes
    # - ID, Mmax, completeness magnitude history
    pr.addAttributes([QgsField("ID", QVariant.String),
                      QgsField("mmax", QVariant.Double),
                      QgsField("mcdist", QVariant.String)])

    # add zones as features
    for zone_id, zone in background_mmax.items():

        f = QgsFeature()

        poly = [QgsPoint(x, y) for (x, y) in zone['coord']]
        f.setGeometry(QgsGeometry.fromPolygon([poly]))
        
        f[0] = QVariant(zone_id)
        f[1] = QVariant(zone['mmax'])
        f[2] = QVariant(background_completeness[zone_id]['mcdist'])

        pr.addFeatures([f])

    # write memory layer to disk (as a Shapefile)
    if layer2file is True:
        utils.writeLayerToShapefile(layer, filename_out, crs, ui_mode=ui_mode)

    return layer

def readBackgroundMmax(path, ui_mode=True):
    """Load geometry and Mmax of background zones from ASCII file.

    Output:
        ID
        coord
        mmax
    """

    fileStartMode = True
    zones = {}

    # open file for reading
    with open(path, 'r') as fh:

        zoneStartMode = False
        coordLineMode = False
        dataLineStartMode = False
        dataLineMode = False

        # loop over zones
        for line in fh:
        
            # ignore blank lines
            if len(line.strip()) == 0:
                continue

            elif fileStartMode is True:
                zone_count = int(line.strip())
                zone_idx = 0
                fileStartMode = False
                zoneStartMode = True

            elif zoneStartMode is True:

                zone_idx += 1
                line_arr = line.strip().split(',')
                zone_id = line_arr[0].strip()
                coord_count = int(line_arr[1])

                coord = []
                coord_idx = 0
                zoneStartMode = False
                coordLineMode = True

            elif coordLineMode is True:

                coord_idx += 1
                line_arr = line.strip().split(',')

                # zone file has coords in lat, lon order
                coord.append((float(line_arr[1].strip()), 
                    float(line_arr[0].strip())))

                if coord_idx == coord_count:
                
                    # copy first coord pair
                    coord.append(coord[-1])
                    coordLineMode = False
                    dataLineStartMode = True

            elif dataLineStartMode is True:

                # line contains no. of Mmax values and weights
                # it's always 1, so safe to ignore
                dataLineStartMode = False
                dataLineMode = True
        
            elif dataLineMode is True:

                line_arr = line.strip().split()

                # line has Mmax and weight, use only Mmax
                zones[zone_id] = {'coord': coord,
                    'mmax': float(line_arr[0].strip())}

                dataLineMode = False
                zoneStartMode = True

    if zone_idx != zone_count:
        error_msg = \
            "Zone count mismatch in zone file %s: found %s, expected %s" % (
                path, zone_idx, zone_count)
        if ui_mode is True:
            QMessageBox.warning(None, "Zone count", error_msg)
        else:
            print error_msg
            
    return zones

def readBackgroundCompleteness(path, ui_mode=True):
    """Load completeness history for background zones from CSV file.

    Output:
        ID
        mcdist
    """

    fileStartMode = True
    completeness = {}

    # open file for reading
    with open(path, 'r') as fh:

        zoneStartMode = False
        coordLineMode = False
        dataLineStartMode = False
        dataLineMode = False

        # loop over zones
        for line in fh:
        
            # ignore blank lines
            if len(line.strip()) == 0:
                continue

            elif fileStartMode is True:
                zone_count = int(line.strip())
                zone_idx = 0
                fileStartMode = False
                zoneStartMode = True

            elif zoneStartMode is True:

                zone_idx += 1
                line_arr = line.strip().split(',')
                zone_id = line_arr[0].strip()
                coord_count = int(line_arr[1])

                coord_idx = 0
                zoneStartMode = False
                coordLineMode = True

            elif coordLineMode is True:

                coord_idx += 1

                if coord_idx == coord_count:
                    coordLineMode = False
                    dataLineStartMode = True

            elif dataLineStartMode is True:

                mc_count = int(line.strip())
                mc_idx = 0
                zone_mchist = ""
                dataLineStartMode = False
                dataLineMode = True
        
            elif dataLineMode is True:

                line_arr = line.strip().split()
                mc_idx += 1
                zone_mchist = "%s %s %s" % (zone_mchist, 
                    float(line_arr[0].strip()), int(line_arr[1].strip()))

                if mc_idx == mc_count:
                    completeness[zone_id] = {'mcdist': zone_mchist.lstrip()}
                    dataLineMode = False
                    zoneStartMode = True

    if mc_idx != mc_count:
        error_msg = \
            "Zone count mismatch in zone file %s: found %s, expected %s" % (
                path, mc_idx, mc_count)
        if ui_mode is True:
            QMessageBox.warning(None, "Zone count", error_msg)
        else:
            print error_msg
        
    return completeness
