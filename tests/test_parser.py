from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ofmx2pgsql import parser


class ParserTests(unittest.TestCase):
    def test_iter_ofmx_files_finds_sample(self) -> None:
        paths = list(parser.iter_ofmx_files(Path("ofmx_lk/isolated")))
        self.assertEqual(paths, [Path("ofmx_lk/isolated/ofmx_lk.ofmx")])

    def test_iter_airports_reads_first_airport(self) -> None:
        airports = parser.iter_airports(Path("ofmx_lk/isolated/ofmx_lk.ofmx"))
        first = next(airports)
        self.assertEqual(first.code_id, "LKCB")
        self.assertEqual(first.name, "CHEB")

    def test_iter_waypoints_reads_first_point(self) -> None:
        waypoints = parser.iter_waypoints(Path("ofmx_lk/isolated/ofmx_lk.ofmx"))
        first = next(waypoints)
        self.assertEqual(first.code_id, "ENITA")

    def test_iter_navaids_reads_first_vor(self) -> None:
        navaids = parser.iter_navaids(Path("ofmx_lk/isolated/ofmx_lk.ofmx"))
        first = next(navaids)
        self.assertEqual(first.navaid_type, "VOR")
        self.assertEqual(first.code_id, "OKG")

    def test_iter_airspace_shapes_reads_sample(self) -> None:
        shapes = parser.iter_airspace_shapes(
            Path("ofmx_lk/isolated/ofmx_lk_ofmShapeExtension.xml")
        )
        first = next(shapes)
        self.assertIsNotNone(first.ofmx_id)
        self.assertGreater(len(first.positions), 3)


if __name__ == "__main__":
    unittest.main()
