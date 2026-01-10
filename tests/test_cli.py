import argparse
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ofmx2pgsql import cli


class CliTests(unittest.TestCase):
    def test_build_parser_returns_argparse_parser(self) -> None:
        parser = cli.build_parser()
        self.assertIsInstance(parser, argparse.ArgumentParser)

    def test_scan_flag_runs(self) -> None:
        exit_code = cli.main(["scan", "ofmx_lk/isolated"])
        self.assertEqual(exit_code, 0)

    def test_apply_config_populates_defaults(self) -> None:
        with tempfile.NamedTemporaryFile("w", delete=False) as handle:
            handle.write(
                "[ofmx2pgsql]\n"
                "dsn = postgresql://user:pass@localhost:5432/ofmx\n"
                "ofmx = ofmx_lk/isolated/ofmx_lk.ofmx\n"
                "shapes = ofmx_lk/isolated/ofmx_lk_ofmShapeExtension.xml\n"
                "apply_migrations = true\n"
                "schema = custom_schema\n"
            )
            config_path = Path(handle.name)

        try:
            parser = cli.build_parser()
            args = parser.parse_args(["--config", str(config_path), "import"])
            cli._apply_config(args)
            self.assertEqual(args.dsn, "postgresql://user:pass@localhost:5432/ofmx")
            self.assertEqual(args.ofmx, Path("ofmx_lk/isolated/ofmx_lk.ofmx"))
            self.assertEqual(
                args.shapes,
                Path("ofmx_lk/isolated/ofmx_lk_ofmShapeExtension.xml"),
            )
            self.assertTrue(args.apply_migrations)
            self.assertEqual(args.schema, "custom_schema")
        finally:
            config_path.unlink()


if __name__ == "__main__":
    unittest.main()
