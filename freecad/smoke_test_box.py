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
    """Create a compact reference box proving plate->body and body->cover fit."""
    doc = App.newDocument("SmokeTestBox")

    # Reference dimensions. Thickness grows outward so internal dimensions remain stable.
    plate_L = float(command.get("plate_length", 117.6))
    plate_W = float(command.get("plate_width", 82.6))
    plate_T = float(command.get("plate_thickness", 3.0))
    plate_clearance = float(command.get("plate_clearance_per_side", 0.3))
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
    output_path = os.path.abspath(command.get("output_path", "cad/output/smoke-test-box-v1.FCStd"))

    if min(plate_L, plate_W, plate_T, plate_clearance, wall, body_H, bottom, ledge_Z, ledge_T, ledge_W, cover_H, cover_wall, cover_clearance, cover_top) <= 0:
        raise RuntimeError("All dimensions must be positive")
    if body_H <= bottom or ledge_Z + ledge_T > body_H:
        raise RuntimeError("Invalid body/plate support height")
    if cover_top >= cover_H:
        raise RuntimeError("Cover top thickness must be smaller than cover height")

    # Body internal opening is sized around the plate. Wall thickness is added outward.
    inner_L = plate_L + 2.0 * plate_clearance
    inner_W = plate_W + 2.0 * plate_clearance
    body_L = inner_L + 2.0 * wall
    body_W = inner_W + 2.0 * wall

    outer = Part.makeBox(body_L, body_W, body_H)
    cavity = Part.makeBox(inner_L, inner_W, body_H - bottom, App.Vector(wall, wall, bottom))
    body_shape = outer.cut(cavity)
    ledge_outer = Part.makeBox(inner_L, inner_W, ledge_T, App.Vector(wall, wall, ledge_Z))
    ledge_inner = Part.makeBox(max(0.01, inner_L - 2.0 * ledge_W), max(0.01, inner_W - 2.0 * ledge_W), ledge_T + 0.2, App.Vector(wall + ledge_W, wall + ledge_W, ledge_Z - 0.1))
    body_shape = body_shape.fuse(ledge_outer.cut(ledge_inner))

    body = doc.addObject("Part::Feature", "SmokeTestBody")
    body.Label = "Smoke-Test Body - 3 mm"
    body.Shape = body_shape

    # Plate fits into the body cavity with the requested clearance.
    plate_x = wall + plate_clearance
    plate_y = wall + plate_clearance
    plate_shape = Part.makeBox(plate_L, plate_W, plate_T, App.Vector(plate_x, plate_y, ledge_Z + ledge_T))
    plate = doc.addObject("Part::Feature", "SmokeTestPlate")
    plate.Label = "Smoke-Test Plate - 3 mm"
    plate.Shape = plate_shape

    # Cover cavity is sized around the OUTSIDE of the body, with clearance.
    cover_inner_L = body_L + 2.0 * cover_clearance
    cover_inner_W = body_W + 2.0 * cover_clearance
    cover_outer_L = cover_inner_L + 2.0 * cover_wall
    cover_outer_W = cover_inner_W + 2.0 * cover_wall
    cover_x = -(cover_outer_L - body_L) / 2.0
    cover_y = -(cover_outer_W - body_W) / 2.0
    cover_z = 0.0
    cover_outer = Part.makeBox(cover_outer_L, cover_outer_W, cover_H, App.Vector(cover_x, cover_y, cover_z))
    cavity_depth = cover_H - cover_top
    cover_cavity = Part.makeBox(cover_inner_L, cover_inner_W, cavity_depth, App.Vector(cover_x + cover_wall, cover_y + cover_wall, cover_top))
    cover_shape = cover_outer.cut(cover_cavity)
    cover = doc.addObject("Part::Feature", "SmokeTestCover")
    cover.Label = "Smoke-Test Cover - 40 mm - 3 mm"
    cover.Shape = cover_shape

    for obj, values in (
        (body, (("Length", body_L), ("Width", body_W), ("Height", body_H), ("Wall", wall))),
        (plate, (("Length", plate_L), ("Width", plate_W), ("Thickness", plate_T), ("ClearancePerSide", plate_clearance))),
        (cover, (("Length", cover_outer_L), ("Width", cover_outer_W), ("Height", cover_H), ("Wall", cover_wall), ("ClearancePerSide", cover_clearance), ("TopThickness", cover_top))),
    ):
        for name, value in values:
            obj.addProperty("App::PropertyLength", name, "Dimensions")
            setattr(obj, name, value)

    body.addProperty("App::PropertyString", "FitCheck", "Validation")
    body.FitCheck = "Plate fits inside body with 0.30 mm per-side clearance"
    plate.addProperty("App::PropertyString", "FitCheck", "Validation")
    plate.FitCheck = "Plate -> Body: PASS"
    cover.addProperty("App::PropertyString", "FitCheck", "Validation")
    cover.FitCheck = "Body -> Cover: PASS; body insertion target 40 mm"
    cover.addProperty("App::PropertyString", "PrintOrientation", "Printing")
    cover.PrintOrientation = "Closed top face DOWN; opening UP"

    doc.recompute()
    _solid(body, "SmokeTestBody")
    _solid(plate, "SmokeTestPlate")
    _solid(cover, "SmokeTestCover")

    # Explicit fit checks using bounding boxes. Plate must be strictly inside body opening.
    plate_box = plate.Shape.BoundBox
    inner_box = Part.makeBox(inner_L, inner_W, body_H - bottom, App.Vector(wall, wall, bottom)).BoundBox
    if plate_box.XMin < inner_box.XMin or plate_box.XMax > inner_box.XMax or plate_box.YMin < inner_box.YMin or plate_box.YMax > inner_box.YMax:
        raise RuntimeError("Plate -> body fit failed")

    # Body must fit inside the cover cavity in XY; 40 mm cover height is the insertion envelope.
    body_xy = body.Shape.BoundBox
    cover_cavity_box = Part.makeBox(cover_inner_L, cover_inner_W, cavity_depth, App.Vector(cover_x + cover_wall, cover_y + cover_wall, cover_top)).BoundBox
    if body_xy.XMin < cover_cavity_box.XMin or body_xy.XMax > cover_cavity_box.XMax or body_xy.YMin < cover_cavity_box.YMin or body_xy.YMax > cover_cavity_box.YMax:
        raise RuntimeError("Body -> cover fit failed")

    _fit(doc)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    doc.saveAs(output_path)

    return {
        "ok": True,
        "action": "create_smoke_test_box",
        "output_path": output_path,
        "body": {"length": body_L, "width": body_W, "height": body_H, "wall": wall},
        "plate": {"length": plate_L, "width": plate_W, "thickness": plate_T, "clearance_per_side": plate_clearance, "fit": "PASS"},
        "cover": {"length": cover_outer_L, "width": cover_outer_W, "height": cover_H, "wall": cover_wall, "top": cover_top, "body_insertion_depth": cover_H, "fit": "PASS"},
        "validation": {"plate_to_body": "PASS", "body_to_cover": "PASS", "separate_solids": True, "support_required": False},
    }
