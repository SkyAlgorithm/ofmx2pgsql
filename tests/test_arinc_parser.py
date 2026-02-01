from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ofmx2pgsql import arinc

ARINC_SAMPLE = Path("tests/data/arinc_sample.pc")


class ArincParserTests(unittest.TestCase):
    def test_iter_airports_reads_sample(self) -> None:
        airports = list(arinc.iter_airports(ARINC_SAMPLE))
        self.assertEqual(len(airports), 1)
        self.assertEqual(airports[0].code_icao, "LSGG")

    def test_iter_runways_pairs_sample(self) -> None:
        runways = list(arinc.iter_runways(ARINC_SAMPLE))
        runway_ends = list(arinc.iter_runway_ends(ARINC_SAMPLE))
        self.assertEqual(len(runways), 1)
        self.assertEqual(runways[0].designator, "05/23")
        self.assertEqual(len(runway_ends), 2)

    def test_iter_navaids_reads_sample(self) -> None:
        navaids = list(arinc.iter_navaids(ARINC_SAMPLE))
        self.assertEqual(len(navaids), 1)
        self.assertEqual(navaids[0].code_id, "PAS")
        self.assertAlmostEqual(navaids[0].frequency or 0.0, 116.6, places=1)

    def test_iter_waypoints_reads_sample(self) -> None:
        waypoints = list(arinc.iter_waypoints(ARINC_SAMPLE))
        codes = {point.code_id for point in waypoints}
        self.assertEqual(codes, {"SW", "PLAYA"})

    def test_iter_airspaces_reads_sample(self) -> None:
        airspaces = list(arinc.iter_airspaces(ARINC_SAMPLE))
        self.assertEqual(len(airspaces), 3)
        code_types = {airspace.code_type for airspace in airspaces}
        self.assertIn("L", code_types)
        self.assertIn("R", code_types)
        self.assertIn("F", code_types)


if __name__ == "__main__":
    unittest.main()
