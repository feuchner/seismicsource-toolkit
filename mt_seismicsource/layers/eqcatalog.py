# -*- coding: utf-8 -*-
"""
SHARE Seismic Source Toolkit

Loader for EQ catalog layer.

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

import os

from PyQt4.QtCore import *
from PyQt4.QtGui import *

from qgis.core import *

import QPCatalog

from mt_seismicsource import layers
from mt_seismicsource import features
from mt_seismicsource import utils


CATALOG_DIR = 'eq_catalog'
CATALOG_FILES = ('cenec-zmap.dat', 'SHARE_20110311.dat.gz')

def loadEQCatalogLayer(cls):
    """Load EQ catalog layer from ASCII catalog file. 
    Add required feature attributes if they are missing.

    TODO(fab): load catalog from Python pickle of compact catalog format.

    Input:
        path    Filename of catalog file
    """
    catalog_path = os.path.join(layers.DATA_DIR, CATALOG_DIR, 
        unicode(cls.comboBoxEQCatalogInput.currentText()))

    if not os.path.isfile(catalog_path):
        utils.warning_box_missing_layer_file(catalog_path)
        return

    cls.catalog = QPCatalog.QPCatalog()

    if catalog_path.endswith('.gz'):
        cls.catalog.importZMAP(catalog_path, minimumDataset=True,
            compression='gz')
    else:
        cls.catalog.importZMAP(catalog_path, minimumDataset=True)

    # cut catalog to years > 1900 (because of datetime)
    # TODO(fab): change the datetime lib to mx.DateTime
    cls.catalog.cut(mintime='1900-01-01', mintime_exclude=True)
    cls.labelCatalogEvents.setText(
        "Catalog events: %s" % cls.catalog.size())

    # cut with selected polygons
    cls.catalog_selected = QPCatalog.QPCatalog()
    cls.catalog_selected.merge(cls.catalog)
    cls.labelSelectedEvents.setText(
        "Selected events: %s" % cls.catalog_selected.size())

    # create layer
    layer = QgsVectorLayer("Point", "CENEC catalog", "memory")
    pr = layer.dataProvider()

    # add fields
    pr.addAttributes([QgsField("magnitude", QVariant.Double),
                        QgsField("depth",  QVariant.Double)])

    # add EQs as features
    for curr_event in cls.catalog_selected.eventParameters.event:
        curr_ori = curr_event.getPreferredOrigin()

        # skip events without magnitude
        try:
            curr_mag = curr_event.getPreferredMagnitude()
        except IndexError:
            continue

        curr_lon = curr_ori.longitude.value
        curr_lat = curr_ori.latitude.value
        magnitude = curr_mag.mag.value

        try:
            depth = curr_ori.depth.value
        except Exception:
            depth = numpy.nan

        f = QgsFeature()
        f.setGeometry(QgsGeometry.fromPoint(QgsPoint(curr_lon, curr_lat)))
        f[0] = QVariant(magnitude)
        f[1] = QVariant(depth)
        pr.addFeatures([f])

    # update layer's extent when new features have been added
    # because change of extent in provider is not 
    # propagated to the layer
    layer.updateExtents()
    QgsMapLayerRegistry.instance().addMapLayer(layer)
    return layer
