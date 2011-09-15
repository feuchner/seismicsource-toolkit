# -*- coding: utf-8 -*-
"""
SHARE Seismic Source Toolkit

Common functions for engines.

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

import QPCatalog

def prepareEQCatalog(catalog, catalog_time_span, mindepth, maxdepth):
    """Cuts EQ catalog with depth and computes time span, if not provided."""

    if catalog_time_span is None:
        catalog_time_span = catalog.timeSpan()[0]
    
    # cut catalog with min/max depth
    cat_depthcut = QPCatalog.QPCatalog()
    cat_depthcut.merge(catalog)
    cat_depthcut.cut(mindepth=mindepth, maxdepth=maxdepth)
    
    return (cat_depthcut, catalog_time_span)
    