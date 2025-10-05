from qgis.core import QgsApplication

from .moe_geoportal_loader_provider import MOELoaderProvider


class MOEGeoportalLoader(object):
    def __init__(self):
        self.provider = None

    def initProcessing(self):
        self.provider = MOELoaderProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)

    def initGui(self):
        self.initProcessing()

    def unload(self):
        QgsApplication.processingRegistry().removeProvider(self.provider)
