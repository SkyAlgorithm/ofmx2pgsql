from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ofmx2pgsql import parser


class ParserTests(unittest.TestCase):
    def test_iter_ofmx_files_finds_sample(self) -> None:
        paths = list(parser.iter_ofmx_files(Path("ofmx_lk/isolated")))
        self.assertEqual(paths, [Path("ofmx_lk/isolated/ofmx_lk.ofmx")])


if __name__ == "__main__":
    unittest.main()
