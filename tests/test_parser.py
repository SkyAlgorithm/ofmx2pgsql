from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ofmx2pgsql import parser

DATA_ROOT = Path("data/ofmx_lk/isolated")
OFMX_FILE = DATA_ROOT / "ofmx_lk.ofmx"
SHAPES_FILE = DATA_ROOT / "ofmx_lk_ofmShapeExtension.xml"
HAS_DATA = OFMX_FILE.exists() and SHAPES_FILE.exists()

class ParserTests(unittest.TestCase):
    @unittest.skipUnless(DATA_ROOT.exists(), "OFMX sample data not available")
    def test_iter_ofmx_files_finds_sample(self) -> None:
        paths = list(parser.iter_ofmx_files(DATA_ROOT))
        self.assertEqual(paths, [OFMX_FILE])

    @unittest.skipUnless(HAS_DATA, "OFMX sample data not available")
    def test_iter_airports_reads_first_airport(self) -> None:
        airports = parser.iter_airports(OFMX_FILE)
        first = next(airports)
        self.assertEqual(first.code_id, "LKCB")
        self.assertEqual(first.name, "CHEB")

    @unittest.skipUnless(HAS_DATA, "OFMX sample data not available")
    def test_iter_waypoints_reads_first_point(self) -> None:
        waypoints = parser.iter_waypoints(OFMX_FILE)
        first = next(waypoints)
        self.assertEqual(first.code_id, "ENITA")

    @unittest.skipUnless(HAS_DATA, "OFMX sample data not available")
    def test_iter_navaids_reads_first_vor(self) -> None:
        navaids = parser.iter_navaids(OFMX_FILE)
        first = next(navaids)
        self.assertEqual(first.navaid_type, "VOR")
        self.assertEqual(first.code_id, "OKG")

    @unittest.skipUnless(HAS_DATA, "OFMX sample data not available")
    def test_iter_airspace_shapes_reads_sample(self) -> None:
        shapes = parser.iter_airspace_shapes(SHAPES_FILE)
        first = next(shapes)
        self.assertIsNotNone(first.ofmx_id)
        self.assertGreater(len(first.positions), 3)


if __name__ == "__main__":
    unittest.main()
