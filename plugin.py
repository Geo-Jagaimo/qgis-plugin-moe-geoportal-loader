from qgis.core import QgsApplication
from qgis.gui import QgisInterface

from .moe_geoportal_loader.provider import MOELoaderProvider


class MOEGeoportalLoader:
    def __init__(self, iface: QgisInterface):
        self.provider = None
        self.iface = iface

    def initProcessing(self):
        self.provider = MOELoaderProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)

    def initGui(self):
        self.initProcessing()

    def unload(self):
        QgsApplication.processingRegistry().removeProvider(self.provider)
