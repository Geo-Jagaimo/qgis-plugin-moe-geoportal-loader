import sys
import unittest


def test_package():
    """Return a test suite for the plugin."""
    test_loader = unittest.TestLoader()
    test_suite = test_loader.discover("test", pattern="test_*.py")
    return test_suite


if __name__ == "__main__":
    suite = test_package()
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
