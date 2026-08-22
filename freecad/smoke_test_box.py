import os

import FreeCAD as App
import FreeCADGui as Gui
import Part


def _fit(doc):
    try:
        gui = Gui.getDocument(doc.Name)
        if gui:
            gui.activeView().viewAxonometric()
            gui.activeView().fitAll()
    except Exception:
        pass


def _solid(obj, name):
    if not obj.Shape.isValid():
        raise RuntimeError(f"Invalid generated geometry: {name}")
    if not obj.Shape.Solids:
        raise RuntimeError(f"Generated part is not a solid: {name}")


def create_smoke_test_box(command):
    """Medicine Box V3 smoke test: same horizontal contract, body height reduced to 50 mm."""
    doc = App.newDocument("SmokeTestBoxV3")

    # V3 contract: body internal cavity is 120 x 85 mm.
    # Plate is 0.3 mm smaller per side so it has 0.3 mm clearance.
    plate_L = float(command.get("plate_length", 119.4))
    plate_W = float(command.get("plate_width", 84.4))
    plate_T = float(command.get("plate_thickness", 3.0))
    plate_clearance = float(command.get("plate_clearance_per_side", 0.3))
    inner_L = 120.0
    inner_W = 85.0
    wall = float(command.get("wall", 3.0))
    body_H = float(command.get("body_height", 50.0))
    bottom = float(command.get("bottom_thickness", 3.0))
    ledge_Z = float(command.get("plate_support_z", 25.0))
    ledge_T = float(command.get("ledge_thickness", 3.0))
    ledge_W = float(command.get("ledge_width", 3.0))
    cover_H = float(command.get("cover_height", 40.0))
    cover_wall = float(command.get("cover_wall", 3.0))
    cover_clearance = float(command.get("cover_clearance_per_side", 0.3))
    cover_top = float(command.get("cover_top_thickness", 3.0))
    output_path = os.path.abspath(command.get("output_path", "cad/output/smoke-test-box-v3.FCStd"))

    if min(plate_L, plate_W, plate_T, plate_clearance, inner_L, inner_W, wall, body_H, bottom, ledge_Z, ledge_T, ledge_W, cover_H, cover_wall, cover_clearance, cover_top) <= 0:
        raise RuntimeError("All dimensions must be positive")
    if abs((inner_L - plate_L) - 2.0 * plate_clearance) > 0.001 or abs((inner_W - plate_W) - 2.0 * plate_clearance) > 0.001:
        raise RuntimeError("Plate clearance does not match V3 contract")
    if body_H <= bottom or ledge_Z + ledge_T > body_H:
        raise RuntimeError("Invalid body/plate support height")
    if cover_top >= cover_H:
        raise RuntimeError("Cover top thickness must be smaller than cover height")

    body_L = inner_L + 2.0 * wall
    body_W = inner_W + 2.0 * wall

    outer = Part.makeBox(body_L, body_W, body_H)
    cavity = Part.makeBox(inner_L, inner_W, body_H - bottom, App.Vector(wall, wall, bottom))
    body_shape = outer.cut(cavity)
    ledge_outer = Part.makeBox(inner_L, inner_W, ledge_T, App.Vector(wall, wall, ledge_Z))
    ledge_inner = Part.makeBox(max(0.01, inner_L - 2.0 * ledge_W), max(0.01, inner_W - 2.0 * ledge_W), ledge_T + 0.2, App.Vector(wall + ledge_W, wall + ledge_W, ledge_Z - 0.1))
    body_shape = body_shape.fuse(ledge_outer.cut(ledge_inner))

    body = doc.addObject("Part::Feature", "SmokeTestBody")
    body.Label = "Smoke-Test V3 Body - 126x91x50 - 3 mm"
    body.Shape = body_shape

    plate_x = wall + plate_clearance
    plate_y = wall + plate_clearance
    plate_shape = Part.makeBox(plate_L, plate_W, plate_T, App.Vector(plate_x, plate_y, ledge_Z + ledge_T))
    # Six-hole V3 pattern: 3 columns x 2 rows, diameter 35 mm.
    hole_d = float(command.get("hole_diameter", 35.0))
    hole_margin_x = (plate_L - 3.0 * hole_d) / 4.0
    hole_margin_y = (plate_W - 2.0 * hole_d) / 3.0
    for row in range(2):
        y = plate_y + hole_margin_y + row * (hole_d + hole_margin_y)
        for col in range(3):
            x = plate_x + hole_margin_x + col * (hole_d + hole_margin_x)
            plate_shape = plate_shape.cut(Part.makeCylinder(hole_d / 2.0, plate_T + 0.2, App.Vector(x, y, ledge_Z + ledge_T - 0.1)))

    plate = doc.addObject("Part::Feature", "SmokeTestPlate")
    plate.Label = "Smoke-Test V3 Plate - 119.4x84.4x3 - 6xØ35"
    plate.Shape = plate_shape

    # Cover follows the V3 body outer footprint with 0.3 mm per-side clearance.
    cover_inner_L = body_L + 2.0 * cover_clearance
    cover_inner_W = body_W + 2.0 * cover_clearance
    cover_outer_L = cover_inner_L + 2.0 * cover_wall
    cover_outer_W = cover_inner_W + 2.0 * cover_wall
    cover_x = -(cover_outer_L - body_L) / 2.0
    cover_y = -(cover_outer_W - body_W) / 2.0
    cover_outer = Part.makeBox(cover_outer_L, cover_outer_W, cover_H, App.Vector(cover_x, cover_y, 0))
    cavity_depth = cover_H - cover_top
    cover_cavity = Part.makeBox(cover_inner_L, cover_inner_W, cavity_depth, App.Vector(cover_x + cover_wall, cover_y + cover_wall, cover_top))
    cover_shape = cover_outer.cut(cover_cavity)

    cover = doc.addObject("Part::Feature", "SmokeTestCover")
    cover.Label = "Smoke-Test V3 Cover - 40 mm - 3 mm"
    cover.Shape = cover_shape

    for obj, values in (
        (body, (("Length", body_L), ("Width", body_W), ("Height", body_H), ("Wall", wall), ("InternalLength", inner_L), ("InternalWidth", inner_W))),
        (plate, (("Length", plate_L), ("Width", plate_W), ("Thickness", plate_T), ("ClearancePerSide", plate_clearance), ("HoleDiameter", hole_d))),
        (cover, (("Length", cover_outer_L), ("Width", cover_outer_W), ("Height", cover_H), ("Wall", cover_wall), ("ClearancePerSide", cover_clearance), ("TopThickness", cover_top))),
    ):
        for name, value in values:
            obj.addProperty("App::PropertyLength", name, "Dimensions")
            setattr(obj, name, value)

    body.addProperty("App::PropertyString", "FitCheck", "Validation")
    body.FitCheck = "V3 body internal 120 x 85; plate clearance 0.30 mm/side"
    plate.addProperty("App::PropertyString", "FitCheck", "Validation")
    plate.FitCheck = "Plate -> Body: PASS"
    cover.addProperty("App::PropertyString", "FitCheck", "Validation")
    cover.FitCheck = "Body -> Cover: PASS"
    cover.addProperty("App::PropertyString", "PrintOrientation", "Printing")
    cover.PrintOrientation = "Closed top face DOWN; opening UP"

    doc.recompute()
    _solid(body, "SmokeTestBody")
    _solid(plate, "SmokeTestPlate")
    _solid(cover, "SmokeTestCover")

    plate_box = plate.Shape.BoundBox
    inner_box = Part.makeBox(inner_L, inner_W, body_H - bottom, App.Vector(wall, wall, bottom)).BoundBox
    if plate_box.XMin < inner_box.XMin or plate_box.XMax > inner_box.XMax or plate_box.YMin < inner_box.YMin or plate_box.YMax > inner_box.YMax:
        raise RuntimeError("Plate -> body fit failed")

    cover_cavity_box = Part.makeBox(cover_inner_L, cover_inner_W, cavity_depth, App.Vector(cover_x + cover_wall, cover_y + cover_wall, cover_top)).BoundBox
    body_box = body.Shape.BoundBox
    if body_box.XMin < cover_cavity_box.XMin or body_box.XMax > cover_cavity_box.XMax or body_box.YMin < cover_cavity_box.YMin or body_box.YMax > cover_cavity_box.YMax:
        raise RuntimeError("Body -> cover fit failed")

    _fit(doc)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    doc.saveAs(output_path)

    return {
        "ok": True,
        "action": "create_smoke_test_box",
        "output_path": output_path,
        "body": {"length": body_L, "width": body_W, "height": body_H, "wall": wall, "internal_length": inner_L, "internal_width": inner_W},
        "plate": {"length": plate_L, "width": plate_W, "thickness": plate_T, "clearance_per_side": plate_clearance, "holes": 6, "hole_diameter": hole_d, "fit": "PASS"},
        "cover": {"length": cover_outer_L, "width": cover_outer_W, "height": cover_H, "wall": cover_wall, "top": cover_top, "clearance_per_side": cover_clearance, "fit": "PASS"},
        "validation": {"plate_to_body": "PASS", "body_to_cover": "PASS", "separate_solids": True, "support_required": False, "v3_horizontal_contract": True},
    }
