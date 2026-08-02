"""Unit tests for ExifTool wrapper validation and command construction."""

from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
import tempfile
import unittest
from pathlib import Path


LOADER = SourceFileLoader(
    "exiftool_wrapper_win", str(Path(__file__).with_name("exiftool_wrapper_win.pyw"))
)
SPEC = spec_from_loader(LOADER.name, LOADER)
if SPEC is None:
    raise RuntimeError("Could not load exiftool_wrapper_win.pyw")
WRAPPER = module_from_spec(SPEC)
LOADER.exec_module(WRAPPER)

chunk_paths = WRAPPER.chunk_paths
discover_images = WRAPPER.discover_images
metadata_arguments = WRAPPER.metadata_arguments
parse_coordinates = WRAPPER.parse_coordinates
parse_taken_datetime = WRAPPER.parse_taken_datetime


class MetadataValidationTests(unittest.TestCase):
    def test_parse_taken_datetime_converts_to_exif_format(self) -> None:
        self.assertEqual(
            parse_taken_datetime("2026-08-02", "12:34:56"),
            "2026:08:02 12:34:56",
        )

    def test_parse_taken_datetime_rejects_invalid_value(self) -> None:
        with self.assertRaisesRegex(ValueError, "YYYY-MM-DD"):
            parse_taken_datetime("2026-02-30", "12:34")

    def test_parse_coordinates_accepts_boundaries(self) -> None:
        self.assertEqual(parse_coordinates("-90", "180"), (-90.0, 180.0))

    def test_parse_coordinates_rejects_out_of_range_values(self) -> None:
        with self.assertRaisesRegex(ValueError, "Latitude"):
            parse_coordinates("90.1", "10")
        with self.assertRaisesRegex(ValueError, "Longitude"):
            parse_coordinates("10", "-180.1")

    def test_parse_coordinates_rejects_non_finite_values(self) -> None:
        with self.assertRaisesRegex(ValueError, "finite"):
            parse_coordinates("nan", "10")
        with self.assertRaisesRegex(ValueError, "finite"):
            parse_coordinates("10", "inf")


class ImageDiscoveryTests(unittest.TestCase):
    def test_discover_images_filters_extensions_and_optionally_recurses(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "photo.JPG").touch()
            (root / "notes.txt").touch()
            nested = root / "nested"
            nested.mkdir()
            (nested / "photo.png").touch()

            self.assertEqual(discover_images(root, recursive=False), [root / "photo.JPG"])
            self.assertEqual(
                discover_images(root, recursive=True),
                [nested / "photo.png", root / "photo.JPG"],
            )


class ExifToolArgumentTests(unittest.TestCase):
    def test_metadata_arguments_sets_hemispheres_and_keeps_backups(self) -> None:
        arguments = metadata_arguments(
            "2026:08:02 12:34:56", -33.5, -70.75, keep_backups=True
        )

        self.assertIn("-FileCreateDate=2026:08:02 12:34:56", arguments)
        self.assertIn("-EXIF:GPSLatitude=33.50000000", arguments)
        self.assertIn("-EXIF:GPSLatitudeRef=S", arguments)
        self.assertIn("-EXIF:GPSLongitude=70.75000000", arguments)
        self.assertIn("-EXIF:GPSLongitudeRef=W", arguments)
        self.assertNotIn("-overwrite_original", arguments)

    def test_metadata_arguments_can_disable_backups(self) -> None:
        arguments = metadata_arguments(
            "2026:08:02 12:34:56", 0.0, 0.0, keep_backups=False
        )

        self.assertIn("-EXIF:GPSLatitudeRef=N", arguments)
        self.assertIn("-EXIF:GPSLongitudeRef=E", arguments)
        self.assertIn("-overwrite_original", arguments)

    def test_chunk_paths_preserves_order_and_splits_at_limit(self) -> None:
        paths = [Path("first.jpg"), Path("second.jpg"), Path("third.jpg")]

        chunks = chunk_paths(paths, ["exiftool", "-argument"], limit=48)

        self.assertGreater(len(chunks), 1)
        self.assertEqual([path for chunk in chunks for path in chunk], paths)


if __name__ == "__main__":
    unittest.main()
