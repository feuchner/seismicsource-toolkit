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

BACKGROUND_DIR = 'background_zones'
BACKGROUND_ZONE_FILE = 'Musson-Background-2011-04-27.dat'
BACKGROUND_COMPLETENESS_FILE = 'Musson-Background-2011-04-27.csv'

TEMP_FILENAME = 'background-zones.shp'

CSV_DELIMITER = ','
CSV_QUOTECHAR = '"'

COMPLETENESS_REF_MAGNITUDES = [4.0, 4.5, 5.0, 5.5, 6.0]

# column (count starts with one) in CSV file at which completeness 
# values (years) start
START_COL_COMPLETENESS = 4

def loadBackgroundZoneLayer(cls):
    """Load layer of background zones with completeness history and
    Mmax from ASCII files. 
    """
    background_zone_path = os.path.join(layers.DATA_DIR, BACKGROUND_DIR, 
        BACKGROUND_ZONE_FILE)

    if not os.path.isfile(background_zone_path):
        utils.warning_box_missing_layer_file(background_zone_path)
        return

    background_completeness_path = os.path.join(layers.DATA_DIR, 
        BACKGROUND_DIR, BACKGROUND_COMPLETENESS_FILE)

    if not os.path.isfile(background_completeness_path):
        utils.warning_box_missing_layer_file(background_completeness_path)
        return

    # read data dicts from files
    background_completeness = readBackgroundCompleteness(
        background_completeness_path)
    background_zones = readBackgroundZones(background_zone_path)
   
    # PostGIS SRID 4326 is allocated for WGS84
    crs = QgsCoordinateReferenceSystem(4326, 
        QgsCoordinateReferenceSystem.PostgisCrsId)

    # create layer
    layer = QgsVectorLayer("Polygon", "Background Zones", "memory")
    layer.setCrs(crs) 
    pr = layer.dataProvider()

    # add attributes
    # - ID, Description, no of EQs, Mmax, completeness magnitude history
    pr.addAttributes([QgsField("ID", QVariant.String),
                      QgsField("descr", QVariant.String),
                      QgsField("eqcount", QVariant.Int),
                      QgsField("mmax", QVariant.Double),
                      QgsField("mcdist", QVariant.String)])

    # add zones as features
    for zone_id, zone in background_zones.items():

        f = QgsFeature()

        poly = [QgsPoint(x, y) for (x, y) in zone['coord']]
        f.setGeometry(QgsGeometry.fromPolygon([poly]))
        
        f[0] = QVariant(zone_id)
        f[1] = QVariant(background_completeness[zone_id]['descr'])
        f[2] = QVariant(background_completeness[zone_id]['eqcount'])
        f[3] = QVariant(zone['mmax'])
        f[4] = QVariant(background_completeness[zone_id]['mcdist'])

        pr.addFeatures([f])

    # update layer's extent when new features have been added
    # because change of extent in provider is not 
    # propagated to the layer
    layer.updateExtents()
    QgsMapLayerRegistry.instance().addMapLayer(layer)

    utils.writeLayerToShapefile(layer, os.path.join(layers.DATA_DIR, 
        BACKGROUND_DIR, TEMP_FILENAME), crs)

    return layer

def readBackgroundCompleteness(path):
    """Load completeness history for background zones from CSV file.

    Output:
        ID
        descr
        eqcount
        mcdist
    """

    completeness = {}

    # open file for reading
    with open(path, 'r') as fh:
        reader = csv.reader(fh, delimiter=CSV_DELIMITER, 
            quotechar=CSV_QUOTECHAR)

        # over lines (= events) in ZMAP input stream
        for line_ctr, line in enumerate(reader):

            # skip first header line
            if line_ctr == 0:
                continue
            
            zone_id = line[0].strip()
            zone_descr = line[1].strip()
            zone_eqcount = int(line[2].strip())

            # max. number of (Mc, year) pairs
            mc_pair_count = len(line) - START_COL_COMPLETENESS + 1
            zone_mchist = ""
            for idx in xrange(mc_pair_count):
                curr_year = line[START_COL_COMPLETENESS - 1 + idx]
                if len(curr_year.strip()) > 0:
                    zone_mchist = "%s %s %s" % (zone_mchist, 
                        COMPLETENESS_REF_MAGNITUDES[idx], curr_year.strip())
                else:
                    break

            completeness[zone_id] = {'descr': zone_descr,  
                'eqcount': zone_eqcount, 'mcdist': zone_mchist.lstrip()}

    return completeness

def readBackgroundZones(path):
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
                    dataLineMode = True

            elif dataLineMode is True:

                line_arr = line.strip().split()

                zones[zone_id.strip()] = {'coord': coord,
                    'mmax': float(line_arr[-1].strip())}

                dataLineMode = False
                zoneStartMode = True
        
        if zone_idx != zone_count:
            QMessageBox.warning(None, "Zone count", 
                "Zone count mismatch in zone file: found %s, expected %s" % (
                    zone_idx, zone_count))

    return zones