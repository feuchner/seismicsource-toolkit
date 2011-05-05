# -*- coding: utf-8 -*-
"""
SHARE Seismic Source Toolkit

Wrappers for Roger Musson's AtticIvy program.

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

import os
import shutil
import stat
import subprocess
import tempfile

from PyQt4.QtCore import *
from PyQt4.QtGui import *

from qgis.core import *

from mt_seismicsource import features
from mt_seismicsource import utils

ATTICIVY_MMIN = 3.5

# full path of AtticIvy executable
ATTICIVY_EXECUTABLE = os.path.join(os.path.dirname(os.path.dirname(__file__)),
    'code/AtticIvy/AtticIvy')
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

def assignActivityAtticIvy(provider, catalog):
    """Compute activity with Roger Musson's AtticIvy code and assign a and
    b values to each area source zone.

    Input:
        provider    QGis layer provider for zone features
        catalog     earthquake catalog as QuakePy object
    """


    # get attribute indexes
    provider.select()
    attribute_map = utils.getAttributeIndex(provider, 
        features.AREA_SOURCE_ATTRIBUTES_AB_RM, create=True)
    #QMessageBox.information(None, "Attributes", "%s" % attribute_map)

    provider.rewind()
    activity = computeActivityAtticIvy(provider, catalog)
    QMessageBox.information(None, "Activity", "%s" % activity)

    provider.rewind()
    for zone_idx, zone in utils.walkValidPolygonFeatures(provider):
        for attr_idx, attr_dict in enumerate(
            features.AREA_SOURCE_ATTRIBUTES_AB_RM):
            (curr_idx, curr_type) = attribute_map[attr_dict['name']]
            try:
                zone[curr_idx] = QVariant(activity[zone_idx][attr_idx])
            except Exception:
                error_str = "curr_idx: %s, zone_idx: %s, attr_idx: %s" % (
                    curr_idx, zone_idx, attr_idx)
                raise RuntimeError, error_str

def computeActivityAtticIvy(zones, catalog, Mmin=ATTICIVY_MMIN):
    """Computes a-and b values using Roger Musson's AtticIvy code for
    a set of source zone polygons.
    
    Input: 
        zones       QGis layer provider for zone features
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
    exec_file = os.path.basename(ATTICIVY_EXECUTABLE)

    # copy executable to temp dir, set executable permissions
    shutil.copy(ATTICIVY_EXECUTABLE, temp_dir)
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
    #shutil.rmtree(temp_dir)

    return activity_list

def writeZones2AtticIvy(zones, path, Mmin):
    """Write AtticIvy zone file.

    Input:
        zones   QGis layer provider for zone features
    """

    # open file for writing
    with open(path, 'w') as fh:

        # write header
        fh.write('Mmin.......:%3.1f\n' % ATTICIVY_MMIN)
        fh.write('# zones....:%3i\n' % utils.featureCount(zones, 
            checkGeometry=True))
        
        # loop over zones
        for curr_zone_idx, curr_zone in enumerate(zones):

            # get geometry
            vertices = utils.verticesOuterFromQGSPolygon(curr_zone)
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
