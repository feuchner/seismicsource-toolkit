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

# import mt_seismicsource

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

def main():
    """Main program."""
    global scriptname
    global metadata

    setUp()
    runParts()
    
def runParts():
    """Sequentially run parts of program."""
    runPart1()

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
                in_outfile_name[:-4], shp_component[-3:]))
        
        metadata['outfile_name'] = in_outfile_name
        
    else:
        # change input file in-place, but make backup copy
        
        # get all shp components
        shp_components = getShpComponents(metadata['infile_name'])
        for shp_component in shp_components:
            shutil.copy(shp_component, "%s~" % shp_component)
        
        metadata['outfile_name'] = metadata['infile_name']

    ## set auxiliary data files
    
    # EQ catalog
    
    # background zones
    

def runPart1():
    """Run part 1 of computation."""

    global metadata
    
    # open shapefile for writing
    ds = ogr.Open(metadata['outfile_name'], True)
    
    # use first layer
    lyr = ds.GetLayer(0)
    lyr.ResetReading()

    # add attribute
    field_new = ogr.FieldDefn("NEW", ogr.OFTString)
    field_new.SetWidth(32)
    lyr.CreateField(field_new)
        
    feat_defn = lyr.GetLayerDefn()
    feat_cnt = feat_defn.GetFieldCount()
        
    for feat in lyr:
        for idx in xrange(feat_cnt-1):
            
            field_defn = feat_defn.GetFieldDefn(idx)
            print "%s %s" % (idx, feat.GetField(idx))

        feat.SetField(feat_cnt-1, 'foo') 
        lyr.SetFeature(feat)
        
        geom = feat.GetGeometryRef()
        
        if geom is not None and geom.GetGeometryType() == ogr.wkbPolygon:
            #print "%.3f, %.3f" % ( geom.GetX(), geom.GetY() )
            print "polygon"
        else:
            print "no polygon geometry\n"
            
    ds = None

def processASZ():
    pass

def processFSZ():
    pass

def processBGZ():
    pass

def getShpComponents(shapefile_name):
    """Find components of shapefile."""
    return glob.glob("%s.???" % shapefile_name[:-4])
    
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
