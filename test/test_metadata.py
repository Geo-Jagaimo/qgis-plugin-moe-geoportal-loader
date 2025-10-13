import configparser
import os
import unittest


class TestInit(unittest.TestCase):
    """Test that the plugin init is usable for QGIS.
    reference: https://github.com/felt/qgis-plugin/blob/main/felt/test/test_init.py
    """

    def test_read_init(self):
        required_metadata = [
            "name",
            "description",
            "about",
            "version",
            "qgisMinimumVersion",
            "email",
            "author",
        ]

        file_path = os.path.abspath(
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "metadata.txt")
        )
        metadata = []

        class CasePreservingConfigParser(configparser.ConfigParser):
            def optionxform(self, optionstr):
                return str(optionstr)

        parser = CasePreservingConfigParser()
        parser.read(file_path)
        message = 'Cannot find a section named "general" in %s' % file_path
        assert parser.has_section("general"), message
        metadata.extend(parser.items("general"))
        metadata_dict = dict(metadata)
        for expectation in required_metadata:
            message = 'Cannot find metadata "%s" in metadata source (%s).' % (
                expectation,
                file_path,
            )
            self.assertIn(expectation, metadata_dict, message)
            value = metadata_dict.get(expectation, "").strip()
            self.assertTrue(value, f'Metadata "{expectation}" must not be empty')
            if expectation == "email":
                self.assertIn("@", value, 'Metadata "email" must contain "@"')
            if expectation == "qgisMinimumVersion":
                parts = value.split(".")
                self.assertTrue(
                    all(part.isdigit() for part in parts),
                    "qgisMinimumVersion must look like a version number",
                )


if __name__ == "__main__":
    unittest.main()
