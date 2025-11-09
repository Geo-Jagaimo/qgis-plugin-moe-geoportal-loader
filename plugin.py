from qgis.core import QgsApplication
from qgis.gui import QgisInterface

from .data_loader.provider import MOELoaderProvider


class MOEGeoportalLoader:
    def __init__(self, iface: QgisInterface):
        self.iface = iface

    def initGui(self):
        self.provider = MOELoaderProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)

    def unload(self):
        QgsApplication.processingRegistry().removeProvider(self.provider)
