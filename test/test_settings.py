import unittest

from data_loader.settings_datasets import DATASETS
from data_loader.settings_prefecture import PREFECTURES


class TestSettings(unittest.TestCase):
    def test_datasets_structure(self):
        self.assertTrue(DATASETS, "DATASETS must not be empty")
        for key, dataset in DATASETS.items():
            with self.subTest(dataset=key):
                self.assertIn("name", dataset)
                self.assertIn("url", dataset)
                self.assertIn("has_prefecture", dataset)
                self.assertIsInstance(
                    dataset["has_prefecture"], bool, "has_prefecture must be boolean"
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
        names = [dataset["name"] for dataset in DATASETS.values()]
        self.assertEqual(len(names), len(set(names)), "Dataset names must be unique")

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
