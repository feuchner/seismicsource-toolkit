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
import os
import sys

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

    ## set auxiliary data files
    
    # EQ catalog
    
    # background zones
    

def runPart1(**kwargs):
    """Run part 1 of computation."""

    global metadata
    pass


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
