# -*- coding: utf-8 -*-
"""
SHARE Seismic Source Toolkit

Engine functions that can be called from either UI or batch program. 

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

#from PyQt4.QtCore import *
#from PyQt4.QtGui import *

#from qgis.core import *

from mt_seismicsource import utils

from mt_seismicsource.algorithms import atticivy
from mt_seismicsource.algorithms import recurrence
from mt_seismicsource.layers import eqcatalog

def computeASZ(layer, catalog, mindepth=eqcatalog.CUT_DEPTH_MIN,
    maxdepth=eqcatalog.CUT_DEPTH_MAX, ui_mode=True):
    """Compute attributes on selected features of ASZ layer."""
    
    # check that at least one feature is selected
    if not utils.check_at_least_one_feature_selected(layer):
        return

    updateASZAtticIvy(layer, catalog, mindepth, maxdepth, ui_mode)
    updateASZMaxLikelihoodAB()
    updateASZMomentRate()

def updateASZAtticIvy(layer, catalog, mindepth=eqcatalog.CUT_DEPTH_MIN,
    maxdepth=eqcatalog.CUT_DEPTH_MAX, ui_mode=True):
    """Update AtticIvy attributes on ASZ layer."""
    
    atticivy.assignActivityAtticIvy(layer, catalog, atticivy.ATTICIVY_MMIN,
        mindepth, maxdepth, ui_mode)
    layer.commitChanges()

def updateASZMaxLikelihoodAB(ui_mode=True):
    """Update max likelihood a/b value attributes on ASZ layer."""
    pass

def updateASZMomentRate(ui_mode=True):
    """Update seismic moment rate attributes on ASZ layer."""
    pass

def computeFSZ(layer_fault, layer_fault_background=None, 
    layer_background=None, catalog=None, catalog_time_span=None, b_value=None,
    mmin=atticivy.ATTICIVY_MMIN, 
    m_threshold=recurrence.FAULT_BACKGROUND_MAG_THRESHOLD,
    mindepth=eqcatalog.CUT_DEPTH_MIN, maxdepth=eqcatalog.CUT_DEPTH_MAX,
    ui_mode=True):
    """Compute attributes on selected features of ASZ layer."""
    
    # check that at least one feature is selected
    if not utils.check_at_least_one_feature_selected(layer_fault):
        return

    updateFSZRecurrence(layer_fault, layer_fault_background, layer_background,
        catalog, catalog_time_span, b_value, mmin, m_threshold, mindepth, 
        maxdepth, ui_mode)
    updateFSZMaxLikelihoodAB()
    updateFSZMomentRate()

def updateFSZRecurrence(layer_fault, layer_fault_background=None, 
    layer_background=None, catalog=None, catalog_time_span=None, b_value=None,
    mmin=atticivy.ATTICIVY_MMIN, 
    m_threshold=recurrence.FAULT_BACKGROUND_MAG_THRESHOLD,
    mindepth=eqcatalog.CUT_DEPTH_MIN, maxdepth=eqcatalog.CUT_DEPTH_MAX,
    ui_mode=True):
    """Update AtticIvy attributes on FSZ layer."""

    recurrence.assignRecurrence(layer_fault, layer_fault_background, 
        layer_background, catalog, catalog_time_span, 
        m_threshold=m_threshold, mindepth=mindepth, maxdepth=maxdepth, 
        ui_mode=ui_mode)
    layer_fault.commitChanges()

def updateFSZMaxLikelihoodAB(ui_mode=True):
    """Update max likelihood a/b value attributes on FSZ layer."""
    pass

def updateFSZMomentRate(ui_mode=True):
    """Update seismic moment rate attributes on FSZ layer."""
    pass
