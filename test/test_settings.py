import unittest

from data_loader.settings_datasets import DATASETS
from data_loader.settings_prefecture import PREFECTURES


class TestDatasets(unittest.TestCase):
    """Test DATASETS structure and consistency"""

    def test_datasets_not_empty(self):
        """Verify that datasets are not empty"""
        self.assertTrue(DATASETS, "DATASETS must not be empty")
        self.assertGreater(len(DATASETS), 0, "DATASETS must contain at least one entry")

    def test_dataset_required_keys(self):
        """Verify that all datasets have required keys"""
        required_keys = {"name", "url", "has_prefecture"}
        for dataset_key, dataset in DATASETS.items():
            with self.subTest(dataset=dataset_key):
                self.assertIsInstance(dataset, dict, f"{dataset_key} must be a dict")
                missing_keys = required_keys - dataset.keys()
                self.assertEqual(
                    set(),
                    missing_keys,
                    f"{dataset_key} is missing required keys: {missing_keys}",
                )

    def test_dataset_name_is_string(self):
        """Verify that dataset names are strings"""
        for dataset_key, dataset in DATASETS.items():
            with self.subTest(dataset=dataset_key):
                self.assertIsInstance(
                    dataset["name"],
                    str,
                    f"{dataset_key}: name must be a string",
                )
                self.assertGreater(
                    len(dataset["name"]),
                    0,
                    f"{dataset_key}: name must not be empty",
                )

    def test_dataset_url_format(self):
        """Verify dataset URL format"""
        for dataset_key, dataset in DATASETS.items():
            with self.subTest(dataset=dataset_key):
                url = dataset["url"]
                self.assertIsInstance(url, str, f"{dataset_key}: url must be a string")
                self.assertTrue(
                    url.startswith("https://"),
                    f"{dataset_key}: url must start with https://",
                )
                self.assertTrue(
                    "/FeatureServer" in url,
                    f"{dataset_key}: url must contain /FeatureServer",
                )

    def test_dataset_has_prefecture_type(self):
        """Verify that has_prefecture is a boolean type"""
        for dataset_key, dataset in DATASETS.items():
            with self.subTest(dataset=dataset_key):
                self.assertIsInstance(
                    dataset["has_prefecture"],
                    bool,
                    f"{dataset_key}: has_prefecture must be boolean",
                )

    def test_prefecture_aware_url_contains_placeholder(self):
        """Verify that prefecture-aware dataset URLs contain {pref_code}"""
        for dataset_key, dataset in DATASETS.items():
            if dataset["has_prefecture"]:
                with self.subTest(dataset=dataset_key):
                    self.assertIn(
                        "{pref_code}",
                        dataset["url"],
                        f"{dataset_key}: Prefecture-aware dataset must include {{pref_code}} in URL",
                    )

    def test_non_prefecture_url_no_placeholder(self):
        """Verify that non-prefecture dataset URLs do not contain {pref_code}"""
        for dataset_key, dataset in DATASETS.items():
            if not dataset["has_prefecture"]:
                with self.subTest(dataset=dataset_key):
                    self.assertNotIn(
                        "{pref_code}",
                        dataset["url"],
                        f"{dataset_key}: Non-prefecture dataset must not include {{pref_code}} in URL",
                    )

    def test_dataset_keys_unique(self):
        """Verify that dataset keys are unique"""
        keys = list(DATASETS.keys())
        unique_keys = set(keys)
        self.assertEqual(
            len(keys),
            len(unique_keys),
            f"Dataset keys must be unique. Duplicates: {[k for k in keys if keys.count(k) > 1]}",
        )

    def test_dataset_names_unique(self):
        """Verify that dataset names are unique"""
        names = [dataset["name"] for dataset in DATASETS.values()]
        unique_names = set(names)
        duplicates = [name for name in names if names.count(name) > 1]
        self.assertEqual(
            len(names),
            len(unique_names),
            f"Dataset names must be unique. Duplicates: {set(duplicates)}",
        )

    def test_prefecture_placeholder_format(self):
        """Verify that URL prefecture placeholder has correct format"""
        for dataset_key, dataset in DATASETS.items():
            if dataset["has_prefecture"]:
                with self.subTest(dataset=dataset_key):
                    url = dataset["url"]
                    # Verify that {pref_code} appears exactly once
                    count = url.count("{pref_code}")
                    self.assertEqual(
                        count,
                        1,
                        f"{dataset_key}: URL must contain exactly one {{pref_code}} placeholder",
                    )
                    # Verify no other curly braces exist
                    self.assertEqual(
                        url.count("{"),
                        1,
                        f"{dataset_key}: URL must not contain other placeholders",
                    )
                    self.assertEqual(
                        url.count("}"),
                        1,
                        f"{dataset_key}: URL must not contain other placeholders",
                    )


class TestPrefectures(unittest.TestCase):
    """Test PREFECTURES structure and consistency"""

    def test_prefectures_not_empty(self):
        """Verify that prefecture data is not empty"""
        self.assertTrue(PREFECTURES, "PREFECTURES must not be empty")
        self.assertEqual(
            len(PREFECTURES), 47, "PREFECTURES must contain exactly 47 entries"
        )

    def test_no_placeholder_prefecture(self):
        """Verify that placeholder prefecture (00) does not exist"""
        self.assertNotIn("00", PREFECTURES, "Prefecture code '00' must not exist")

    def test_all_prefectures_exist(self):
        """Verify that all 47 prefectures exist"""
        for i in range(1, 48):
            code = f"{i:02d}"
            with self.subTest(code=code):
                self.assertIn(
                    code,
                    PREFECTURES,
                    f"Prefecture code '{code}' must exist",
                )

    def test_prefecture_codes_are_strings(self):
        """Verify that prefecture codes are strings"""
        for code in PREFECTURES.keys():
            with self.subTest(code=code):
                self.assertIsInstance(code, str, f"Code {code} must be a string")
                self.assertEqual(len(code), 2, f"Code {code} must be 2 characters long")
                self.assertTrue(code.isdigit(), f"Code {code} must contain only digits")

    def test_prefecture_names_are_strings(self):
        """Verify that prefecture names are strings"""
        for code, name in PREFECTURES.items():
            with self.subTest(code=code):
                self.assertIsInstance(name, str, f"Name for {code} must be a string")
                self.assertGreater(len(name), 0, f"Name for {code} must not be empty")

    def test_prefecture_codes_unique(self):
        """Verify that prefecture codes are unique"""
        codes = list(PREFECTURES.keys())
        unique_codes = set(codes)
        self.assertEqual(
            len(codes),
            len(unique_codes),
            "Prefecture codes must be unique",
        )

    def test_prefecture_names_unique(self):
        """Verify that prefecture names are unique"""
        names = list(PREFECTURES.values())
        unique_names = set(names)
        self.assertEqual(
            len(names),
            len(unique_names),
            "Prefecture names must be unique",
        )

    def test_key_prefectures_present(self):
        """Verify that key prefectures are present"""
        key_prefectures = {
            "01": "北海道",
            "13": "東京都",
            "27": "大阪府",
            "47": "沖縄県",
        }
        for code, expected_name in key_prefectures.items():
            with self.subTest(code=code):
                self.assertIn(code, PREFECTURES, f"Prefecture code '{code}' must exist")
                self.assertEqual(
                    PREFECTURES[code],
                    expected_name,
                    f"Prefecture code '{code}' must be '{expected_name}'",
                )


class TestAlgorithmIntegration(unittest.TestCase):
    """Integration tests related to algorithm implementation"""

    def test_prefecture_url_formatting(self):
        """Verify that URL formatting with prefecture codes works correctly"""
        for dataset_key, dataset in DATASETS.items():
            if dataset["has_prefecture"]:
                with self.subTest(dataset=dataset_key):
                    # Verify that formatting works correctly for each prefecture code
                    for pref_code in ["01", "13", "47"]:
                        try:
                            formatted_url = dataset["url"].format(pref_code=pref_code)
                            self.assertNotIn(
                                "{pref_code}",
                                formatted_url,
                                f"{dataset_key}: URL formatting failed for {pref_code}",
                            )
                            self.assertIn(
                                pref_code,
                                formatted_url,
                                f"{dataset_key}: Formatted URL must contain {pref_code}",
                            )
                        except KeyError as e:
                            self.fail(
                                f"{dataset_key}: URL formatting failed with KeyError: {e}"
                            )

    def test_hokkaido_vg_50000_special_case(self):
        """Test special handling for Hokkaido vg_50000 dataset"""
        # Corresponds to processing at algorithm.py lines 100-101
        if "vg_50000" in DATASETS:
            dataset = DATASETS["vg_50000"]
            self.assertTrue(
                dataset["has_prefecture"],
                "vg_50000 must be a prefecture-aware dataset",
            )
            # Verify that formatting works with Hokkaido code "01"
            url_template = dataset["url"]
            formatted_url = url_template.format(pref_code="01_0420")
            self.assertIn("01_0420", formatted_url)

    def test_dataset_count_reasonable(self):
        """Verify that dataset count is reasonable"""
        # Verify that minimum datasets exist
        self.assertGreater(
            len(DATASETS),
            10,
            "Should have more than 10 datasets",
        )

    def test_prefecture_aware_datasets_exist(self):
        """Verify that prefecture-aware datasets exist"""
        prefecture_aware = [ds for ds in DATASETS.values() if ds["has_prefecture"]]
        self.assertGreater(
            len(prefecture_aware),
            0,
            "Should have at least one prefecture-aware dataset",
        )

    def test_non_prefecture_datasets_exist(self):
        """Verify that non-prefecture datasets exist"""
        non_prefecture = [ds for ds in DATASETS.values() if not ds["has_prefecture"]]
        self.assertGreater(
            len(non_prefecture),
            0,
            "Should have at least one non-prefecture dataset",
        )


if __name__ == "__main__":
    unittest.main()
