from pathlib import Path

from qgis.core import QgsApplication
from qgis.gui import QgisInterface
from qgis.PyQt.QtCore import QCoreApplication, QSettings, QTranslator

from .data_loader.provider import MOELoaderProvider


class MOEGeoportalLoader:
    def __init__(self, iface: QgisInterface):
        self.iface = iface
        self.translator = None

        self.load_translator()

    def load_translator(self):
        """Load translation file."""
        plugin_dir = Path(__file__).parent

        # Get locale ("ja")
        locale = QSettings().value("locale/userLocale", "ja")
        if locale:
            locale = locale[:2]

        qm_file = plugin_dir / "i18n" / f"data_loader_{locale}.qm"

        if qm_file.exists():
            self.translator = QTranslator()
            if self.translator.load(str(qm_file)):
                QCoreApplication.installTranslator(self.translator)
                print(f"Loaded translation file: {qm_file}")
            else:
                print(f"Failed to load translation file: {qm_file}")
                self.translator = None
        else:
            print(f"Translation file not found: {qm_file}")

    def initGui(self):
        self.provider = MOELoaderProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)

    def unload(self):
        QgsApplication.processingRegistry().removeProvider(self.provider)

        if self.translator:
            QCoreApplication.removeTranslator(self.translator)
            self.translator = None
