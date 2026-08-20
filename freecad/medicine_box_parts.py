import os

import FreeCAD as App
import FreeCADGui as Gui
import Part

L = 120.0
W = 85.0
H = 130.0
WALL = 3.0
BOTTOM = 3.0
PLATE_Z = 70.0
PLATE_T = 3.0
LEDGE_T = 3.0
LEDGE_WIDTH = 3.0
PLATE_CLEARANCE = 0.3
HOLE_D = 35.0
HOLE_MARGIN = 6.0
COVER_WALL = 3.0
COVER_CLEARANCE = 0.3
COVER_TOP = 3.0
COVER_INSERTION = 60.0


def _fit(doc):
    try:
        gui = Gui.getDocument(doc.Name)
        if gui:
            gui.activeView().viewAxonometric()
            gui.activeView().fitAll()
    except Exception:
        pass


def _save(doc, output_path):
    output_path = os.path.abspath(output_path)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    doc.recompute()
    for obj in doc.Objects:
        if hasattr(obj, "Shape") and obj.Shape and not obj.Shape.isValid():
            raise RuntimeError(f"Invalid generated geometry: {obj.Name}")
        if hasattr(obj, "Shape") and obj.Shape and not obj.Shape.Solids:
            raise RuntimeError(f"Generated part is not a solid: {obj.Name}")
    _fit(doc)
    doc.saveAs(output_path)
    return output_path


def create_medicine_cover(command):
    """Standalone FDM cover; functional body footprint remains L x W."""
    doc = App.newDocument("MedicineCover")
    outer_L = L + 2 * COVER_WALL + 2 * COVER_CLEARANCE
    outer_W = W + 2 * COVER_WALL + 2 * COVER_CLEARANCE
    inner_L = L + 2 * COVER_CLEARANCE
    inner_W = W + 2 * COVER_CLEARANCE
    total_H = COVER_INSERTION + COVER_TOP

    outer = Part.makeBox(outer_L, outer_W, total_H, App.Vector(0, 0, 0))
    cavity = Part.makeBox(inner_L, inner_W, COVER_INSERTION, App.Vector(COVER_WALL, COVER_WALL, COVER_TOP))
    shape = outer.cut(cavity)

    obj = doc.addObject("Part::Feature", "MedicineCover")
    obj.Label = "Medicine Box Cover - PRINT ORIENTATION"
    obj.Shape = shape
    obj.addProperty("App::PropertyString", "PrintOrientation", "Printing")
    obj.PrintOrientation = "Closed face DOWN on build plate; opening UP"
    obj.addProperty("App::PropertyLength", "ClearancePerSide", "Dimensions")
    obj.ClearancePerSide = COVER_CLEARANCE
    obj.addProperty("App::PropertyLength", "InsertionDepth", "Dimensions")
    obj.InsertionDepth = COVER_INSERTION
    obj.addProperty("App::PropertyLength", "TopThickness", "Dimensions")
    obj.TopThickness = COVER_TOP
    obj.addProperty("App::PropertyString", "Support", "Printing")
    obj.Support = "No support required by design"

    output = command.get("output_path", "cad/output/medicine-box-cover-v3.FCStd")
    return {"ok": True, "action": "create_medicine_cover", "output_path": _save(doc, output),
            "dimensions": {"length": outer_L, "width": outer_W, "height": total_H},
            "functional_footprint": {"length": L, "width": W},
            "printability": {"orientation": "closed face down / opening up", "support_required": False}}


def create_medicine_plate(command):
    """Standalone 6-hole plate, printed flat on the build plate."""
    doc = App.newDocument("MedicinePlate6Holes")
    plate_L = L
    plate_W = W

    margin = HOLE_MARGIN
    radius = HOLE_D / 2.0
    if plate_L < 3 * HOLE_D + 2 * margin or plate_W < 2 * HOLE_D + 2 * margin:
        raise RuntimeError("Plate is too small for 6 x Ø35 mm holes with 6 mm edge margin")

    xs = [margin + radius, plate_L / 2.0, plate_L - margin - radius]
    ys = [margin + radius, plate_W - margin - radius]

    shape = Part.makeBox(plate_L, plate_W, PLATE_T, App.Vector(0, 0, 0))
    for x in xs:
        for y in ys:
            hole = Part.makeCylinder(HOLE_D / 2, PLATE_T + 2, App.Vector(x, y, -1), App.Vector(0, 0, 1))
            shape = shape.cut(hole)

    obj = doc.addObject("Part::Feature", "MedicinePlate6Holes")
    obj.Label = "Medicine Plate - 6 x Ø35 mm - PRINT FLAT"
    obj.Shape = shape
    obj.addProperty("App::PropertyString", "PrintOrientation", "Printing")
    obj.PrintOrientation = "Flat on build plate; holes vertical through plate"
    obj.addProperty("App::PropertyString", "Fit", "Design")
    obj.Fit = "120 x 85 mm functional plate; body cavity remains 120 x 85 mm"
    obj.addProperty("App::PropertyString", "HolePattern", "Design")
    obj.HolePattern = "3 columns x 2 rows; 6 x Ø35 mm; 6 mm edge margin"

    output = command.get("output_path", "cad/output/medicine-box-plate-6holes-v3.FCStd")
    return {"ok": True, "action": "create_medicine_plate", "output_path": _save(doc, output),
            "dimensions": {"length": plate_L, "width": plate_W, "thickness": PLATE_T},
            "holes": {"count": 6, "diameter": HOLE_D, "pattern": "3 x 2", "edge_margin": margin,
                      "centers_x": xs, "centers_y": ys},
            "printability": {"orientation": "flat", "support_required": False}}


def create_medicine_body(command):
    """Standalone body. length/width are functional internal dimensions; wall is added outward."""
    doc = App.newDocument("MedicineBody")
    functional_L = float(command.get("length", L))
    functional_W = float(command.get("width", W))
    height = float(command.get("height", H))
    wall = float(command.get("wall", WALL))
    bottom = float(command.get("bottom_thickness", BOTTOM))
    plate_z = float(command.get("plate_support_z", PLATE_Z))
    plate_t = float(command.get("plate_thickness", PLATE_T))
    ledge_t = float(command.get("ledge_thickness", LEDGE_T))
    ledge_width = float(command.get("ledge_width", LEDGE_WIDTH))
    if min(functional_L, functional_W, height, wall, bottom, plate_t, ledge_t, ledge_width) <= 0:
        raise RuntimeError("All body dimensions must be positive")
    if plate_z <= bottom or plate_z + plate_t > height:
        raise RuntimeError("Plate support position is outside the body")

    outer_L = functional_L + 2 * wall
    outer_W = functional_W + 2 * wall
    outer = Part.makeBox(outer_L, outer_W, height)
    cavity = Part.makeBox(functional_L, functional_W, height - bottom, App.Vector(wall, wall, bottom))
    shape = outer.cut(cavity)

    ledge_outer = Part.makeBox(functional_L, functional_W, ledge_t, App.Vector(wall, wall, plate_z - ledge_t))
    ledge_inner = Part.makeBox(max(0.01, functional_L - 2 * ledge_width), max(0.01, functional_W - 2 * ledge_width), ledge_t + 0.2,
                               App.Vector(wall + ledge_width, wall + ledge_width, plate_z - ledge_t - 0.1))
    shape = shape.fuse(ledge_outer.cut(ledge_inner))

    obj = doc.addObject("Part::Feature", "MedicineBody")
    obj.Label = f"Medicine Box Body - functional {functional_L:.0f}x{functional_W:.0f} - PRINT UPRIGHT"
    obj.Shape = shape
    for name, value in (("FunctionalLength", functional_L), ("FunctionalWidth", functional_W), ("OuterLength", outer_L),
                        ("OuterWidth", outer_W), ("Height", height), ("WallThickness", wall), ("BottomThickness", bottom),
                        ("PlateSupportZ", plate_z), ("PlateSupportThickness", ledge_t), ("PlateSupportWidth", ledge_width)):
        obj.addProperty("App::PropertyLength", name, "Dimensions")
        setattr(obj, name, value)
    obj.addProperty("App::PropertyString", "PrintOrientation", "Printing")
    obj.PrintOrientation = "Bottom DOWN on build plate; opening UP"
    obj.addProperty("App::PropertyString", "PlateSupport", "Design")
    obj.PlateSupport = "Continuous ledge on all four inner sides"
    obj.addProperty("App::PropertyString", "DimensionContract", "Design")
    obj.DimensionContract = "120 x 85 mm functional/internal footprint; 3 mm wall added outward"

    output = command.get("output_path", "cad/output/medicine-box-body-v3-smoke.FCStd")
    return {"ok": True, "action": "create_medicine_body", "output_path": _save(doc, output),
            "dimensions": {"functional_length": functional_L, "functional_width": functional_W,
                           "outer_length": outer_L, "outer_width": outer_W, "height": height,
                           "wall": wall, "bottom": bottom},
            "plate_support": {"z": plate_z, "thickness": ledge_t, "width": ledge_width},
            "printability": {"orientation": "upright", "support_required": False}}
