# -*- coding: utf-8 -*-
"""
SHARE Seismic Source Toolkit

Loader for tectonic regime layer.

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

from PyQt4.QtCore import *
from PyQt4.QtGui import *

from qgis.core import *

#from mt_seismicsource import layers
#from mt_seismicsource import utils

def loadTectonicRegimeLayer(cls):
    """Load layer of tectonic regime polygons."""

    # PostGIS SRID 4326 is allocated for WGS84
    crs = QgsCoordinateReferenceSystem(4326, 
        QgsCoordinateReferenceSystem.PostgisCrsId)

    # create layer
    layer = QgsVectorLayer("Polygon", "Tectonic Regimes", "memory")
    layer.setCrs(crs) 
    pr = layer.dataProvider()

    # add attributes
    # - type
    pr.addAttributes([QgsField("type", QVariant.String)])

    for regime_id, multipoly in cls.data.deformation_regimes_bird.items():
        
        for polygon in multipoly.geoms:

            f = QgsFeature()

            poly = [QgsPoint(x, y) for (x, y) in polygon.exterior.coords]
            f.setGeometry(QgsGeometry.fromPolygon([poly]))
            
            f[0] = QVariant(regime_id)

            pr.addFeatures([f])

    # update layer's extent when new features have been added
    # because change of extent in provider is not 
    # propagated to the layer
    layer.updateExtents()
    QgsMapLayerRegistry.instance().addMapLayer(layer)

    return layer
