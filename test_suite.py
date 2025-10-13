import os
import sys
import unittest


def test_package():
    """Return a test suite for the plugin."""
    test_loader = unittest.TestLoader()
    # Get the directory where this file is located
    test_dir = os.path.dirname(os.path.abspath(__file__))
    test_suite = test_loader.discover(test_dir, pattern="test_*.py")
    return test_suite


if __name__ == "__main__":
    suite = test_package()
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
