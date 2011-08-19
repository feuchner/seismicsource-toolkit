#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SHARE Seismic Source Toolkit

This is the batch script for the toolkit.

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

import getopt
import glob
import ogr
import os
import shutil
import sys

from PyQt4.QtCore import *
from qgis.core import *

import mt_seismicsource.data
import mt_seismicsource.layers
import mt_seismicsource.utils

from mt_seismicsource.algorithms import atticivy
from mt_seismicsource.algorithms import recurrence

from mt_seismicsource.layers import areasource
from mt_seismicsource.layers import background
from mt_seismicsource.layers import eqcatalog

## set a few paths

# this gets the absolute base path (path where this script resides)
# subsequent directory hierarchy will be below this directory
scriptpath = os.path.abspath(sys.argv[0])
scriptname = os.path.basename(scriptpath)
scriptdir = os.path.dirname(scriptpath)

# get working directory - subsequent directory hierarchy will be below
basepath = os.getcwd()

# location of toolkit code
toolkitdir = os.path.join(scriptdir, 'mt_seismicsource')

metadata = {}

MODE_IDENTIFIERS = ('ASZ', 'FSZ', 'FBZ')

CATALOG_PATH = os.path.join(mt_seismicsource.layers.DATA_DIR, 
    eqcatalog.CATALOG_DIR, eqcatalog.CATALOG_FILES[0])

BACKGROUND_MMAX_PATH = os.path.join(mt_seismicsource.layers.DATA_DIR, 
    background.BACKGROUND_DIR, background.BACKGROUND_ZONES_MMAX_FILE)
BACKGROUND_COMPLETENESS_PATH = os.path.join(mt_seismicsource.layers.DATA_DIR, 
    background.BACKGROUND_DIR, background.BACKGROUND_ZONES_COMPLETENESS_FILE)

SHP_EXTENSION_CHAR_CNT = 3

def main():
    """Main program."""
    global scriptname
    global metadata

    # supply path to where is your qgis installed
    QgsApplication.setPrefixPath("/usr", True)

    # load providers
    QgsApplication.initQgis()
    QgsApplication.registerOgrDrivers()
    
    setUp()
    run()
    
    QgsApplication.exitQgis()

def setUp():
    """Set up computation, evaluate commandline options."""
    global metadata
    
    # command line variables
    in_overwrite = False
    in_infile_name = None
    in_mode = None
    in_outfile_name = None

    # Read commandline arguments
    cmdParams = sys.argv[1:]
    if len(cmdParams) == 0:
        PrintHelp()
        sys.exit()
            
    opts, args = getopt.gnu_getopt(cmdParams, 'hwi:m:o:', [])

    for option, parameter in opts:

        if option == '-w':
            in_overwrite = True

        if option == '-i':
            in_infile_name = parameter

        if option == '-m':
            in_mode = parameter
            
        if option == '-o':
            in_outfile_name = parameter

        if option == '-h':
            PrintHelp()
            sys.exit()

    # check if valid mode identifier has been specified
    if in_mode not in MODE_IDENTIFIERS:
        error_str = "%s - no valid mode identifier has been specified" % scriptname
        raise ValueError, error_str
    else:
        metadata['mode'] = in_mode

    # check if input file exists
    if os.path.isfile(in_infile_name):
        metadata['infile_name'] = in_infile_name
    else:
        error_str = "input file does not exist"
        raise ValueError, error_str
    
    # set output file name
    if in_outfile_name is not None:
        # write to a new output file
        
        # copy all shp components to output base file name
        shp_components = getShpComponents(metadata['infile_name'])
        for shp_component in shp_components:
            shutil.copy(shp_component, "%s.%s" % (
                in_outfile_name[:-(SHP_EXTENSION_CHAR_CNT+1)], 
                shp_component[-SHP_EXTENSION_CHAR_CNT:]))
        
        metadata['outfile_name'] = in_outfile_name
        
    else:
        # change input file in-place, but make backup copy
        
        # get all shp components
        shp_components = getShpComponents(metadata['infile_name'])
        for shp_component in shp_components:
            shutil.copy(shp_component, "%s~" % shp_component)
        
        metadata['outfile_name'] = metadata['infile_name']

    print "loading auxiliary data"
    
    ## set auxiliary data files
    metadata['data'] = mt_seismicsource.data.Datasets()
    
    # EQ catalog
    (foo, metadata['catalog']) = eqcatalog.loadEQCatalogFromFile(CATALOG_PATH)
    
    # background zones
    metadata['background_layer'] = background.loadBackgroundZoneFromFile(
        BACKGROUND_MMAX_PATH, BACKGROUND_COMPLETENESS_PATH, ui_mode=False)
    

def run():
    """Run batch computation."""

    global metadata

    # choose mode
    if metadata['mode'] == 'ASZ':
        layer = processASZ()
    elif metadata['mode'] == 'FSZ':
        layer = processFSZ()
    elif metadata['mode'] == 'FBZ':
        layer = processBGZ()
    else:
        error_str = "invalid mode"
        raise RuntimeError, error_str

    # write layer to shapefile
    print "writing to shapefile"
    
    pr = layer.dataProvider()
    pr.select()
    
    mt_seismicsource.utils.writeFeaturesToShapefile(layer, 
        metadata['outfile_name'])

def processASZ():
    """Compute attributes for Area Source Zones:
        - activity parameters using Roger Musson's code
    """
    
    global metadata
    
    print "loading ASZ layer"
    metadata['asz_layer'] = areasource.loadAreaSourceFromSHP(
        metadata['infile_name'], metadata['data'].mmax, 
        metadata['background_layer'])

    pr = metadata['asz_layer'].dataProvider()
    pr.select()
    print "features:", pr.featureCount()
    print "fields:", pr.fieldCount()
    
    #attribute_map = mt_seismicsource.utils.getAttributeIndex(pr, ({'name': 'FOO', 'type': QVariant.String},), create=True)
    
    #all_features = [feat.id() for feat in pr]
    #all_features = [292, 295, 297, 304]
    all_features = [108]
    #all_features = [279]
    #all_features = [292, 304]
    metadata['asz_layer'].setSelectedFeatures(all_features)
    
    print "running AtticIvy on ASZ layer"
    atticivy.assignActivityAtticIvy(metadata['asz_layer'], 
        metadata['catalog'], ui_mode=False)

    #values = {}
    #fts = metadata['asz_layer'].selectedFeatures()
    #for zone_idx, zone in enumerate(fts):
        #zone_str = "bar%s" % zone_idx
        #values[zone.id()] = {11: QVariant(zone_str)}
        
    #pr.changeAttributeValues(values)
    #metadata['asz_layer'].commitChanges()
    
    return metadata['asz_layer']

def processFSZ():
    pass

def processBGZ():
    pass

def getShpComponents(shapefile_name):
    """Find components of shapefile."""
    extension_str = SHP_EXTENSION_CHAR_CNT * '?'
    return glob.glob("%s.%s" % (shapefile_name[:-(SHP_EXTENSION_CHAR_CNT+1)], 
        extension_str))
    
def PrintHelp():
    """Print help info."""
    global scriptname
    
    print 'Batch processing of Seismic Source Toolkit'
    print 'Usage: %s [OPTION]' % scriptname
    print '  Options'
    print '   -i FILE      Input file'
    print '   -m VALUE     Mode (ASZ/FSZ/FBZ)'
    print '   -o FILE      Output file'
    print '   -w           Overwrite existing attributes'
    print '   -h, --help   Print this information'
    
if __name__ == "__main__":
    main()
