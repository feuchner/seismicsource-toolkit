# -*- coding: utf-8 -*-
"""
SHARE Seismic Source Toolkit

This is a toolkit for editing seismic source zones used in the
SHARE project.
It is realized as a Python plugin for Quantum GIS.

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

def name():
    return "SHARE Seismic Source Toolkit"

def description():
    return "This toolkit allows to modify the seismic source zones for the "\
        "SHARE project"

def version():
    return "0.1"
  
def qgisMinimumVersion():
    return "1.0"

def authorName():
    return "Fabian Euchner"

def classFactory(iface):
    from seismic_source_toolkit import SeismicSourceToolkit
    return SeismicSourceToolkit(iface)
