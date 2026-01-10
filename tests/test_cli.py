import argparse
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ofmx2pgsql import cli


class CliTests(unittest.TestCase):
    def test_build_parser_returns_argparse_parser(self) -> None:
        parser = cli.build_parser()
        self.assertIsInstance(parser, argparse.ArgumentParser)

    def test_scan_flag_runs(self) -> None:
        exit_code = cli.main(["--scan", "ofmx_lk/isolated"])
        self.assertEqual(exit_code, 0)


if __name__ == "__main__":
    unittest.main()
