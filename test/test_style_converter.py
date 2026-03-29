import base64
import os
import tempfile
import unittest
import xml.etree.ElementTree as ET

from qgis.PyQt.QtCore import QBuffer, QByteArray, QIODevice
from qgis.PyQt.QtGui import QColor, QImage

from data_loader.style_converter import (
    PIXEL_SIZE,
    _analyze_tile,
    _build_line_pattern_fill_layer,
    _build_point_pattern_fill_layer,
    _build_simple_fill_layer,
    _convert_pattern_to_layers,
    _rgba_to_qgis,
    convert_rasterfill_qml,
)


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


class TestRgbaToQgis(unittest.TestCase):
    """Tests for _rgba_to_qgis color conversion"""

    def test_opaque_black(self):
        result = _rgba_to_qgis((0, 0, 0, 255))
        self.assertTrue(result.startswith("0,0,0,255,rgb:"))

    def test_opaque_white(self):
        result = _rgba_to_qgis((255, 255, 255, 255))
        self.assertTrue(result.startswith("255,255,255,255,rgb:"))

    def test_transparent(self):
        result = _rgba_to_qgis((0, 0, 0, 0))
        self.assertTrue(result.startswith("0,0,0,0,rgb:"))

    def test_mid_color(self):
        result = _rgba_to_qgis((128, 64, 32, 200))
        parts = result.split(",rgb:")
        self.assertEqual(parts[0], "128,64,32,200")

    def test_output_format(self):
        result = _rgba_to_qgis((100, 50, 25, 255))
        self.assertIn(",rgb:", result)
        csv_part, rgb_part = result.split(",rgb:")
        self.assertEqual(len(csv_part.split(",")), 4)
        self.assertEqual(len(rgb_part.split(",")), 4)


class TestBuildSimpleFillLayer(unittest.TestCase):
    """Tests for _build_simple_fill_layer"""

    def test_returns_element(self):
        layer = _build_simple_fill_layer("0,0,0,255,rgb:0,0,0,1")
        self.assertIsInstance(layer, ET.Element)
        self.assertEqual(layer.get("class"), "SimpleFill")

    def test_color_set(self):
        color = "128,64,32,255,rgb:0.5,0.25,0.125,1"
        layer = _build_simple_fill_layer(color)
        opt = layer.find("Option")
        color_opt = opt.find("Option[@name='color']")  # type: ignore
        self.assertEqual(color_opt.get("value"), color)  # type: ignore

    def test_outline_style(self):
        layer = _build_simple_fill_layer("0,0,0,255,rgb:0,0,0,1", outline="solid")
        opt = layer.find("Option")
        outline = opt.find("Option[@name='outline_style']")  # type: ignore
        self.assertEqual(outline.get("value"), "solid")  # type: ignore

    def test_fill_style(self):
        layer = _build_simple_fill_layer("0,0,0,255,rgb:0,0,0,1", style="no")
        opt = layer.find("Option")
        style = opt.find("Option[@name='style']")  # type: ignore
        self.assertEqual(style.get("value"), "no")  # type: ignore


class TestBuildPointPatternFillLayer(unittest.TestCase):
    """Tests for _build_point_pattern_fill_layer"""

    def test_returns_element(self):
        info = {
            "dx": 3,
            "dy": 3,
            "disp_x": 0,
            "marker": 0.75,
            "fg_qgis": "0,0,0,255,rgb:0,0,0,1",
        }
        layer = _build_point_pattern_fill_layer("sym0", 1, info)
        self.assertEqual(layer.get("class"), "PointPatternFill")

    def test_contains_marker_symbol(self):
        info = {
            "dx": 3,
            "dy": 3,
            "disp_x": 0,
            "marker": 0.75,
            "fg_qgis": "0,0,0,255,rgb:0,0,0,1",
        }
        layer = _build_point_pattern_fill_layer("sym0", 1, info)
        marker_sym = layer.find("symbol[@type='marker']")
        self.assertIsNotNone(marker_sym)
        self.assertEqual(marker_sym.get("name"), "@sym0@1")  # type: ignore

    def test_explicit_params_override_info(self):
        info = {
            "dx": 3,
            "dy": 3,
            "disp_x": 0,
            "marker": 0.75,
            "fg_qgis": "0,0,0,255,rgb:0,0,0,1",
        }
        layer = _build_point_pattern_fill_layer(
            "sym0", 1, info, dx=5, dy=6, disp_x=1, marker_size=2
        )
        opt = layer.find("Option")
        dx_opt = opt.find("Option[@name='distance_x']")  # type: ignore
        dy_opt = opt.find("Option[@name='distance_y']")  # type: ignore
        self.assertEqual(dx_opt.get("value"), "5")  # type: ignore
        self.assertEqual(dy_opt.get("value"), "6")  # type: ignore


class TestBuildLinePatternFillLayer(unittest.TestCase):
    """Tests for _build_line_pattern_fill_layer"""

    def test_returns_element(self):
        layer = _build_line_pattern_fill_layer(
            "sym0", 1, 45, 5.3, 2.25, "0,0,0,255,rgb:0,0,0,1"
        )
        self.assertEqual(layer.get("class"), "LinePatternFill")

    def test_contains_line_symbol(self):
        layer = _build_line_pattern_fill_layer(
            "sym0", 2, 135, 5.3, 2.25, "0,0,0,255,rgb:0,0,0,1"
        )
        line_sym = layer.find("symbol[@type='line']")
        self.assertIsNotNone(line_sym)
        self.assertEqual(line_sym.get("name"), "@sym0@2")  # type: ignore

    def test_angle_and_distance(self):
        layer = _build_line_pattern_fill_layer(
            "sym0", 1, 45, 5.3, 2.25, "0,0,0,255,rgb:0,0,0,1"
        )
        opt = layer.find("Option")
        angle = opt.find("Option[@name='angle']")  # type: ignore
        dist = opt.find("Option[@name='distance']")  # type: ignore
        self.assertEqual(angle.get("value"), "45")  # type: ignore
        self.assertEqual(dist.get("value"), "5.3")  # type: ignore


class TestConvertPatternToLayers(unittest.TestCase):
    """Tests for _convert_pattern_to_layers"""

    def _make_info(self, ptype, **kwargs):
        base = {
            "type": ptype,
            "bg_qgis": "255,255,255,255,rgb:1,1,1,1",
            "fg_qgis": "0,0,0,255,rgb:0,0,0,1",
            "dx": 3,
            "dy": 3,
            "disp_x": 0,
            "marker": PIXEL_SIZE,
        }
        base.update(kwargs)
        return base

    def test_dot_grid_produces_two_layers(self):
        info = self._make_info("dot_grid")
        layers = _convert_pattern_to_layers("sym0", info)
        self.assertEqual(len(layers), 2)
        self.assertEqual(layers[0].get("class"), "SimpleFill")
        self.assertEqual(layers[1].get("class"), "PointPatternFill")

    def test_dot_staggered_produces_two_layers(self):
        info = self._make_info("dot_staggered")
        layers = _convert_pattern_to_layers("sym0", info)
        self.assertEqual(len(layers), 2)

    def test_dot_grid_plus_produces_three_layers(self):
        info = self._make_info(
            "dot_grid_plus",
            extra_dx=4 * PIXEL_SIZE,
            extra_dy=4 * PIXEL_SIZE,
            extra_disp_x=0,
            extra_offset_x=1 * PIXEL_SIZE,
            extra_offset_y=3 * PIXEL_SIZE,
        )
        layers = _convert_pattern_to_layers("sym0", info)
        self.assertEqual(len(layers), 3)
        self.assertEqual(layers[1].get("class"), "PointPatternFill")
        self.assertEqual(layers[2].get("class"), "PointPatternFill")

    def test_diamond_hatch_produces_three_layers(self):
        info = self._make_info("diamond_hatch", line_distance=5.3, line_width=2.25)
        layers = _convert_pattern_to_layers("sym0", info)
        self.assertEqual(len(layers), 3)
        self.assertEqual(layers[0].get("class"), "SimpleFill")
        self.assertEqual(layers[1].get("class"), "LinePatternFill")
        self.assertEqual(layers[2].get("class"), "LinePatternFill")

    def test_diamond_hatch_bg_uses_fg_color(self):
        info = self._make_info("diamond_hatch", line_distance=5.3, line_width=2.25)
        layers = _convert_pattern_to_layers("sym0", info)
        bg_opt = layers[0].find("Option/Option[@name='color']")
        self.assertEqual(bg_opt.get("value"), info["fg_qgis"])  # type: ignore

    def test_semi_transparent_hatch_produces_two_layers(self):
        info = self._make_info(
            "semi_transparent_hatch", line_distance=3.75, line_width=0.75
        )
        layers = _convert_pattern_to_layers("sym0", info)
        self.assertEqual(len(layers), 2)
        self.assertEqual(layers[1].get("class"), "LinePatternFill")

    def test_tricolor_dot_with_third_color(self):
        info = self._make_info(
            "tricolor_dot",
            dx=6,
            dy=6,
            disp_x=3,
            marker=1.5,
            third_qgis="100,0,0,255,rgb:0.39,0,0,1",
        )
        layers = _convert_pattern_to_layers("sym0", info)
        self.assertEqual(len(layers), 3)
        self.assertEqual(layers[1].get("class"), "PointPatternFill")
        self.assertEqual(layers[2].get("class"), "PointPatternFill")

    def test_tricolor_dot_without_third_color(self):
        info = self._make_info("tricolor_dot", dx=6, dy=6, disp_x=3, marker=1.5)
        layers = _convert_pattern_to_layers("sym0", info)
        self.assertEqual(len(layers), 2)

    def test_dot_sparse_pair_produces_two_layers(self):
        info = self._make_info("dot_sparse_pair")
        layers = _convert_pattern_to_layers("sym0", info)
        self.assertEqual(len(layers), 2)


class TestConvertRasterfillQml(unittest.TestCase):
    """Tests for convert_rasterfill_qml (public entry point)"""

    def _make_b64_tile(self):
        fmt = (
            QImage.Format.Format_ARGB32
            if hasattr(QImage, "Format")
            else QImage.Format_ARGB32
        )
        img = QImage(12, 12, fmt)
        img.fill(QColor(255, 255, 255, 255))
        img.setPixelColor(0, 0, QColor(0, 0, 0, 255))
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

    def _write_qml(self, content):
        fd, path = tempfile.mkstemp(suffix=".qml")
        os.close(fd)
        with open(path, "w") as f:
            f.write(content)
        return path

    def test_converts_rasterfill_symbol(self):
        b64 = self._make_b64_tile()
        qml = f"""<qgis>
  <renderer-v2>
    <symbols>
      <symbol name="0" type="fill">
        <layer class="RasterFill" enabled="1" pass="0" locked="0" id="test">
          <Option type="Map">
            <Option name="imageFile" value="base64:{b64}" type="QString"/>
          </Option>
        </layer>
      </symbol>
    </symbols>
  </renderer-v2>
</qgis>"""
        path = self._write_qml(qml)
        try:
            result = convert_rasterfill_qml(path)
            self.assertTrue(result)
            tree = ET.parse(path)
            root = tree.getroot()
            raster_layers = root.findall(".//layer[@class='RasterFill']")
            self.assertEqual(len(raster_layers), 0)
            simple_fills = root.findall(".//layer[@class='SimpleFill']")
            self.assertGreater(len(simple_fills), 0)
        finally:
            os.unlink(path)

    def test_returns_false_no_symbols(self):
        qml = "<qgis><renderer-v2></renderer-v2></qgis>"
        path = self._write_qml(qml)
        try:
            result = convert_rasterfill_qml(path)
            self.assertFalse(result)
        finally:
            os.unlink(path)

    def test_returns_false_no_rasterfill(self):
        qml = """<qgis>
  <renderer-v2>
    <symbols>
      <symbol name="0" type="fill">
        <layer class="SimpleFill" enabled="1" pass="0" locked="0" id="test">
          <Option type="Map"/>
        </layer>
      </symbol>
    </symbols>
  </renderer-v2>
</qgis>"""
        path = self._write_qml(qml)
        try:
            result = convert_rasterfill_qml(path)
            self.assertFalse(result)
        finally:
            os.unlink(path)

    def test_prepends_doctype(self):
        b64 = self._make_b64_tile()
        qml = f"""<qgis>
  <renderer-v2>
    <symbols>
      <symbol name="0" type="fill">
        <layer class="RasterFill" enabled="1" pass="0" locked="0" id="test">
          <Option type="Map">
            <Option name="imageFile" value="base64:{b64}" type="QString"/>
          </Option>
        </layer>
      </symbol>
    </symbols>
  </renderer-v2>
</qgis>"""
        path = self._write_qml(qml)
        try:
            convert_rasterfill_qml(path)
            with open(path) as f:
                first_line = f.readline()
            self.assertIn("<!DOCTYPE qgis", first_line)
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
