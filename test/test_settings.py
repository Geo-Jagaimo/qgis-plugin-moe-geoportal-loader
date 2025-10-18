import unittest

from data_loader.datasets.coral import CORAL_DATASETS
from data_loader.datasets.mammal import MAMMAL_DATASETS
from data_loader.datasets.prefecture import PREFECTURES
from data_loader.datasets.seagrass import SEAGRASS_DATASETS
from data_loader.datasets.vegetation import VEGETATION_DATASETS

# 全データセットをまとめたもの
ALL_DATASETS = {
    **VEGETATION_DATASETS,
    **CORAL_DATASETS,
    **MAMMAL_DATASETS,
    **SEAGRASS_DATASETS,
}


class TestSettings(unittest.TestCase):
    def test_datasets_structure(self):
        """全カテゴリのデータセット構造をテスト"""
        dataset_collections = {
            "vegetation": VEGETATION_DATASETS,
            "coral": CORAL_DATASETS,
            "mammal": MAMMAL_DATASETS,
            "seagrass": SEAGRASS_DATASETS,
        }

        for category, datasets in dataset_collections.items():
            with self.subTest(category=category):
                self.assertTrue(datasets, f"{category} datasets must not be empty")
                for key, dataset in datasets.items():
                    with self.subTest(dataset=key):
                        self.assertIn("name", dataset)
                        self.assertIn("url", dataset)
                        self.assertIn("has_prefecture", dataset)
                        self.assertIsInstance(
                            dataset["has_prefecture"],
                            bool,
                            "has_prefecture must be boolean",
                        )
                        url = dataset["url"]
                        self.assertTrue(url.startswith("https://"))
                        if dataset["has_prefecture"]:
                            self.assertIn(
                                "{pref_code}",
                                url,
                                "Prefecture aware datasets must include {pref_code} in URL",
                            )
                        else:
                            self.assertNotIn(
                                "{pref_code}",
                                url,
                                "Non-prefecture datasets must not include {pref_code} in URL",
                            )

    def test_dataset_names_unique(self):
        """全データセット間で名前が重複していないことを確認"""
        names = [dataset["name"] for dataset in ALL_DATASETS.values()]
        self.assertEqual(len(names), len(set(names)), "Dataset names must be unique")

    def test_dataset_keys_unique(self):
        """全データセット間でキーが重複していないことを確認"""
        all_keys = list(ALL_DATASETS.keys())
        self.assertEqual(
            len(all_keys), len(set(all_keys)), "Dataset keys must be unique"
        )

    def test_prefectures_structure(self):
        self.assertEqual(
            PREFECTURES.get("00"),
            "都道府県を選択してください",
            'Prefecture code "00" should be the placeholder entry',
        )
        self.assertTrue(
            PREFECTURES.keys() >= {"01", "13", "47"},
            "Prefecture mapping should include key prefectures",
        )
        codes = list(PREFECTURES.keys())
        self.assertEqual(len(codes), len(set(codes)), "Prefecture codes must be unique")


if __name__ == "__main__":
    unittest.main()
