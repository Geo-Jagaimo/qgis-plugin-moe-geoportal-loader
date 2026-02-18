"""
RasterFill to QGIS native symbol conversion module.

Converts RasterFill symbols (base64 tile images) found in QML style files
from the MOE vegetation maps into native QGIS symbols
(SimpleFill + PointPatternFill / LinePatternFill).
"""

import base64
import hashlib
import uuid
import xml.etree.ElementTree as ET

from qgis.PyQt.QtCore import QByteArray
from qgis.PyQt.QtGui import QImage, qAlpha, qBlue, qGreen, qRed

PIXEL_SIZE = 0.75
SCALE_3X = "3x:0,0,0,0,0,0"


def convert_rasterfill_qml(qml_path):
    """Convert RasterFill symbols in a QML file to native QGIS symbols.

    Returns:
        True if conversion was performed, False otherwise.
    """
    tree = ET.parse(qml_path)
    root = tree.getroot()

    symbols = root.find(".//symbols")
    if symbols is None:
        return False

    pattern_cache = {}
    converted = 0

    for symbol in symbols.findall("symbol"):
        sym_name = symbol.get("name", "")
        raster_layers = [
            lyr for lyr in symbol.findall("layer") if lyr.get("class") == "RasterFill"
        ]
        if not raster_layers:
            continue

        for raster_layer in raster_layers:
            b64_data = None
            opt_elem = raster_layer.find("Option")
            if opt_elem is not None:
                for opt in opt_elem:
                    if opt.get("name") == "imageFile":
                        val = opt.get("value", "")
                        if val.startswith("base64:"):
                            b64_data = val[7:]
                        break

            if not b64_data:
                continue

            cache_key = hashlib.md5(b64_data.encode()).hexdigest()
            if cache_key not in pattern_cache:
                pattern_cache[cache_key] = _analyze_tile(b64_data)
            info = pattern_cache[cache_key]

            layer_list = list(symbol)
            raster_idx = layer_list.index(raster_layer)

            new_layers = _convert_pattern_to_layers(sym_name, info)

            symbol.remove(raster_layer)
            for i, nl in enumerate(new_layers):
                symbol.insert(raster_idx + i, nl)

            converted += 1

    if converted == 0:
        return False

    ET.indent(tree, space="  ")
    tree.write(qml_path, encoding="unicode", xml_declaration=False)

    with open(qml_path, "r") as f:
        content = f.read()
    with open(qml_path, "w") as f:
        f.write("<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>\n")
        f.write(content)

    return True


# ===========================================================================
# Utilities
# ===========================================================================


def _rgba_to_qgis(rgba):
    r, g, b, a = int(rgba[0]), int(rgba[1]), int(rgba[2]), int(rgba[3])
    rf, gf, bf, af = r / 255, g / 255, b / 255, a / 255
    return f"{r},{g},{b},{a},rgb:{rf:.7g},{gf:.7g},{bf:.7g},{af:.7g}"


def _new_uuid():
    return "{" + str(uuid.uuid4()) + "}"


def _make_data_defined_properties():
    ddp = ET.Element("data_defined_properties")
    opt = ET.SubElement(ddp, "Option", type="Map")
    ET.SubElement(opt, "Option", value="", type="QString", name="name")
    ET.SubElement(opt, "Option", name="properties")
    ET.SubElement(opt, "Option", value="collection", type="QString", name="type")
    return ddp


# ===========================================================================
# Tile pattern analysis (Qt QImage based)
# ===========================================================================


def _analyze_tile(b64_data):
    raw = base64.b64decode(b64_data)
    ba = QByteArray(raw)
    img = QImage()
    img.loadFromData(ba)
    img = img.convertToFormat(QImage.Format_ARGB32)

    w = img.width()
    h = img.height()

    colors = {}
    for y in range(h):
        for x in range(w):
            px = img.pixel(x, y)
            k = (qRed(px), qGreen(px), qBlue(px), qAlpha(px))
            colors[k] = colors.get(k, 0) + 1

    sorted_colors = sorted(colors.items(), key=lambda x: -x[1])
    bg_color = sorted_colors[0][0]
    fg_color = sorted_colors[1][0] if len(sorted_colors) >= 2 else bg_color

    info = {
        "w": w,
        "h": h,
        "bg": bg_color,
        "fg": fg_color,
        "bg_qgis": _rgba_to_qgis(bg_color),
        "fg_qgis": _rgba_to_qgis(fg_color),
        "num_colors": len(sorted_colors),
    }

    if len(sorted_colors) >= 3:
        info["third"] = sorted_colors[2][0]
        info["third_qgis"] = _rgba_to_qgis(sorted_colors[2][0])

    # Foreground pixel positions
    fg_positions = []
    for y in range(h):
        for x in range(w):
            px = img.pixel(x, y)
            k = (qRed(px), qGreen(px), qBlue(px), qAlpha(px))
            if k == fg_color:
                fg_positions.append((y, x))  # (row, col)

    fg_rows = set(r for r, c in fg_positions)
    row_cols = {}
    for r, c in fg_positions:
        row_cols.setdefault(r, []).append(c)
    for r in row_cols:
        row_cols[r] = sorted(row_cols[r])

    # =============== 12x12 tile ===============
    if w == 12 and h == 12:
        even_rows = {0, 2, 4, 6, 8, 10}
        even_cols = [0, 2, 4, 6, 8, 10]

        # Type A: evenly spaced row dots
        is_a = fg_rows == even_rows and all(
            row_cols.get(r) == even_cols for r in even_rows
        )
        if is_a:
            info["type"] = "dot_grid"
            info["dx"] = 2 * PIXEL_SIZE
            info["dy"] = 2 * PIXEL_SIZE
            info["disp_x"] = 0
            info["marker"] = PIXEL_SIZE
            return info

        # Type B: staggered diagonal dots
        ba_rows = {0, 4, 8}
        bb_rows = {2, 6, 10}
        ba_cols = [0, 4, 8]
        bb_cols = [2, 6, 10]
        is_b = fg_rows == ba_rows | bb_rows and all(
            row_cols.get(r) == ba_cols for r in ba_rows if r in fg_rows
        ) and all(row_cols.get(r) == bb_cols for r in bb_rows if r in fg_rows)
        if is_b:
            info["type"] = "dot_staggered"
            info["dx"] = 4 * PIXEL_SIZE
            info["dy"] = 2 * PIXEL_SIZE
            info["disp_x"] = 2 * PIXEL_SIZE
            info["marker"] = PIXEL_SIZE
            return info

        # Type D: sparse dots
        d_rows = {2, 6, 10}
        is_d = fg_rows == d_rows and all(
            row_cols.get(r) == ba_cols or row_cols.get(r) == bb_cols
            for r in d_rows
            if r in fg_rows
        )
        if is_d:
            info["type"] = "dot_staggered"
            info["dx"] = 4 * PIXEL_SIZE
            info["dy"] = 2 * PIXEL_SIZE
            info["disp_x"] = 2 * PIXEL_SIZE
            info["marker"] = PIXEL_SIZE
            return info

        # Type C: row dots + extra row dots
        extra_rows = {3, 7, 11}
        base_ok = all(
            row_cols.get(r) == even_cols for r in even_rows if r in fg_rows
        )
        has_extra = extra_rows.issubset(fg_rows)
        if base_ok and has_extra:
            extra_cols = row_cols.get(3, [])
            info["type"] = "dot_grid_plus"
            info["dx"] = 2 * PIXEL_SIZE
            info["dy"] = 2 * PIXEL_SIZE
            info["disp_x"] = 0
            info["marker"] = PIXEL_SIZE
            if len(extra_cols) >= 2:
                spacing = extra_cols[1] - extra_cols[0]
            else:
                spacing = 4
            info["extra_dx"] = spacing * PIXEL_SIZE
            info["extra_dy"] = 4 * PIXEL_SIZE
            info["extra_disp_x"] = 0
            info["extra_offset_x"] = extra_cols[0] * PIXEL_SIZE if extra_cols else 0
            info["extra_offset_y"] = 3 * PIXEL_SIZE
            return info

        # Fallback: density-based approximation
        fg_count = len(fg_positions)
        density = fg_count / (w * h)
        spacing = (1.0 / (density**0.5)) * PIXEL_SIZE if density > 0 else 6
        info["type"] = "dot_grid"
        info["dx"] = round(spacing, 2)
        info["dy"] = round(spacing, 2)
        info["disp_x"] = 0
        info["marker"] = PIXEL_SIZE
        return info

    # =============== 40x40 tile: diamond hatch ===============
    if w == 40 and h == 40:
        info["type"] = "diamond_hatch"
        info["line_distance"] = 5.3
        info["line_width"] = 2.25
        return info

    # =============== 64x64 tile ===============
    if w == 64 and h == 64:
        has_transparent = any(color[3] == 0 for color, _ in sorted_colors)
        if has_transparent:
            opaque = [(color, n) for color, n in sorted_colors if color[3] > 0]
            hatch_main = opaque[0][0]
            info["type"] = "semi_transparent_hatch"
            info["fg_qgis"] = _rgba_to_qgis(hatch_main)
            info["fg"] = hatch_main
            info["line_distance"] = 5 * PIXEL_SIZE
            info["line_width"] = 1 * PIXEL_SIZE
            return info
        else:
            info["type"] = "tricolor_dot"
            info["dx"] = 8 * PIXEL_SIZE
            info["dy"] = 8 * PIXEL_SIZE
            info["disp_x"] = 4 * PIXEL_SIZE
            info["marker"] = 2 * PIXEL_SIZE
            return info

    # =============== 80x80 tile ===============
    if w == 80 and h == 80:
        info["type"] = "dot_sparse_pair"
        info["dx"] = 4 * PIXEL_SIZE
        info["dy"] = 4 * PIXEL_SIZE
        info["disp_x"] = 0
        info["marker"] = PIXEL_SIZE
        return info

    # Fallback
    info["type"] = "dot_grid"
    info["dx"] = 3
    info["dy"] = 3
    info["disp_x"] = 0
    info["marker"] = PIXEL_SIZE
    return info


# ===========================================================================
# QML layer builders
# ===========================================================================


def _build_simple_fill_layer(color_qgis, outline="no"):
    layer = ET.Element(
        "layer",
        {
            "pass": "0",
            "locked": "0",
            "class": "SimpleFill",
            "enabled": "1",
            "id": _new_uuid(),
        },
    )
    opt = ET.SubElement(layer, "Option", type="Map")
    ET.SubElement(
        opt,
        "Option",
        value=SCALE_3X,
        type="QString",
        name="border_width_map_unit_scale",
    )
    ET.SubElement(opt, "Option", value=color_qgis, type="QString", name="color")
    ET.SubElement(opt, "Option", value="bevel", type="QString", name="joinstyle")
    ET.SubElement(opt, "Option", value="0,0", type="QString", name="offset")
    ET.SubElement(
        opt, "Option", value=SCALE_3X, type="QString", name="offset_map_unit_scale"
    )
    ET.SubElement(opt, "Option", value="MM", type="QString", name="offset_unit")
    ET.SubElement(
        opt,
        "Option",
        value="0,0,0,255,rgb:0,0,0,1",
        type="QString",
        name="outline_color",
    )
    ET.SubElement(opt, "Option", value=outline, type="QString", name="outline_style")
    ET.SubElement(opt, "Option", value="0", type="QString", name="outline_width")
    ET.SubElement(
        opt, "Option", value="Point", type="QString", name="outline_width_unit"
    )
    ET.SubElement(opt, "Option", value="solid", type="QString", name="style")
    layer.append(_make_data_defined_properties())
    return layer


def _build_point_pattern_fill_layer(
    sym_name,
    layer_idx,
    info,
    dx=None,
    dy=None,
    disp_x=None,
    marker_size=None,
    color_qgis=None,
    offset_x=0,
    offset_y=0,
):
    dx = dx or info.get("dx", 3)
    dy = dy or info.get("dy", 3)
    disp_x = disp_x if disp_x is not None else info.get("disp_x", 0)
    marker_size = marker_size or info.get("marker", PIXEL_SIZE)
    color_qgis = color_qgis or info["fg_qgis"]

    layer = ET.Element(
        "layer",
        {
            "pass": "0",
            "locked": "0",
            "class": "PointPatternFill",
            "enabled": "1",
            "id": _new_uuid(),
        },
    )
    opt = ET.SubElement(layer, "Option", type="Map")

    params = [
        ("angle", "0"),
        ("clip_mode", "0"),
        ("coordinate_reference", "feature"),
        ("displacement_x", str(disp_x)),
        ("displacement_x_map_unit_scale", SCALE_3X),
        ("displacement_x_unit", "Point"),
        ("displacement_y", "0"),
        ("displacement_y_map_unit_scale", SCALE_3X),
        ("displacement_y_unit", "Point"),
        ("distance_x", str(dx)),
        ("distance_x_map_unit_scale", SCALE_3X),
        ("distance_x_unit", "Point"),
        ("distance_y", str(dy)),
        ("distance_y_map_unit_scale", SCALE_3X),
        ("distance_y_unit", "Point"),
        ("offset_x", str(offset_x)),
        ("offset_x_map_unit_scale", SCALE_3X),
        ("offset_x_unit", "Point"),
        ("offset_y", str(offset_y)),
        ("offset_y_map_unit_scale", SCALE_3X),
        ("offset_y_unit", "Point"),
        ("outline_width_map_unit_scale", SCALE_3X),
        ("outline_width_unit", "Point"),
        ("random_deviation_x", "0"),
        ("random_deviation_x_map_unit_scale", SCALE_3X),
        ("random_deviation_x_unit", "Point"),
        ("random_deviation_y", "0"),
        ("random_deviation_y_map_unit_scale", SCALE_3X),
        ("random_deviation_y_unit", "Point"),
        ("seed", "0"),
    ]
    for pname, pval in params:
        ET.SubElement(opt, "Option", value=pval, type="QString", name=pname)

    layer.append(_make_data_defined_properties())

    # Sub-symbol (marker)
    sub_sym_name = f"@{sym_name}@{layer_idx}"
    marker_sym = ET.SubElement(
        layer,
        "symbol",
        {
            "force_rhr": "0",
            "is_animated": "0",
            "type": "marker",
            "clip_to_extent": "1",
            "frame_rate": "10",
            "name": sub_sym_name,
            "alpha": "1",
        },
    )
    marker_sym.append(_make_data_defined_properties())

    marker_layer = ET.SubElement(
        marker_sym,
        "layer",
        {
            "pass": "0",
            "locked": "0",
            "class": "SimpleMarker",
            "enabled": "1",
            "id": _new_uuid(),
        },
    )
    mopt = ET.SubElement(marker_layer, "Option", type="Map")
    marker_params = [
        ("angle", "0"),
        ("cap_style", "square"),
        ("color", color_qgis),
        ("horizontal_anchor_point", "1"),
        ("joinstyle", "bevel"),
        ("name", "square"),
        ("offset", "0,0"),
        ("offset_map_unit_scale", SCALE_3X),
        ("offset_unit", "Point"),
        ("outline_color", color_qgis),
        ("outline_style", "no"),
        ("outline_width", "0"),
        ("outline_width_map_unit_scale", SCALE_3X),
        ("outline_width_unit", "Point"),
        ("scale_method", "diameter"),
        ("size", str(marker_size)),
        ("size_map_unit_scale", SCALE_3X),
        ("size_unit", "Point"),
        ("vertical_anchor_point", "1"),
    ]
    for pname, pval in marker_params:
        ET.SubElement(mopt, "Option", value=pval, type="QString", name=pname)
    marker_layer.append(_make_data_defined_properties())

    return layer


def _build_line_pattern_fill_layer(
    sym_name, layer_idx, angle, distance, line_width, color_qgis
):
    layer = ET.Element(
        "layer",
        {
            "pass": "0",
            "locked": "0",
            "class": "LinePatternFill",
            "enabled": "1",
            "id": _new_uuid(),
        },
    )
    opt = ET.SubElement(layer, "Option", type="Map")
    params = [
        ("angle", str(angle)),
        ("clip_mode", "0"),
        ("coordinate_reference", "feature"),
        ("distance", str(distance)),
        ("distance_map_unit_scale", SCALE_3X),
        ("distance_unit", "Point"),
        ("line_width", str(line_width)),
        ("line_width_map_unit_scale", SCALE_3X),
        ("line_width_unit", "Point"),
        ("offset", "0"),
        ("offset_map_unit_scale", SCALE_3X),
        ("offset_unit", "Point"),
    ]
    for pname, pval in params:
        ET.SubElement(opt, "Option", value=pval, type="QString", name=pname)
    layer.append(_make_data_defined_properties())

    # Sub-symbol (line)
    sub_sym_name = f"@{sym_name}@{layer_idx}"
    line_sym = ET.SubElement(
        layer,
        "symbol",
        {
            "force_rhr": "0",
            "is_animated": "0",
            "type": "line",
            "clip_to_extent": "1",
            "frame_rate": "10",
            "name": sub_sym_name,
            "alpha": "1",
        },
    )
    line_sym.append(_make_data_defined_properties())

    line_layer = ET.SubElement(
        line_sym,
        "layer",
        {
            "pass": "0",
            "locked": "0",
            "class": "SimpleLine",
            "enabled": "1",
            "id": _new_uuid(),
        },
    )
    lopt = ET.SubElement(line_layer, "Option", type="Map")
    line_params = [
        ("align_dash_pattern", "0"),
        ("capstyle", "square"),
        ("customdash", "5;2"),
        ("customdash_map_unit_scale", SCALE_3X),
        ("customdash_unit", "MM"),
        ("dash_pattern_offset", "0"),
        ("dash_pattern_offset_map_unit_scale", SCALE_3X),
        ("dash_pattern_offset_unit", "MM"),
        ("draw_inside_polygon", "0"),
        ("joinstyle", "bevel"),
        ("line_color", color_qgis),
        ("line_style", "solid"),
        ("line_width", str(line_width)),
        ("line_width_unit", "Point"),
        ("offset", "0"),
        ("offset_map_unit_scale", SCALE_3X),
        ("offset_unit", "MM"),
        ("ring_filter", "0"),
        ("trim_distance_end", "0"),
        ("trim_distance_end_map_unit_scale", SCALE_3X),
        ("trim_distance_end_unit", "MM"),
        ("trim_distance_start", "0"),
        ("trim_distance_start_map_unit_scale", SCALE_3X),
        ("trim_distance_start_unit", "MM"),
        ("tweak_dash_pattern_on_corners", "0"),
        ("use_custom_dash", "0"),
        ("width_map_unit_scale", SCALE_3X),
    ]
    for pname, pval in line_params:
        ET.SubElement(lopt, "Option", value=pval, type="QString", name=pname)
    line_layer.append(_make_data_defined_properties())

    return layer


# ===========================================================================
# Pattern to layer conversion
# ===========================================================================


def _convert_pattern_to_layers(sym_name, info, start_layer_idx=0):
    layers = []
    idx = start_layer_idx

    ptype = info["type"]

    # 1) Background color SimpleFill
    bg_layer = _build_simple_fill_layer(info["bg_qgis"], outline="no")
    layers.append(bg_layer)
    idx += 1

    # 2) Pattern layers
    if ptype in ("dot_grid", "dot_staggered"):
        layers.append(
            _build_point_pattern_fill_layer(
                sym_name,
                idx,
                info,
                dx=info["dx"],
                dy=info["dy"],
                disp_x=info["disp_x"],
                marker_size=info["marker"],
                color_qgis=info["fg_qgis"],
            )
        )
        idx += 1

    elif ptype == "dot_grid_plus":
        layers.append(
            _build_point_pattern_fill_layer(
                sym_name,
                idx,
                info,
                dx=info["dx"],
                dy=info["dy"],
                disp_x=0,
                marker_size=info["marker"],
                color_qgis=info["fg_qgis"],
            )
        )
        idx += 1
        layers.append(
            _build_point_pattern_fill_layer(
                sym_name,
                idx,
                info,
                dx=info["extra_dx"],
                dy=info["extra_dy"],
                disp_x=info.get("extra_disp_x", 0),
                marker_size=info["marker"],
                color_qgis=info["fg_qgis"],
                offset_x=info.get("extra_offset_x", 0),
                offset_y=info.get("extra_offset_y", 0),
            )
        )
        idx += 1

    elif ptype == "diamond_hatch":
        layers[0] = _build_simple_fill_layer(info["fg_qgis"], outline="no")
        line_color = info["bg_qgis"]
        dist = info["line_distance"]
        lw = info["line_width"]
        layers.append(
            _build_line_pattern_fill_layer(
                sym_name, idx, angle=45, distance=dist, line_width=lw,
                color_qgis=line_color,
            )
        )
        idx += 1
        layers.append(
            _build_line_pattern_fill_layer(
                sym_name, idx, angle=135, distance=dist, line_width=lw,
                color_qgis=line_color,
            )
        )
        idx += 1

    elif ptype == "semi_transparent_hatch":
        line_color = info["fg_qgis"]
        dist = info["line_distance"]
        lw = info["line_width"]
        layers[0] = _build_simple_fill_layer("0,0,0,0,rgb:0,0,0,0", outline="no")
        for opt_elem in layers[0].iter("Option"):
            if opt_elem.get("name") == "style":
                opt_elem.set("value", "no")
        layers.append(
            _build_line_pattern_fill_layer(
                sym_name, idx, angle=45, distance=dist, line_width=lw,
                color_qgis=line_color,
            )
        )
        idx += 1

    elif ptype == "tricolor_dot":
        layers.append(
            _build_point_pattern_fill_layer(
                sym_name,
                idx,
                info,
                dx=info["dx"],
                dy=info["dy"],
                disp_x=info["disp_x"],
                marker_size=info["marker"],
                color_qgis=info["fg_qgis"],
            )
        )
        idx += 1
        if "third_qgis" in info:
            layers.append(
                _build_point_pattern_fill_layer(
                    sym_name,
                    idx,
                    info,
                    dx=info["dx"] * 2,
                    dy=info["dy"] * 2,
                    disp_x=info["disp_x"],
                    marker_size=info["marker"],
                    color_qgis=info["third_qgis"],
                )
            )
            idx += 1

    elif ptype == "dot_sparse_pair":
        layers.append(
            _build_point_pattern_fill_layer(
                sym_name,
                idx,
                info,
                dx=info["dx"],
                dy=info["dy"],
                disp_x=0,
                marker_size=info["marker"],
                color_qgis=info["fg_qgis"],
            )
        )
        idx += 1

    return layers