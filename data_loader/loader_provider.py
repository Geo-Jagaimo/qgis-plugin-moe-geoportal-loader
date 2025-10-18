from pathlib import Path

from qgis.core import QgsProcessingProvider
from qgis.PyQt.QtGui import QIcon

from .loader_coral import CoralLoaderAlgorithm
from .loader_mammal import MammalLoaderAlgorithm
from .loader_seagrass import SeagrassLoaderAlgorithm
from .loader_vegetation import VegetationLoaderAlgorithm


class MOELoaderProvider(QgsProcessingProvider):
    def loadAlgorithms(self, *args, **kwargs):
        self.addAlgorithm(VegetationLoaderAlgorithm())
        self.addAlgorithm(CoralLoaderAlgorithm())
        self.addAlgorithm(MammalLoaderAlgorithm())
        self.addAlgorithm(SeagrassLoaderAlgorithm())

    def id(self, *args, **kwargs):
        return "moe"

    def name(self, *args, **kwargs):
        return "MOE Geoportal Loader"

    def icon(self):
        path = (Path(__file__).parent.parent / "imgs" / "icon.png").resolve()
        return QIcon(str(path))
