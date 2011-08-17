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

import numpy
import os
import shutil
import stat
import subprocess
import tempfile

from PyQt4.QtCore import *
from PyQt4.QtGui import *

from qgis.core import *

import QPCatalog

from mt_seismicsource import features
from mt_seismicsource import utils
from mt_seismicsource.layers import eqcatalog

ATTICIVY_MMIN = 3.5

# full path of AtticIvy executable
ATTICIVY_EXECUTABLE = os.path.join(os.path.dirname(os.path.dirname(__file__)),
    'code/AtticIvy/AtticIvy')
ATTICIVY_ZONE_FILE = 'AtticIvy-Zone.inp'
ATTICIVY_CATALOG_FILE = 'AtticIvy-Catalog.dat'

# AtticIvy output file name convention:
# remove '.inp' extension of zone file name and add '_out.txt'
ATTICIVY_RESULT_FILE = '%s_out.txt' % ATTICIVY_ZONE_FILE[0:-4]

# third commandline parameter: number of bootstrap iterations
# 0: use default (1000 iterations)
ATTICIVY_BOOTSTRAP_ITERATIONS = 0

ATTICIVY_EMPTY_ZONE_MMAX = """# Mmax.....: 0
# Mmax.....: 0
"""

ATTICIVY_MISSING_ZONE_PARAMETERS_MMAX = """# Mmax.....:  2
 5.5   0.5
 6.5   0.5
"""

ATTICIVY_MISSING_ZONE_PARAMETERS_MCDIST = """# Periods..:  4
 3.5 1970
 4.0 1750
 4.5 1700
 6.5 1300
"""

ATTICIVY_MISSING_ZONE_PARAMETERS_PRIORS = """A prior and weight
 0.0   0.0
B prior and weight
 1.0  50.0
"""

ZONE_ATTRIBUTES = (features.AREA_SOURCE_ATTR_MMAX,
    features.AREA_SOURCE_ATTR_MCDIST)

def assignActivityAtticIvy(layer, catalog, mmin=ATTICIVY_MMIN,
    mindepth=eqcatalog.CUT_DEPTH_MIN, maxdepth=eqcatalog.CUT_DEPTH_MAX):
    """Compute activity with Roger Musson's AtticIvy code and assign a and
    b values to each area source zone.

    Input:
        layer       QGis layer with area zone features
        catalog     earthquake catalog as QuakePy object
    """

    # get attribute indexes
    provider = layer.dataProvider()
    attribute_map = utils.getAttributeIndex(provider, 
        features.AREA_SOURCE_ATTRIBUTES_AB_RM, create=True)

    zone_attribute_map = utils.getAttributeIndex(provider, ZONE_ATTRIBUTES, 
        create=False)

    mmax_name = features.AREA_SOURCE_ATTR_MMAX['name']    
    mmax_idx = zone_attribute_map[mmax_name][0]
    mcdist_name = features.AREA_SOURCE_ATTR_MCDIST['name']
    mcdist_idx = zone_attribute_map[mcdist_name][0]

    fts = layer.selectedFeatures()
    polygons, vertices = utils.polygonsQGS2Shapely(fts)

    # get mmax and mcdist from layer zone attributes
    mmax = []
    mcdist = []
    for zone in fts:
        mmax.append(float(zone[mmax_idx].toDouble()[0]))
        mcdist.append(str(zone[mcdist_idx].toString()))

    activity = computeActivityAtticIvy(polygons, mmax, mcdist, catalog, mmin, 
        mindepth, maxdepth)

    # assemble value dict
    values = {}

    # loop over QGis features
    for zone_idx, zone in enumerate(fts):
        attributes = {}
        skipZone = False
        for attr_idx, attr_dict in enumerate(
            features.AREA_SOURCE_ATTRIBUTES_AB_RM):
            (curr_idx, curr_type) = attribute_map[attr_dict['name']]
            try:
                attributes[curr_idx] = QVariant(activity[zone_idx][attr_idx])
            except Exception, e:
                skipZone = True
                break

        if skipZone is False:
            values[zone.id()] = attributes

    try:
        provider.changeAttributeValues(values)
    except Exception, e:
        error_str = "cannot update attribute values, %s" % (e)
        raise RuntimeError, error_str

    layer.commitChanges()

def computeActivityAtticIvy(polygons, mmax, mcdist, catalog, 
    mmin=ATTICIVY_MMIN, mindepth=eqcatalog.CUT_DEPTH_MIN,
    maxdepth=eqcatalog.CUT_DEPTH_MAX):
    """Computes a-and b values using Roger Musson's AtticIvy code for
    a set of source zone polygons.
    
    Input: 
        polygons        list of Shapely polygons for input zones
        mmax            list of mmax values
        mcdist          list of mcdist strings
        catalog         earthquake catalog as QuakePy object
        mmin            minimum magnitude used for AtticIvy computation

    Output: 
        list of (a, b, ab-matrix-string) triples
    """
    
    # create temp dir for computation
    temp_dir_base = os.path.dirname(__file__)
    temp_dir = tempfile.mkdtemp(dir=temp_dir_base)

    # NOTE: cannot use full file names, since they can be only 30 chars long
    # write zone data to temp file in AtticIvy format
    zone_file_path = os.path.join(temp_dir, ATTICIVY_ZONE_FILE)
    
    writeZones2AtticIvy(zone_file_path, polygons, mmax, mcdist, mmin)

    # do depth filtering on catalog
    cat_cut = QPCatalog.QPCatalog()
    cat_cut.merge(catalog)
    cat_cut.cut(mindepth=mindepth, maxdepth=maxdepth)
    
    # write catalog to temp file in AtticIvy format
    catalog_file_path = os.path.join(temp_dir, ATTICIVY_CATALOG_FILE)
    cat_cut.exportAtticIvy(catalog_file_path)

    # start AtticIvy computation (subprocess)
    exec_file = os.path.basename(ATTICIVY_EXECUTABLE)

    # copy executable to temp dir
    shutil.copy(ATTICIVY_EXECUTABLE, temp_dir)

    retcode = subprocess.call(["./%s" % exec_file, ATTICIVY_ZONE_FILE, 
        ATTICIVY_CATALOG_FILE, str(ATTICIVY_BOOTSTRAP_ITERATIONS)], 
        cwd=temp_dir)
    
    if retcode != 0:
        QMessageBox.warning(None, "AtticIvy Error", 
            "AtticIvy return value: %s" % retcode)

    # read results from AtticIvy output file
    result_file_path = os.path.join(temp_dir, ATTICIVY_RESULT_FILE)
    activity_list = activityFromAtticIvy(result_file_path)

    # remove temp file directory
    #shutil.rmtree(temp_dir)

    return activity_list

def writeZones2AtticIvy(path, polygons, mmax, mcdist, mmin=ATTICIVY_MMIN):
    """Write AtticIvy zone file.

    Input:
        path            filename to write AtticIvy zone file to
        polygons        list of Shapely polygons for input zones
        mmax            list of mmax values
        mcdist          list of mcdist strings
        mmin            minimum magnitude used for AtticIvy computation

    """

    # open file for writing
    with open(path, 'w') as fh:

        # write header
        fh.write('Mmin.......:%3.1f\n' % mmin)
        fh.write('# zones....:%3i\n' % len(polygons))
        
        # loop over zones
        for curr_zone_idx, curr_zone in enumerate(polygons):

            # get geometry
            vertices = list(curr_zone.exterior.coords)
            if len(vertices) < 4:
                continue
            
            fh.write('%04i , %s\n' % (curr_zone_idx, len(vertices)-1))
            for vertex in vertices[0:-1]:
                fh.write('%s , %s\n' % (vertex[1], vertex[0]))

            try:
                # add mmax from area source zone
                mmax_str = "# Mmax.....:  1\n %.1f   1.0\n" % (
                    mmax[curr_zone_idx])
                fh.write(mmax_str)

                # assume that mcdist is also valid if mmax is valid
                mcdist = mcdist[curr_zone_idx]
                mcdist_arr = mcdist.strip().split()
                mcdist_mag = mcdist_arr[::2]
                mcdist_year = mcdist_arr[1::2]
                mcdist_entries = len(mcdist_arr)/2

                mcdist_str = "# Periods..:%3i\n" % mcdist_entries
                for idx in xrange(mcdist_entries):
                    mcdist_str += " %.1f %s\n" % (
                        float(mcdist_mag[idx].strip()), 
                        mcdist_year[idx].strip())
                fh.write(mcdist_str)

                # a/b priors: default setting
                fh.write(ATTICIVY_MISSING_ZONE_PARAMETERS_PRIORS)

            except Exception:

                # if mmax is not set properly, write special lines for zone
                # and proceed to next zone
                fh.write(ATTICIVY_EMPTY_ZONE_MMAX)
                continue

def activityFromAtticIvy(path):
    """Read output from AtticIvy program. Returns list of 
    [a, b, activity_string] value triples.
    a: a value
    b: b value
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
                (weight, a_value, b_value) = line.strip().split()
                zone_data.append([float(a_value), float(b_value)])

                # append new line to zone data string
                zone_data_string = "%s %s %s %s" % (
                    zone_data_string, weight, a_value, b_value)
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
    
def activity2aValue(A_value, b_value, m_min=ATTICIVY_MMIN):
    """The resulting activity parameter A from AtticIvy is the 
    non-logarithmic annual occurrence at M=Mmin (default M=3.5). This 
    function converts this to log10 of the annual occurrence at 
    M=0 (the usual a parameter).
    
    a = log10(A) + b * Mmin
    
    Input:
        A_value     list of AtticIvy A parameters
        b_value     list of AtticIvy b parameters
        m_min       Mmin for which AtticIvy activity has been computed
    """
    A = numpy.array(A_value)
    b = numpy.array(b_value)
    
    a = numpy.log10(A) + b * m_min
    
    return a
