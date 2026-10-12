"""Run the suite, rejecting empty discovery and unresolved expected failures."""

import argparse
import unittest
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument(
    "--test-dir", type=Path, default=Path(__file__).resolve().parent.parent / "tests"
)
args = parser.parse_args()
suite = unittest.defaultTestLoader.discover(str(args.test_dir), pattern="test_*.py")
result = unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(
    0 if result.wasSuccessful() and result.testsRun and not result.expectedFailures else 1
)
