import argparse
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ofmx2pgsql import cli

DATA_ROOT = Path("data/ofmx_lk/isolated")
OFMX_FILE = DATA_ROOT / "ofmx_lk.ofmx"
SHAPES_FILE = DATA_ROOT / "ofmx_lk_ofmShapeExtension.xml"

class CliTests(unittest.TestCase):
    def test_build_parser_returns_argparse_parser(self) -> None:
        parser = cli.build_parser()
        self.assertIsInstance(parser, argparse.ArgumentParser)

    @unittest.skipUnless(DATA_ROOT.exists(), "OFMX sample data not available")
    def test_scan_flag_runs(self) -> None:
        exit_code = cli.main(["scan", str(DATA_ROOT)])
        self.assertEqual(exit_code, 0)

    def test_apply_config_populates_defaults(self) -> None:
        with tempfile.NamedTemporaryFile("w", delete=False) as handle:
            handle.write(
                "[ofmx2pgsql]\n"
                "dsn = postgresql://user:pass@localhost:5432/ofmx\n"
                "ofmx = data/ofmx_lk/isolated/ofmx_lk.ofmx\n"
                "shapes = data/ofmx_lk/isolated/ofmx_lk_ofmShapeExtension.xml\n"
                "apply_migrations = true\n"
                "schema = custom_schema\n"
            )
            config_path = Path(handle.name)

        try:
            parser = cli.build_parser()
            args = parser.parse_args(["--config", str(config_path), "import"])
            cli._apply_config(args)
            self.assertEqual(args.dsn, "postgresql://user:pass@localhost:5432/ofmx")
            self.assertEqual(args.ofmx, OFMX_FILE)
            self.assertEqual(
                args.shapes,
                SHAPES_FILE,
            )
            self.assertTrue(args.apply_migrations)
            self.assertEqual(args.schema, "custom_schema")
        finally:
            config_path.unlink()


if __name__ == "__main__":
    unittest.main()
