import importlib
import importlib.util
import os
import sys
import unittest

from qgis.core import QgsApplication
from qgis.testing import start_app

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_plugin_package():
    # Import the repository as the "moe_geoportal_loader" package, as QGIS does
    # with the released plugin, so that plugin.py's relative imports resolve
    spec = importlib.util.spec_from_file_location(
        "moe_geoportal_loader",
        os.path.join(ROOT, "__init__.py"),
        submodule_search_locations=[ROOT],
    )
    package = importlib.util.module_from_spec(spec)
    sys.modules["moe_geoportal_loader"] = package
    spec.loader.exec_module(package)
    return package


class TestPluginEntryPoints(unittest.TestCase):
    """The provider must be registered both in QGIS Desktop and in qgis_process."""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        start_app()
        cls.package = _load_plugin_package()

    def setUp(self):
        # QGIS passes no iface to qgis_process plugins
        self.plugin = self.package.classFactory(None)
        self.addCleanup(self.plugin.unload)

    def _registered(self):
        return QgsApplication.processingRegistry().providerById("moe") is not None

    def test_init_processing_registers_the_provider(self):
        # qgis_process only calls initProcessing()
        self.plugin.initProcessing()
        self.assertTrue(self._registered())

        self.plugin.unload()
        self.assertFalse(self._registered())

    def test_init_gui_registers_the_provider(self):
        self.plugin.initGui()
        self.assertTrue(self._registered())

        self.plugin.unload()
        self.assertFalse(self._registered())

    def test_unload_before_init_does_not_fail(self):
        self.plugin.unload()
        self.assertFalse(self._registered())


if __name__ == "__main__":
    unittest.main()
