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


def _centers(size, count, diameter, margin):
    if count < 1:
        raise RuntimeError("Hole count must be positive")
    radius = diameter / 2.0
    available = size - 2.0 * margin
    required = count * diameter
    if available < required:
        raise RuntimeError(f"Cannot fit {count} x Ø{diameter:.1f} mm holes in {size:.1f} mm with {margin:.1f} mm margin")
    if count == 1:
        return [size / 2.0]
    start = margin + radius
    end = size - margin - radius
    step = (end - start) / (count - 1)
    return [start + i * step for i in range(count)]


def create_medicine_box(command):
    """Create Medicine Box v1, or one standalone printable part when command.part is set."""
    part = command.get("part")
    if part:
        from medicine_box_parts import create_medicine_body, create_medicine_cover, create_medicine_plate
        handlers = {"cover": create_medicine_cover, "plate": create_medicine_plate, "body": create_medicine_body}
        if part not in handlers:
            raise RuntimeError("Medicine Box part must be cover, plate, or body")
        return handlers[part](command)

    doc = App.ActiveDocument or App.newDocument("MedicineBoxV1")
    L = float(command.get("length", 120.0))
    W = float(command.get("width", 85.0))
    H = float(command.get("height", 130.0))
    wall = float(command.get("wall", 1.0))
    bottom = float(command.get("bottom_thickness", 1.0))
    plate_z = float(command.get("plate_bottom_z", 70.0))
    plate_t = float(command.get("plate_thickness", 1.0))
    ledge_t = float(command.get("ledge_thickness", 1.0))
    ledge_width = float(command.get("ledge_width", 3.0))
    plate_clearance = float(command.get("plate_clearance_per_side", 0.2))
    hole_d = float(command.get("hole_diameter", 35.0))
    columns = int(command.get("hole_columns", 3))
    rows = int(command.get("hole_rows", 2))
    hole_margin = float(command.get("hole_edge_margin", 6.0))
    cover_clearance = float(command.get("cover_clearance_per_side", 0.25))
    cover_wall = float(command.get("cover_wall", 1.0))
    cover_top = float(command.get("cover_top_thickness", 1.0))
    cover_insertion = float(command.get("cover_insertion_depth", 60.0))
    output_path = os.path.abspath(command.get("output_path", "cad/output/medicine-box-v1.FCStd"))

    if min(L, W, H, wall, bottom, plate_t, ledge_t, ledge_width, hole_d, plate_clearance, cover_clearance, cover_wall, cover_top, cover_insertion) <= 0:
        raise RuntimeError("All dimensions must be positive")
    if wall * 2 >= min(L, W):
        raise RuntimeError("Body wall is too thick for body dimensions")
    if plate_z < bottom or plate_z + plate_t > H:
        raise RuntimeError("Plate position is outside the body")
    if cover_insertion > H:
        raise RuntimeError("Cover insertion depth cannot exceed body height")
    if columns != 3 or rows != 2:
        raise RuntimeError("Medicine Box requires a 3 x 2 hole pattern")

    inner_L = L - 2.0 * wall
    inner_W = W - 2.0 * wall
    plate_L = inner_L - 2.0 * plate_clearance
    plate_W = inner_W - 2.0 * plate_clearance
    plate_x = wall + plate_clearance
    plate_y = wall + plate_clearance
    x_centers_local = _centers(plate_L, columns, hole_d, hole_margin)
    y_centers_local = _centers(plate_W, rows, hole_d, hole_margin)
    x_centers = [plate_x + x for x in x_centers_local]
    y_centers = [plate_y + y for y in y_centers_local]

    if any(x - hole_d / 2.0 < wall for x in x_centers):
        raise RuntimeError("Plate hole violates body-side clearance")

    for name in ("MedicineBody", "MedicinePlate6Holes", "MedicineCover"):
        old = doc.getObject(name)
        if old is not None:
            doc.removeObject(name)

    outer = Part.makeBox(L, W, H)
    cavity = Part.makeBox(inner_L, inner_W, H - bottom, App.Vector(wall, wall, bottom))
    body_shape = outer.cut(cavity)
    ledge_outer = Part.makeBox(inner_L, inner_W, ledge_t, App.Vector(wall, wall, plate_z - ledge_t))
    ledge_inner = Part.makeBox(max(0.01, inner_L - 2.0 * ledge_width), max(0.01, inner_W - 2.0 * ledge_width), ledge_t + 0.2, App.Vector(wall + ledge_width, wall + ledge_width, plate_z - ledge_t - 0.1))
    body_shape = body_shape.fuse(ledge_outer.cut(ledge_inner))
    body = doc.addObject("Part::Feature", "MedicineBody")
    body.Label = f"Medicine Box Body {L:.0f}x{W:.0f}x{H:.0f} mm"
    body.Shape = body_shape

    plate_shape = Part.makeBox(plate_L, plate_W, plate_t, App.Vector(plate_x, plate_y, plate_z))
    for x in x_centers:
        for y in y_centers:
            hole = Part.makeCylinder(hole_d / 2.0, plate_t + 2.0, App.Vector(x, y, plate_z - 1.0), App.Vector(0, 0, 1))
            plate_shape = plate_shape.cut(hole)
    plate = doc.addObject("Part::Feature", "MedicinePlate6Holes")
    plate.Label = "Medicine Plate 6 Holes - 2x3 - Ø35 mm"
    plate.Shape = plate_shape

    cover_outer_L = L + 2.0 * (cover_wall + cover_clearance)
    cover_outer_W = W + 2.0 * (cover_wall + cover_clearance)
    cover_H = cover_insertion + cover_top
    cover_x = -(cover_outer_L - L) / 2.0
    cover_y = -(cover_outer_W - W) / 2.0
    cover_z = H - cover_insertion
    cover_inner_L = L + 2.0 * cover_clearance
    cover_inner_W = W + 2.0 * cover_clearance
    cover_outer = Part.makeBox(cover_outer_L, cover_outer_W, cover_H, App.Vector(cover_x, cover_y, cover_z))
    cover_cavity = Part.makeBox(cover_inner_L, cover_inner_W, cover_insertion, App.Vector(cover_x + cover_wall, cover_y + cover_wall, cover_z))
    cover_shape = cover_outer.cut(cover_cavity)
    cover = doc.addObject("Part::Feature", "MedicineCover")
    cover.Label = f"Medicine Box Cover - {cover_insertion:.0f} mm insertion"
    cover.Shape = cover_shape

    for obj, props in (
        (body, (("Length", L), ("Width", W), ("Height", H), ("WallThickness", wall), ("BottomThickness", bottom), ("PlateLedgeZ", plate_z), ("PlateLedgeThickness", ledge_t), ("PlateLedgeWidth", ledge_width))),
        (plate, (("Length", plate_L), ("Width", plate_W), ("Thickness", plate_t), ("BottomZ", plate_z), ("ClearancePerSide", plate_clearance), ("HoleDiameter", hole_d), ("HoleEdgeMargin", hole_margin))),
        (cover, (("Length", cover_outer_L), ("Width", cover_outer_W), ("Height", cover_H), ("WallThickness", cover_wall), ("TopThickness", cover_top), ("InsertionDepth", cover_insertion), ("ClearancePerSide", cover_clearance))),
    ):
        for name, value in props:
            obj.addProperty("App::PropertyLength", name, "Dimensions")
            setattr(obj, name, value)

    plate.addProperty("App::PropertyString", "HolePattern", "Design")
    plate.HolePattern = "3 columns x 2 rows; 6 x Ø35 mm; holes face TOP"
    plate.addProperty("App::PropertyString", "Fit", "Design")
    plate.Fit = f"Removable; {plate_clearance:.2f} mm clearance per side"
    plate.addProperty("App::PropertyString", "HoleCenters", "Design")
    plate.HoleCenters = "X=" + ", ".join(f"{v:.2f}" for v in x_centers) + " mm; Y=" + ", ".join(f"{v:.2f}" for v in y_centers) + " mm"
    body.addProperty("App::PropertyString", "PlateSupport", "Design")
    body.PlateSupport = "Continuous 1 mm thick ledge on all four inner sides"
    cover.addProperty("App::PropertyString", "Fit", "Design")
    cover.Fit = f"Outer cap; {cover_clearance:.2f} mm clearance per side"
    cover.addProperty("App::PropertyString", "Insertion", "Design")
    cover.Insertion = f"Body enters cover {cover_insertion:.0f} mm"

    doc.recompute()
    for obj in (body, plate, cover):
        if not obj.Shape.isValid():
            raise RuntimeError(f"Invalid generated geometry: {obj.Name}")
    if not body.Shape.Solids or not plate.Shape.Solids or not cover.Shape.Solids:
        raise RuntimeError("Every Medicine Box part must contain a printable solid")

    plate_box = Part.makeBox(plate_L, plate_W, plate_t, App.Vector(plate_x, plate_y, plate_z))
    body_inner_box = Part.makeBox(inner_L, inner_W, H - bottom, App.Vector(wall, wall, bottom))
    if not plate_box.common(body_inner_box).isValid():
        raise RuntimeError("Plate/body fit validation failed")

    _fit_view(doc)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    doc.saveAs(output_path)
    return {
        "ok": True,
        "action": "create_medicine_box",
        "document": doc.Name,
        "output_path": output_path,
        "parts": ["MedicineBody", "MedicinePlate6Holes", "MedicineCover"],
        "body": {"length": L, "width": W, "height": H, "wall": wall, "plate_ledge_z": plate_z, "plate_ledge_thickness": ledge_t, "plate_ledge_width": ledge_width},
        "plate": {"length": plate_L, "width": plate_W, "thickness": plate_t, "bottom_z": plate_z, "clearance_per_side": plate_clearance, "hole_diameter": hole_d, "hole_count": 6, "pattern": "3 x 2", "hole_centers_x": x_centers, "hole_centers_y": y_centers},
        "cover": {"length": cover_outer_L, "width": cover_outer_W, "height": cover_H, "wall": cover_wall, "top": cover_top, "insertion_depth": cover_insertion, "clearance_per_side": cover_clearance},
        "printability": {"separate_parts": True, "plate_body_clearance_validated": True, "intended_orientation": "body upright; plate horizontal; cover upright", "support_required_by_design": False},
    }
