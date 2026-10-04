import os
import sys
import unittest
from unittest.mock import patch

from qgis.core import QgsApplication
from qgis.testing import start_app

from data_loader.algorithm import MOELoaderAlgorithm
from data_loader.settings_datasets import DATASETS

DATASET_KEYS = list(DATASETS)


class TestPrefectureFollowsDataset(unittest.TestCase):
    """The prefecture is enabled only for the datasets published per prefecture."""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        start_app()
        # The dialog comes from the Processing plugin, which QGIS itself puts
        # on the path
        sys.path.append(os.path.join(QgsApplication.pkgDataPath(), "python", "plugins"))

    def setUp(self):
        self.dialog = MOELoaderAlgorithm().create().createCustomParametersWidget()
        wrappers = self.dialog.mainWidget().wrappers
        self.dataset = wrappers["CATEGORY"]
        self.prefecture = wrappers["PREFECTURE"]

    def _select(self, wrapper, value):
        combo = wrapper.wrappedWidget()
        combo.setCurrentIndex(combo.findData(value))

    def _select_dataset(self, key):
        self._select(self.dataset, DATASET_KEYS.index(key))

    def _prefecture_enabled(self):
        enabled = self.prefecture.wrappedWidget().isEnabled()
        self.assertEqual(self.prefecture.wrappedLabel().isEnabled(), enabled)
        return enabled

    def test_opens_disabled_when_the_default_dataset_has_no_prefecture(self):
        # The default is the first dataset
        datasets = {key: DATASETS[key] for key in ("anaguma", "vg_50000")}
        with patch("data_loader.algorithm.DATASETS", datasets):
            dialog = MOELoaderAlgorithm().create().createCustomParametersWidget()
        prefecture = dialog.mainWidget().wrappers["PREFECTURE"]
        self.assertFalse(prefecture.wrappedWidget().isEnabled())
        self.assertFalse(prefecture.wrappedLabel().isEnabled())

    def test_follows_the_selected_dataset(self):
        for key, dataset in DATASETS.items():
            with self.subTest(dataset=key):
                self._select_dataset(key)
                self.assertEqual(self._prefecture_enabled(), dataset["has_prefecture"])

    def test_keeps_the_prefecture_until_enabled_again(self):
        tokyo = 12
        self._select_dataset("vg_50000")
        self._select(self.prefecture, tokyo)

        self._select_dataset("anaguma")
        self.assertFalse(self._prefecture_enabled())
        self._select_dataset("vg_50000")
        self.assertTrue(self._prefecture_enabled())
        self.assertEqual(self.prefecture.parameterValue(), tokyo)

    def test_follows_parameters_set_by_code(self):
        # As processing.execAlgorithmDialog() and "Paste Settings" set them
        self.dialog.setParameters({"CATEGORY": DATASET_KEYS.index("anaguma")})
        self.assertFalse(self._prefecture_enabled())
        self.dialog.setParameters({"CATEGORY": DATASET_KEYS.index("vg_50000")})
        self.assertTrue(self._prefecture_enabled())


class TestDialogFallback(unittest.TestCase):
    def test_qgis_dialog_is_used_when_the_dialog_cannot_be_imported(self):
        with patch.dict(sys.modules, {"data_loader.dialog": None}):
            self.assertIsNone(MOELoaderAlgorithm().createCustomParametersWidget())


if __name__ == "__main__":
    unittest.main()
