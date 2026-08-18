import os

import FreeCAD as App
import FreeCADGui as Gui
import Part

L = 120.0
W = 85.0
H = 130.0
WALL = 1.0
BOTTOM = 1.0
PLATE_Z = 70.0
PLATE_T = 1.0
LEDGE_T = 1.0
LEDGE_WIDTH = 3.0
PLATE_CLEARANCE = 0.2
HOLE_D = 35.0
HOLE_MARGIN = 6.0
COVER_WALL = 1.0
COVER_CLEARANCE = 0.25
COVER_TOP = 1.0
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
    """Standalone FDM cover with the closed 1 mm face on the build plate."""
    doc = App.newDocument("MedicineCover")
    outer_L = L + 2 * (COVER_WALL + COVER_CLEARANCE)
    outer_W = W + 2 * (COVER_WALL + COVER_CLEARANCE)
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
    obj.PrintOrientation = "Closed 1 mm face DOWN on build plate; opening UP"
    obj.addProperty("App::PropertyLength", "ClearancePerSide", "Dimensions")
    obj.ClearancePerSide = COVER_CLEARANCE
    obj.addProperty("App::PropertyLength", "InsertionDepth", "Dimensions")
    obj.InsertionDepth = COVER_INSERTION
    obj.addProperty("App::PropertyLength", "TopThickness", "Dimensions")
    obj.TopThickness = COVER_TOP
    obj.addProperty("App::PropertyString", "Support", "Printing")
    obj.Support = "No support required by design"

    output = command.get("output_path", "cad/output/medicine-box-cover-v1.FCStd")
    return {"ok": True, "action": "create_medicine_cover", "output_path": _save(doc, output),
            "dimensions": {"length": outer_L, "width": outer_W, "height": total_H},
            "printability": {"orientation": "closed face down / opening up", "support_required": False}}


def create_medicine_plate(command):
    """Standalone 6-hole plate, printed flat on the build plate."""
    doc = App.newDocument("MedicinePlate6Holes")
    plate_L = L - 2 * WALL - 2 * PLATE_CLEARANCE
    plate_W = W - 2 * WALL - 2 * PLATE_CLEARANCE

    # 6 mm edge margin around the Ø35 mm holes.
    xs = [HOLE_MARGIN + HOLE_D / 2,
          plate_L / 2,
          plate_L - HOLE_MARGIN - HOLE_D / 2]
    ys = [HOLE_MARGIN + HOLE_D / 2,
          plate_W - HOLE_MARGIN - HOLE_D / 2]

    if plate_L < 3 * HOLE_D + 2 * HOLE_MARGIN or plate_W < 2 * HOLE_D + 2 * HOLE_MARGIN:
        raise RuntimeError("Plate is too small for 6 x Ø35 mm holes with 6 mm edge margin")

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
    obj.Fit = "117.6 x 82.6 mm; 0.2 mm clearance per side to body cavity"
    obj.addProperty("App::PropertyString", "HolePattern", "Design")
    obj.HolePattern = "3 columns x 2 rows; 6 x Ø35 mm; 6 mm edge margin"

    output = command.get("output_path", "cad/output/medicine-box-plate-6holes-v1.FCStd")
    return {"ok": True, "action": "create_medicine_plate", "output_path": _save(doc, output),
            "dimensions": {"length": plate_L, "width": plate_W, "thickness": PLATE_T},
            "holes": {"count": 6, "diameter": HOLE_D, "pattern": "3 x 2", "edge_margin": HOLE_MARGIN},
            "printability": {"orientation": "flat", "support_required": False}}


def create_medicine_body(command):
    """Standalone body with bottom and continuous internal plate ledge."""
    doc = App.newDocument("MedicineBody")
    outer = Part.makeBox(L, W, H)
    cavity = Part.makeBox(L - 2 * WALL, W - 2 * WALL, H - BOTTOM, App.Vector(WALL, WALL, BOTTOM))
    shape = outer.cut(cavity)

    ledge_outer = Part.makeBox(L - 2 * WALL, W - 2 * WALL, LEDGE_T, App.Vector(WALL, WALL, PLATE_Z - LEDGE_T))
    ledge_inner = Part.makeBox(L - 2 * WALL - 2 * LEDGE_WIDTH, W - 2 * WALL - 2 * LEDGE_WIDTH,
                               LEDGE_T + 0.2, App.Vector(WALL + LEDGE_WIDTH, WALL + LEDGE_WIDTH,
                                                        PLATE_Z - LEDGE_T - 0.1))
    shape = shape.fuse(ledge_outer.cut(ledge_inner))

    obj = doc.addObject("Part::Feature", "MedicineBody")
    obj.Label = "Medicine Box Body - PRINT UPRIGHT"
    obj.Shape = shape
    obj.addProperty("App::PropertyString", "PrintOrientation", "Printing")
    obj.PrintOrientation = "Bottom DOWN on build plate; opening UP"
    obj.addProperty("App::PropertyString", "PlateSupport", "Design")
    obj.PlateSupport = "Continuous 1 mm thick x 3 mm wide ledge on all four inner sides at Z=70 mm"
    obj.addProperty("App::PropertyString", "PlateFit", "Design")
    obj.PlateFit = "Plate 117.6 x 82.6 mm; 0.2 mm clearance per side"

    output = command.get("output_path", "cad/output/medicine-box-body-v1.FCStd")
    return {"ok": True, "action": "create_medicine_body", "output_path": _save(doc, output),
            "dimensions": {"length": L, "width": W, "height": H, "wall": WALL},
            "plate_support": {"z": PLATE_Z, "thickness": LEDGE_T, "width": LEDGE_WIDTH},
            "printability": {"orientation": "upright", "support_required": False}}
