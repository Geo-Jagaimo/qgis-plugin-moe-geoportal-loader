import contextlib

from qgis.core import QgsApplication
from qgis.gui import QgisInterface
from qgis.PyQt.QtWidgets import QAction, QToolButton

from .moe_geoportal_loader.provider import MOELoaderProvider

with contextlib.suppress(ImportError):
    from processing import execAlgorithmDialog


class MOEGeoportalLoader:
    def __init__(self, iface: QgisInterface):
        self.iface = iface

    def initGui(self):
        self.provider = MOELoaderProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)

        if self.iface:
            self.setup_algorithm_tool_button()

    def unload(self):
        self.teardown_algorithm_tool_button()
        QgsApplication.processingRegistry().removeProvider(self.provider)

    def setup_algorithm_tool_button(self):
        if hasattr(self, "toolButtonAction") and self.toolButtonAction:
            return

        tool_button = QToolButton()
        icon = self.provider.icon()
        default_action = QAction(
            icon, "環境ジオポータルのデータを読み込む", self.iface.mainWindow()
        )
        default_action.triggered.connect(
            lambda: execAlgorithmDialog("moe:moe_geoportal_loader", {})
        )
        tool_button.setDefaultAction(default_action)

        self.toolButtonAction = self.iface.addToolBarWidget(tool_button)

    def teardown_algorithm_tool_button(self):
        if hasattr(self, "toolButtonAction"):
            self.iface.removeToolBarIcon(self.toolButtonAction)
            del self.toolButtonAction
