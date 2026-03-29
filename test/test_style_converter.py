import base64
import unittest

from qgis.PyQt.QtCore import QBuffer, QByteArray, QIODevice
from qgis.PyQt.QtGui import QColor, QImage

from data_loader.style_converter import PIXEL_SIZE, _analyze_tile


def _make_tile_b64(width, height, bg_color, fg_pixels=None, extra_pixels=None):
    """Create a test tile image and return its base64-encoded PNG data.

    Args:
        width: Tile width in pixels
        height: Tile height in pixels
        bg_color: QColor for background
        fg_pixels: List of (x, y) tuples for foreground pixels (black by default)
        extra_pixels: List of (x, y, QColor) tuples for additional colored pixels
    """
    fmt = (
        QImage.Format.Format_ARGB32
        if hasattr(QImage, "Format")
        else QImage.Format_ARGB32
    )
    img = QImage(width, height, fmt)
    img.fill(bg_color)

    if fg_pixels:
        for x, y in fg_pixels:
            img.setPixelColor(x, y, QColor(0, 0, 0, 255))

    if extra_pixels:
        for x, y, color in extra_pixels:
            img.setPixelColor(x, y, color)

    ba = QByteArray()
    buf = QBuffer(ba)
    buf.open(
        QIODevice.OpenModeFlag.WriteOnly
        if hasattr(QIODevice, "OpenModeFlag")
        else QIODevice.WriteOnly
    )
    img.save(buf, "PNG")
    buf.close()

    return base64.b64encode(bytes(ba)).decode("ascii")


class TestAnalyzeTile12x12TypeA(unittest.TestCase):
    """12x12 Type A: evenly-spaced dot grid at even rows/cols"""

    def setUp(self):
        even_coords = [0, 2, 4, 6, 8, 10]
        fg_pixels = [(x, y) for y in even_coords for x in even_coords]
        self.b64 = _make_tile_b64(12, 12, QColor(255, 255, 255, 255), fg_pixels)

    def test_type(self):
        info = _analyze_tile(self.b64)
        self.assertEqual(info["type"], "dot_grid")  # type: ignore

    def test_dimensions(self):
        info = _analyze_tile(self.b64)
        self.assertEqual(info["w"], 12)  # type: ignore
        self.assertEqual(info["h"], 12)  # type: ignore

    def test_spacing(self):
        info = _analyze_tile(self.b64)
        self.assertAlmostEqual(info["dx"], 2 * PIXEL_SIZE)  # type: ignore
        self.assertAlmostEqual(info["dy"], 2 * PIXEL_SIZE)  # type: ignore
        self.assertAlmostEqual(info["disp_x"], 0)  # type: ignore
        self.assertAlmostEqual(info["marker"], PIXEL_SIZE)  # type: ignore

    def test_colors(self):
        info = _analyze_tile(self.b64)
        self.assertEqual(info["bg"], (255, 255, 255, 255))  # type: ignore
        self.assertEqual(info["fg"], (0, 0, 0, 255))  # type: ignore


class TestAnalyzeTile12x12TypeB(unittest.TestCase):
    """12x12 Type B: staggered diagonal dots"""

    def setUp(self):
        a_rows = [0, 4, 8]
        a_cols = [0, 4, 8]
        b_rows = [2, 6, 10]
        b_cols = [2, 6, 10]
        fg_pixels = [(x, y) for y in a_rows for x in a_cols]
        fg_pixels += [(x, y) for y in b_rows for x in b_cols]
        self.b64 = _make_tile_b64(12, 12, QColor(255, 255, 255, 255), fg_pixels)

    def test_type(self):
        info = _analyze_tile(self.b64)
        self.assertEqual(info["type"], "dot_staggered")  # type: ignore

    def test_spacing(self):
        info = _analyze_tile(self.b64)
        self.assertAlmostEqual(info["dx"], 4 * PIXEL_SIZE)  # type: ignore
        self.assertAlmostEqual(info["dy"], 2 * PIXEL_SIZE)  # type: ignore
        self.assertAlmostEqual(info["disp_x"], 2 * PIXEL_SIZE)  # type: ignore
        self.assertAlmostEqual(info["marker"], PIXEL_SIZE)  # type: ignore


class TestAnalyzeTile12x12TypeD(unittest.TestCase):
    """12x12 Type D: sparse dots on rows {2, 6, 10}"""

    def setUp(self):
        d_rows_a = [2, 10]
        d_rows_b = [6]
        fg_pixels = [(x, y) for y in d_rows_a for x in [0, 4, 8]]
        fg_pixels += [(x, y) for y in d_rows_b for x in [2, 6, 10]]
        self.b64 = _make_tile_b64(12, 12, QColor(255, 255, 255, 255), fg_pixels)

    def test_type(self):
        info = _analyze_tile(self.b64)
        self.assertEqual(info["type"], "dot_staggered")  # type: ignore

    def test_spacing(self):
        info = _analyze_tile(self.b64)
        self.assertAlmostEqual(info["dx"], 4 * PIXEL_SIZE)  # type: ignore
        self.assertAlmostEqual(info["dy"], 2 * PIXEL_SIZE)  # type: ignore


class TestAnalyzeTile12x12TypeC(unittest.TestCase):
    """12x12 Type C: base even-row dots + extra rows {3, 7, 11}"""

    def setUp(self):
        even_coords = [0, 2, 4, 6, 8, 10]
        # Base dots at all even rows/cols
        fg_pixels = [(x, y) for y in even_coords for x in even_coords]
        # Extra dots at rows 3, 7, 11 with cols [1, 5, 9]
        extra_cols = [1, 5, 9]
        fg_pixels += [(x, y) for y in [3, 7, 11] for x in extra_cols]
        self.b64 = _make_tile_b64(12, 12, QColor(255, 255, 255, 255), fg_pixels)

    def test_type(self):
        info = _analyze_tile(self.b64)
        self.assertEqual(info["type"], "dot_grid_plus")  # type: ignore

    def test_base_spacing(self):
        info = _analyze_tile(self.b64)
        self.assertAlmostEqual(info["dx"], 2 * PIXEL_SIZE)  # type: ignore
        self.assertAlmostEqual(info["dy"], 2 * PIXEL_SIZE)  # type: ignore

    def test_extra_spacing(self):
        info = _analyze_tile(self.b64)
        # extra_cols = [1, 5, 9] -> spacing = 5 - 1 = 4
        self.assertAlmostEqual(info["extra_dx"], 4 * PIXEL_SIZE)  # type: ignore
        self.assertAlmostEqual(info["extra_dy"], 4 * PIXEL_SIZE)  # type: ignore
        self.assertAlmostEqual(info["extra_offset_x"], 1 * PIXEL_SIZE)  # type: ignore
        self.assertAlmostEqual(info["extra_offset_y"], 3 * PIXEL_SIZE)  # type: ignore


class TestAnalyzeTile12x12Fallback(unittest.TestCase):
    """12x12 fallback: density-based approximation for unrecognized patterns"""

    def setUp(self):
        # Irregular pattern that doesn't match any specific type
        fg_pixels = [(0, 0), (5, 3), (11, 7), (2, 9)]
        self.b64 = _make_tile_b64(12, 12, QColor(255, 255, 255, 255), fg_pixels)

    def test_type(self):
        info = _analyze_tile(self.b64)
        self.assertEqual(info["type"], "dot_grid")  # type: ignore

    def test_density_based_spacing(self):
        info = _analyze_tile(self.b64)
        # 4 fg pixels in 144 total -> density ~0.028
        # spacing = (1/sqrt(0.028)) * 0.75 ≈ 4.49
        self.assertGreater(info["dx"], 2)  # type: ignore
        self.assertGreater(info["dy"], 2)  # type: ignore
        self.assertEqual(info["dx"], info["dy"])  # type: ignore


class TestAnalyzeTile40x40(unittest.TestCase):
    """40x40 tile: diamond hatch"""

    def setUp(self):
        # Just need a 40x40 image with at least 2 colors
        fg_pixels = [(0, 0), (20, 20)]
        self.b64 = _make_tile_b64(40, 40, QColor(200, 200, 200, 255), fg_pixels)

    def test_type(self):
        info = _analyze_tile(self.b64)
        self.assertEqual(info["type"], "diamond_hatch")  # type: ignore

    def test_dimensions(self):
        info = _analyze_tile(self.b64)
        self.assertEqual(info["w"], 40)  # type: ignore
        self.assertEqual(info["h"], 40)  # type: ignore

    def test_line_params(self):
        info = _analyze_tile(self.b64)
        self.assertAlmostEqual(info["line_distance"], 5.3)  # type: ignore
        self.assertAlmostEqual(info["line_width"], 2.25)  # type: ignore


class TestAnalyzeTile64x64SemiTransparent(unittest.TestCase):
    """64x64 tile with transparent pixels: semi-transparent hatch"""

    def setUp(self):
        # Background is transparent (alpha=0), foreground is opaque
        transparent = QColor(0, 0, 0, 0)
        opaque_pixels = [(x, y) for y in range(0, 64, 4) for x in range(64)]
        self.b64 = _make_tile_b64(
            64,
            64,
            transparent,
            fg_pixels=None,
            extra_pixels=[(x, y, QColor(100, 50, 50, 255)) for x, y in opaque_pixels],
        )

    def test_type(self):
        info = _analyze_tile(self.b64)
        self.assertEqual(info["type"], "semi_transparent_hatch")  # type: ignore

    def test_line_params(self):
        info = _analyze_tile(self.b64)
        self.assertAlmostEqual(info["line_distance"], 5 * PIXEL_SIZE)  # type: ignore
        self.assertAlmostEqual(info["line_width"], 1 * PIXEL_SIZE)  # type: ignore


class TestAnalyzeTile64x64Tricolor(unittest.TestCase):
    """64x64 tile without transparent pixels: tricolor dot"""

    def setUp(self):
        # All opaque, 3 colors
        bg = QColor(200, 200, 200, 255)
        fg_pixels = [(x, y) for y in range(0, 64, 8) for x in range(0, 64, 8)]
        third_pixels = [
            (x, y, QColor(100, 0, 0, 255))
            for y in range(4, 64, 8)
            for x in range(4, 64, 8)
        ]
        self.b64 = _make_tile_b64(64, 64, bg, fg_pixels, third_pixels)

    def test_type(self):
        info = _analyze_tile(self.b64)
        self.assertEqual(info["type"], "tricolor_dot")  # type: ignore

    def test_spacing(self):
        info = _analyze_tile(self.b64)
        self.assertAlmostEqual(info["dx"], 8 * PIXEL_SIZE)  # type: ignore
        self.assertAlmostEqual(info["dy"], 8 * PIXEL_SIZE)  # type: ignore
        self.assertAlmostEqual(info["disp_x"], 4 * PIXEL_SIZE)  # type: ignore
        self.assertAlmostEqual(info["marker"], 2 * PIXEL_SIZE)  # type: ignore

    def test_has_third_color(self):
        info = _analyze_tile(self.b64)
        self.assertIn("third", info)
        self.assertIn("third_qgis", info)


class TestAnalyzeTile80x80(unittest.TestCase):
    """80x80 tile: sparse dot pair"""

    def setUp(self):
        fg_pixels = [(10, 10), (50, 50)]
        self.b64 = _make_tile_b64(80, 80, QColor(255, 255, 255, 255), fg_pixels)

    def test_type(self):
        info = _analyze_tile(self.b64)
        self.assertEqual(info["type"], "dot_sparse_pair")  # type: ignore

    def test_dimensions(self):
        info = _analyze_tile(self.b64)
        self.assertEqual(info["w"], 80)  # type: ignore
        self.assertEqual(info["h"], 80)  # type: ignore

    def test_spacing(self):
        info = _analyze_tile(self.b64)
        self.assertAlmostEqual(info["dx"], 4 * PIXEL_SIZE)  # type: ignore
        self.assertAlmostEqual(info["dy"], 4 * PIXEL_SIZE)  # type: ignore
        self.assertAlmostEqual(info["marker"], PIXEL_SIZE)  # type: ignore


class TestAnalyzeTileFallbackSize(unittest.TestCase):
    """Unknown tile size: fallback to dot_grid"""

    def setUp(self):
        fg_pixels = [(5, 5), (15, 15)]
        self.b64 = _make_tile_b64(20, 20, QColor(255, 255, 255, 255), fg_pixels)

    def test_type(self):
        info = _analyze_tile(self.b64)
        self.assertEqual(info["type"], "dot_grid")  # type: ignore

    def test_default_spacing(self):
        info = _analyze_tile(self.b64)
        self.assertEqual(info["dx"], 3)  # type: ignore
        self.assertEqual(info["dy"], 3)  # type: ignore
        self.assertEqual(info["disp_x"], 0)  # type: ignore
        self.assertAlmostEqual(info["marker"], PIXEL_SIZE)  # type: ignore


class TestAnalyzeTileInvalidData(unittest.TestCase):
    """Invalid base64 image data: should return safe defaults"""

    def test_invalid_image_returns_defaults(self):
        # Valid base64 but not a valid image format
        b64 = base64.b64encode(b"this is not an image at all").decode()
        info = _analyze_tile(b64)
        self.assertEqual(info["type"], "dot_grid")  # type: ignore
        self.assertEqual(info["w"], 0)  # type: ignore
        self.assertEqual(info["h"], 0)  # type: ignore
        self.assertEqual(info["bg"], (255, 255, 255, 255))  # type: ignore
        self.assertEqual(info["fg"], (0, 0, 0, 255))  # type: ignore
        self.assertEqual(info["dx"], 3)  # type: ignore
        self.assertEqual(info["dy"], 3)  # type: ignore

    def test_empty_string_returns_defaults(self):
        # base64 decode of empty string is empty bytes -> invalid image
        info = _analyze_tile("")
        self.assertEqual(info["type"], "dot_grid")  # type: ignore
        self.assertEqual(info["w"], 0)  # type: ignore


class TestAnalyzeTileColorExtraction(unittest.TestCase):
    """Verify correct color extraction from tiles"""

    def test_bg_is_most_frequent_color(self):
        # Green background with a few red foreground pixels
        bg = QColor(0, 128, 0, 255)
        fg_pixels = [(0, 0), (1, 1)]
        b64 = _make_tile_b64(20, 20, bg, fg_pixels)
        info = _analyze_tile(b64)
        self.assertEqual(info["bg"], (0, 128, 0, 255))  # type: ignore
        self.assertEqual(info["fg"], (0, 0, 0, 255))  # type: ignore

    def test_num_colors_two(self):
        fg_pixels = [(0, 0)]
        b64 = _make_tile_b64(20, 20, QColor(255, 255, 255, 255), fg_pixels)
        info = _analyze_tile(b64)
        self.assertEqual(info["num_colors"], 2)  # type: ignore

    def test_num_colors_three(self):
        bg = QColor(200, 200, 200, 255)
        fg_pixels = [(0, 0)]
        third_pixels = [(5, 5, QColor(100, 0, 0, 255))]
        b64 = _make_tile_b64(20, 20, bg, fg_pixels, third_pixels)
        info = _analyze_tile(b64)
        self.assertGreaterEqual(info["num_colors"], 3)  # type: ignore
        self.assertIn("third", info)


if __name__ == "__main__":
    unittest.main()
