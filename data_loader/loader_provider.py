from pathlib import Path

from qgis.core import QgsProcessingProvider
from qgis.PyQt.QtGui import QIcon

from .loader_algorithm import MOELoaderAlgorithm


class MOELoaderProvider(QgsProcessingProvider):
    def loadAlgorithms(self, *args, **kwargs):
        self.addAlgorithm(MOELoaderAlgorithm())

    def id(self, *args, **kwargs):
        return "moe"

    def name(self, *args, **kwargs):
        return "MOE Geoportal Loader"

    def icon(self):
        path = (Path(__file__).parent.parent / "imgs" / "icon.png").resolve()
        return QIcon(str(path))
