import os

import FreeCAD as App
import FreeCADGui as Gui
import Part


def _fit_view(doc):
    try:
        gui_doc = Gui.getDocument(doc.Name)
        if gui_doc is not None:
            gui_doc.activeView().viewAxonometric()
            gui_doc.activeView().fitAll()
    except Exception:
        pass


def _center_positions(size, count, diameter, preferred_edge_margin=5.0):
    """Return evenly spaced hole centers with a safe edge margin when possible."""
    if count < 1:
        raise RuntimeError("Hole count must be positive")
    radius = diameter / 2.0
    min_size = count * diameter
    if size < min_size:
        raise RuntimeError(
            f"Cannot fit {count} holes of Ø{diameter:.1f} mm in {size:.1f} mm"
        )
    max_margin = (size - min_size) / 2.0
    margin = min(preferred_edge_margin, max_margin)
    start = radius + margin
    end = size - radius - margin
    if count == 1:
        return [size / 2.0]
    step = (end - start) / (count - 1)
    return [start + index * step for index in range(count)]


def create_large_enclosure(command):
    """Create a large enclosure, or dispatch the Medicine Box design."""
    if command.get("design") == "medicine_box":
        from medicine_box import create_medicine_box
        return create_medicine_box(command)

    doc = App.ActiveDocument
    if doc is None:
        doc = App.newDocument("LargeEnclosure")

    L = float(command.get("length", 200.0))
    W = float(command.get("width", 100.0))
    H = float(command.get("height", 150.0))
    wall = float(command.get("wall", 2.0))
    bottom = float(command.get("bottom_thickness", 2.0))
    lid_L = float(command.get("lid_length", 204.4))
    lid_W = float(command.get("lid_width", 104.4))
    lid_H = float(command.get("lid_height", 60.0))
    lid_wall = float(command.get("lid_wall", 2.0))
    lid_clearance = float(command.get("lid_clearance", 0.2))
    lid_top = float(command.get("lid_top_thickness", 2.0))
    plate_z_center = float(command.get("plate_center_z", H / 2.0))
    plate_t = float(command.get("plate_thickness", 2.0))
    hole_d = float(command.get("hole_diameter", 50.0))
    hole_columns = int(command.get("hole_columns", 3))
    hole_rows = int(command.get("hole_rows", 2))
    hole_edge_margin = float(command.get("hole_edge_margin", 5.0))
    output_path = os.path.abspath(command.get("output_path", "/home/hikmah/projectx/freecad-agent/cad/output/enclosure-final.FCStd"))

    values = (L, W, H, wall, bottom, lid_L, lid_W, lid_H, lid_wall,
              lid_clearance, lid_top, plate_z_center, plate_t, hole_d)
    if min(values) <= 0:
        raise RuntimeError("All enclosure dimensions must be positive")
    if wall * 2 >= min(L, W) or bottom >= H:
        raise RuntimeError("Invalid enclosure wall/bottom thickness")
    if lid_wall * 2 >= min(lid_L, lid_W) or lid_top >= lid_H:
        raise RuntimeError("Invalid lid wall/top thickness")
    if hole_columns != 3 or hole_rows != 2:
        raise RuntimeError("This design requires a 3 x 2 hole pattern")
    if hole_edge_margin < 0:
        raise RuntimeError("Hole edge margin cannot be negative")

    lid_skirt_h = lid_H - lid_top
    expected_inner_L = L + 2.0 * lid_clearance
    expected_inner_W = W + 2.0 * lid_clearance
    expected_outer_L = expected_inner_L + 2.0 * lid_wall
    expected_outer_W = expected_inner_W + 2.0 * lid_wall
    if abs(lid_L - expected_outer_L) > 0.01 or abs(lid_W - expected_outer_W) > 0.01:
        raise RuntimeError(
            f"Lid dimensions must be {expected_outer_L:.1f} x {expected_outer_W:.1f} mm "
            f"for {lid_clearance:.1f} mm/side clearance and {lid_wall:.1f} mm walls"
        )

    plate_L = L
    plate_W = W
    plate_z = plate_z_center - plate_t / 2.0
    if plate_z <= bottom or plate_z + plate_t >= H:
        raise RuntimeError("Internal plate position is outside the enclosure")

    x_centers = _center_positions(L, hole_columns, hole_d, hole_edge_margin)
    y_centers = _center_positions(W, hole_rows, hole_d, hole_edge_margin)

    for name in ("LargeBoxBase", "InternalTopPlate", "LargeBoxLid"):
        old = doc.getObject(name)
        if old is not None:
            doc.removeObject(old.Name)

    outer = Part.makeBox(L, W, H)
    inner = Part.makeBox(L - 2 * wall, W - 2 * wall, H - bottom, App.Vector(wall, wall, bottom))
    base_shape = outer.cut(inner)
    base = doc.addObject("Part::Feature", "LargeBoxBase")
    base.Label = f"Base {L:.0f}x{W:.0f}x{H:.0f} mm - wall {wall:.1f} mm - bottom {bottom:.1f} mm"
    base.Shape = base_shape

    plate_shape = Part.makeBox(plate_L, plate_W, plate_t, App.Vector(0, 0, plate_z))
    for x in x_centers:
        for y in y_centers:
            hole = Part.makeCylinder(hole_d / 2.0, plate_t + 2.0, App.Vector(x, y, plate_z - 1.0), App.Vector(0, 0, 1))
            plate_shape = plate_shape.cut(hole)
    plate = doc.addObject("Part::Feature", "InternalTopPlate")
    plate.Label = f"Internal TOP plate - 6x Ø{hole_d:.0f} mm - no overlap"
    plate.Shape = plate_shape

    lid_x = -(lid_L - L) / 2.0
    lid_y = -(lid_W - W) / 2.0
    lid_z = H - lid_skirt_h
    lid_outer = Part.makeBox(lid_L, lid_W, lid_H, App.Vector(lid_x, lid_y, lid_z))
    lid_inner = Part.makeBox(expected_inner_L, expected_inner_W, lid_skirt_h, App.Vector(lid_x + lid_wall, lid_y + lid_wall, lid_z))
    lid_shape = lid_outer.cut(lid_inner)
    lid = doc.addObject("Part::Feature", "LargeBoxLid")
    lid.Label = f"Lid {lid_L:.1f}x{lid_W:.1f}x{lid_H:.0f} mm - outer cap"
    lid.Shape = lid_shape

    for obj, props in (
        (base, (("Length", L), ("Width", W), ("Height", H), ("WallThickness", wall), ("BottomThickness", bottom))),
        (plate, (("Length", plate_L), ("Width", plate_W), ("Thickness", plate_t), ("CenterZ", plate_z_center), ("HoleDiameter", hole_d))),
        (lid, (("Length", lid_L), ("Width", lid_W), ("Height", lid_H), ("WallThickness", lid_wall), ("TopThickness", lid_top), ("ClearancePerSide", lid_clearance), ("SkirtHeight", lid_skirt_h))),
    ):
        for name, value in props:
            obj.addProperty("App::PropertyLength", name, "Dimensions")
            setattr(obj, name, value)

    plate.addProperty("App::PropertyString", "Orientation", "Design")
    plate.Orientation = "TOP / holes vertical upward"
    plate.addProperty("App::PropertyString", "Mounting", "Design")
    plate.Mounting = "Plate edges touch all four enclosure sides"
    plate.addProperty("App::PropertyString", "HolePattern", "Design")
    plate.HolePattern = f"{hole_columns} columns x {hole_rows} rows, symmetric, 6 x Ø{hole_d:.0f} mm"
    plate.addProperty("App::PropertyString", "HoleCenters", "Design")
    plate.HoleCenters = "X=" + ", ".join(f"{value:.2f}" for value in x_centers) + " mm; Y=" + ", ".join(f"{value:.2f}" for value in y_centers) + " mm"
    plate.addProperty("App::PropertyLength", "HoleEdgeMargin", "Design")
    plate.HoleEdgeMargin = hole_edge_margin
    lid.addProperty("App::PropertyString", "Fit", "Design")
    lid.Fit = f"Removable outer cap; {lid_clearance:.1f} mm clearance per side"
    lid.addProperty("App::PropertyString", "Insertion", "Design")
    lid.Insertion = f"{lid_skirt_h:.0f} mm skirt surrounds the body; {lid_top:.0f} mm top above body"

    doc.recompute()
    if not plate.Shape.isValid():
        raise RuntimeError("Generated internal plate geometry is invalid")
    if not base.Shape.isValid():
        raise RuntimeError("Generated enclosure geometry is invalid")
    if not lid.Shape.isValid():
        raise RuntimeError("Generated lid geometry is invalid")
    _fit_view(doc)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    doc.saveAs(output_path)
    return {
        "ok": True,
        "action": "create_large_enclosure",
        "document": doc.Name,
        "output_path": output_path,
        "box": {"length": L, "width": W, "height": H, "wall": wall, "bottom": bottom},
        "internal_plate": {"length": plate_L, "width": plate_W, "thickness": plate_t, "center_z": plate_z_center, "touches_all_sides": True, "orientation": "TOP", "hole_diameter": hole_d, "hole_pattern": "3 x 2", "hole_count": 6, "hole_centers_x": x_centers, "hole_centers_y": y_centers, "hole_edge_margin": hole_edge_margin},
        "lid": {"length": lid_L, "width": lid_W, "height": lid_H, "wall": lid_wall, "top_thickness": lid_top, "skirt_height": lid_skirt_h, "inner_length": expected_inner_L, "inner_width": expected_inner_W, "clearance_per_side": lid_clearance, "z_min": lid_z, "z_body_top": H, "z_max": H + lid_top, "separate": True},
        "objects": ["LargeBoxBase", "InternalTopPlate", "LargeBoxLid"],
    }
