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
ATTICIVY_ZONE_FILE_EXTENSION = 'inp'
ATTICIVY_RESULT_FILE = '%s_out.txt' % (
    ATTICIVY_ZONE_FILE[0:-(len(ATTICIVY_ZONE_FILE_EXTENSION)+1)])

# third commandline parameter: number of bootstrap iterations
# 0: use default (1000 iterations)
ATTICIVY_BOOTSTRAP_ITERATIONS = 0

ATTICIVY_MISSING_ZONE_PARAMETERS_PRIORS = """A prior and weight
 0.0   0.0
B prior and weight
 1.0  50.0
"""

ATTICIVY_A_IDX = 0
ATTICIVY_B_IDX = 1
ATTICIVY_WEIGHT_IDX = 2
ATTICIVY_ACT_A_IDX = 3
ATTICIVY_ACT_B_IDX = 4

ZONE_ATTRIBUTES = (features.AREA_SOURCE_ATTR_MMAX,
    features.AREA_SOURCE_ATTR_MCDIST)

def assignActivityAtticIvy(layer, catalog, mmin=ATTICIVY_MMIN,
    mindepth=eqcatalog.CUT_DEPTH_MIN, maxdepth=eqcatalog.CUT_DEPTH_MAX,
    ui_mode=True):
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
    for zone_idx, zone in enumerate(fts):
        
        try:
            mmax_value = float(zone[mmax_idx].toDouble()[0])
        except KeyError:
            mmax_value = None
            error_msg = "AtticIvy: no Mmax value in zone %s" % zone_idx
            if ui_mode is True:
                QMessageBox.warning(None, "AtticIvy Error", error_msg)
            else:
                print error_msg
            
        try:
            mcdist_value = str(zone[mcdist_idx].toString())
        except KeyError:
            mcdist_value = None
            error_msg = "AtticIvy: no Mc value in zone %s" % zone_idx
            if ui_mode is True:
                QMessageBox.warning(None, "AtticIvy Error", error_msg)
            else:
                print error_msg
        
        mmax.append(mmax_value)
        mcdist.append(mcdist_value)

    activity = computeActivityAtticIvy(polygons, mmax, mcdist, catalog, mmin, 
        mindepth, maxdepth, ui_mode=ui_mode)

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
    maxdepth=eqcatalog.CUT_DEPTH_MAX, ui_mode=True):
    """Computes a-and b values using Roger Musson's AtticIvy code for
    a set of source zone polygons.
    
    Input: 
        polygons        list of Shapely polygons for input zones
        mmax            list of mmax values
        mcdist          list of mcdist strings
        catalog         earthquake catalog as QuakePy object
        mmin            minimum magnitude used for AtticIvy computation

    Output: 
        list of (a, b, act_w, act_a, act_b) triples
    """
    
    # create temp dir for computation
    temp_dir_base = os.path.dirname(__file__)
    temp_dir = tempfile.mkdtemp(dir=temp_dir_base)

    # NOTE: cannot use full file names, since they can be only 30 chars long
    # write zone data to temp file in AtticIvy format
    zone_file_path = os.path.join(temp_dir, ATTICIVY_ZONE_FILE)
    
    # return value is list of all internal zone IDs 
    zone_ids = writeZones2AtticIvy(zone_file_path, polygons, mmax, mcdist, 
        mmin, ui_mode=ui_mode)

    # do depth filtering on catalog
    # don't exclude events with 'NaN' values
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
        error_msg = "AtticIvy Error. Return value: %s" % retcode
        if ui_mode is True:
            QMessageBox.warning(None, "AtticIvy Error", error_msg)
        else:
            print error_msg
            
    # read results from AtticIvy output file
    result_file_path = os.path.join(temp_dir, ATTICIVY_RESULT_FILE)
    activity_result = activityFromAtticIvy(result_file_path)
    
    # expand activity_result to original length with inserted None values
    # for zones that do not have valid data
    activity_list = []
    for curr_zone_id in zone_ids:
        if curr_zone_id in activity_result:
            zone_result = activity_result[curr_zone_id]
        else:
            zone_result = None
        
        activity_list.append(zone_result)

    # remove temp file directory
    #shutil.rmtree(temp_dir)

    return activity_list

def writeZones2AtticIvy(path, polygons, mmax_in, mcdist_in, 
    mmin=ATTICIVY_MMIN, ui_mode=True):
    """Write AtticIvy zone file.

    Input:
        path            filename to write AtticIvy zone file to
        polygons        list of Shapely polygons for input zones
        mmax_in         list of mmax values
        mcdist_in       list of mcdist strings
        mmin            minimum magnitude used for AtticIvy computation

    Output:
        list of internal zone IDs
    """

    zone_ids = []
    
    # open file for writing
    with open(path, 'w') as fh:

        counted_zones = len(polygons)
        body_str = ''

        if len(mmax_in) != counted_zones:
            error_str = "AtticIvy zones: only %s mmax values for "\
                "%s zones" % (len(mmax_in), counted_zones)
            raise RuntimeError, error_str
        
        if len(mcdist_in) != counted_zones:
            error_str = "AtticIvy zones: only %s mcdist values for "\
                "%s zones" % (len(mcdist_in), counted_zones)
            raise RuntimeError, error_str

        # loop over zones
        for curr_zone_idx, curr_zone in enumerate(polygons):

            # get geometry
            vertices = list(curr_zone.exterior.coords)
            if len(vertices) < 4:
                
                if ui_mode is False:
                    error_str = "AtticIvy zones: number of vertices "\
                        "below 4, skipping zone %s" % curr_zone_idx
                    print error_str
                    
                counted_zones -= 1
                continue
            
            zone_id = "%04i" % curr_zone_idx
            zone_ids.append(zone_id)
            
            zone_str = "%s , %s\n" % (zone_id, len(vertices)-1)
            for vertex in vertices[0:-1]:
                zone_str += '%s , %s\n' % (vertex[1], vertex[0])

            skipZone = False
            
            if mmax_in[curr_zone_idx] is None or mcdist_in[curr_zone_idx] is None:
                counted_zones -= 1
                continue
                
            try:
                # add mmax from area source zone
                mmax_str = "# Mmax.....:  1\n %.1f   1.0\n" % (
                    mmax_in[curr_zone_idx])
                zone_str += mmax_str
                
            except Exception, e:
                skipZone = True
                error_msg = "Error writing Mmax data in zone %s\n%s" % (
                    curr_zone_idx, e)
                if ui_mode is True:
                    QMessageBox.warning(None, "AtticIvy Error", error_msg)
                else:
                    print error_msg

            try:
                mcdist = mcdist_in[curr_zone_idx]
                mcdist_arr = mcdist.strip().split()
                mcdist_mag = mcdist_arr[::2]
                mcdist_year = mcdist_arr[1::2]
                mcdist_entries = len(mcdist_arr)/2

                mcdist_str = "# Periods..:%3i\n" % mcdist_entries
                for idx in xrange(mcdist_entries):
                    mcdist_str += " %.1f %s\n" % (
                        float(mcdist_mag[idx].strip()), 
                        mcdist_year[idx].strip())
                zone_str += mcdist_str

            except Exception, e:
                skipZone = True
                error_msg = "Error writing Mc data in zone %s\n%s" % (
                    curr_zone_idx, e)
                if ui_mode is True:
                    QMessageBox.warning(None, "AtticIvy Error", error_msg)
                else:
                    print error_msg

            # largest Mmax must be lower or equal than largest Mc value, 
            # otherwise # skip zone (if this case is not caught here, AtticIvy 
            # will stop at the zone with 'largest mmax not covered' error
            largest_mc = float(mcdist_mag[-1].strip())
            if skipZone is False and largest_mc < mmax_in[curr_zone_idx]:
                skipZone = True
                error_msg = "largest mmax not covered by mcdist, zone %s" % (
                    curr_zone_idx)
                if ui_mode is True:
                    QMessageBox.warning(None, "AtticIvy Error", error_msg)
                else:
                    print error_msg
            
            if skipZone is False:
                # a/b priors: default setting
                zone_str += ATTICIVY_MISSING_ZONE_PARAMETERS_PRIORS
                body_str += zone_str
            else:
                counted_zones -= 1
                continue
                
        header_str = 'Mmin.......:%3.1f\n' % mmin
        header_str += '# zones....:%3i\n' % counted_zones
        fh.write(header_str)
        fh.write(body_str)
        
    return zone_ids
    
def activityFromAtticIvy(path):
    """Read output from AtticIvy program. Returns dict of 
    [a, b, 'act_string_w', 'act_string_a', 'act_string_b'] value 5-tuples 
    with 'internal_id' as key.
    a: best a value
    b: best b value
    act_string_w: string of all weights from result matrix in a row,
                  separated by white space
    act_string_a: string of all a values from result matrix in a row,
                  separated by white space
    act_string_b: string of all b values from result matrix in a row,
                  separated by white space
    internal_id      zone identifier from AtticIvy zone file (note: this is
                     not the zone ID from the original shapefile)
    """
    result_values = {}
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
                # read zone ID
                weights = []
                A_values = []
                b_values = []
                
                zone_id = line.strip()
                dataLengthMode = True
                zoneStartMode = False

            elif dataLengthMode is True:
                data_line_count = int(line.strip())
                data_line_idx = 0
                dataLineMode = True
                dataLengthMode = False

            elif dataLineMode is True:
                # output lines in result matrix:
                #  first value: weight, 
                #  second value: A (activity), 
                #  third value: b
                
                (weight, A_value, b_value) = line.strip().split()
                
                weights.append(float(weight))
                A_values.append(float(A_value))
                b_values.append(float(b_value))
                data_line_idx += 1

                # all lines read
                if data_line_idx == data_line_count:

                    # A values are still in Roger Musson's scaling
                    # re-scale them to M=0
                    a_values = activity2aValue(A_values, b_values)
                
                    weight_str_arr = ["%.3f" % (x) for x in weights]
                    a_value_str_arr = ["%.3f" % (x) for x in a_values]
                    b_value_str_arr = ["%.3f" % (x) for x in b_values]
                    
                    # get best a and b value from central line of result matrix
                    zone_values = [float(a_values[data_line_count / 2]),
                        float(b_values[data_line_count / 2]),
                        ' '.join(weight_str_arr), 
                        ' '.join(a_value_str_arr), 
                        ' '.join(b_value_str_arr)]
                    result_values[zone_id] = zone_values
                    
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

def aValue2activity(a_value, b_value, m_min=ATTICIVY_MMIN):
    """Convert a parameter to A as returned from Roger Musson's code
    (at M=3.5).
    
    a = log10(A) + b * Mmin
    
    Input:
        A_value     list of AtticIvy A parameters
        b_value     list of AtticIvy b parameters
        m_min       Mmin for which AtticIvy activity has been computed
    """
    a = numpy.array(a_value)
    b = numpy.array(b_value)
    
    A = numpy.power(10, a - b * m_min)
    
    return A
