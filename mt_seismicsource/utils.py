# -*- coding: utf-8 -*-
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
#import shapely.geometry
#import shapely.ops
import shutil
import subprocess
#import sys
import tempfile

#from PyQt4.QtCore import *
#from PyQt4.QtGui import *

#from qgis.core import *

# import QPCatalog

ATTICIVY_MMIN = 3.5
ATTICIVY_EXECUTABLE = 'code/AtticIvy/AtticIvy'
ATTICIVY_ZONE_FILE = 'AtticIvy-Zone.inp'
ATTICIVY_CATALOG_FILE = 'AtticIvy-Catalog.dat'
ATTICIVY_RESULT_FILE = '%s_out.txt' % ATTICIVY_ZONE_FILE[0:-5]

def assignActivityMaxLikelihood():
    pass

def computeActivityMaxLikelihood():
    """Computes a-and b values using the maximum likelihood method for
    a set of source zone polygons.
    
    Input: iterable of zone polygons
           earthquake catalog as QuakePy object

    Output: list of (a, b) pairs
    """
    
    pass

# Roger Musson's AtticIvy

def assignActivityAtticIvy():
    pass

def computeActivityAtticIvy(zones, catalog, Mmin=ATTICIVY_MMIN):
    """Computes a-and b values using Roger Musson's AtticIvy code for
    a set of source zone polygons.
    
    Input: 
        zones   iterable of zone features in QGis format 
        catalog earthquake catalog as QuakePy object

    Output: 
        list of (a, b) pairs
    """
    
    # create temp dir for computation
    temp_dir = tempfile.mkdtemp()

    # write zone data to temp file in AtticIvy format
    zone_file_path = os.path.join(temp_dir, ATTICIVY_ZONE_FILE)
    writeZones2AtticIvy(zones, zone_file_path, Mmin)

    # write catalog to temp file in AtticIvy format
    catalog_file_path = os.path.join(temp_dir, ATTICIVY_CATALOG_FILE)
    catalog.exportAtticIvy(catalog_file_path)

    # start AtticIvy computation (subprocess)
    exec_path = os.path.join(os.path.dirname(__file__), ATTICIVY_EXECUTABLE)
    retcode = subprocess.call([exec_path, zone_file_path, catalog_file_path])

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
    fh = open(path, 'w')

    # write header
    fh.write('Mmin.......:%3.1f' % ATTICIVY_MMIN)
    fh.write('# zones....:%3i' % len(zones))
    
    # loop over zones
    for curr_zone_idx, curr_zone in enumerate(zones):

        # get geometry
        geom = curr_zone.geometry().asPolygon()
        vertices = [(x.x(), x.y()) for x in geom[0]]
        fh.write('%04i , %s' % (curr_zone_idx, len(vertices)))
        for vertex in vertices:
            fh.write('%s , %s' % (vertex[1], vertex[0]))

        # TODO(fab): get attributes

    fh.close()
