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


def create_large_enclosure(command):
    """Create the 200x100x250 enclosure with internal TOP plate and lid."""
    doc = App.ActiveDocument
    if doc is None:
        doc = App.newDocument("Enclosure200x100x250")

    L = float(command.get("length", 200.0))
    W = float(command.get("width", 100.0))
    H = float(command.get("height", 250.0))
    wall = float(command.get("wall", 2.0))
    bottom = float(command.get("bottom_thickness", 2.0))

    lid_L = float(command.get("lid_length", 202.0))
    lid_W = float(command.get("lid_width", 102.0))
    lid_H = float(command.get("lid_height", 60.0))
    lid_wall = float(command.get("lid_wall", 2.0))

    plate_z_center = float(command.get("plate_center_z", 125.0))
    plate_t = float(command.get("plate_thickness", 2.0))
    hole_d = float(command.get("hole_diameter", 50.0))
    hole_columns = int(command.get("hole_columns", 3))
    hole_rows = int(command.get("hole_rows", 2))

    output_path = os.path.abspath(command.get(
        "output_path",
        "/home/hikmah/projectx/freecad-agent/cad/output/enclosure-200x100x250.FCStd"
    ))

    values = (L, W, H, wall, bottom, lid_L, lid_W, lid_H, lid_wall,
              plate_z_center, plate_t, hole_d)
    if min(values) <= 0:
        raise RuntimeError("All enclosure dimensions must be positive")
    if wall * 2 >= min(L, W) or bottom >= H:
        raise RuntimeError("Invalid enclosure wall/bottom thickness")
    if lid_wall * 2 >= min(lid_L, lid_W) or lid_wall >= lid_H:
        raise RuntimeError("Invalid lid wall thickness")
    if hole_columns != 3 or hole_rows != 2:
        raise RuntimeError("This design requires a 3 x 2 hole pattern")

    # The plate is explicitly required to touch all four inside walls.
    # It therefore spans the full external footprint; its edges meet the
    # enclosure walls at x=0/L and y=0/W.
    plate_L = L
    plate_W = W
    plate_z = plate_z_center - plate_t / 2.0
    if plate_z <= bottom or plate_z + plate_t >= H:
        raise RuntimeError("Internal plate position is outside the enclosure")

    # Six Ø50 mm vertical through-holes, 3 columns x 2 rows, symmetric.
    # Centers are laid out over the 200 x 100 mm plate at x=50/100/150 and
    # y=25/75, so the requested 50 mm diameter is preserved exactly.
    x_centers = [L * 0.25, L * 0.5, L * 0.75]
    y_centers = [W * 0.25, W * 0.75]

    for name in (
        "LargeBoxBase", "InternalTopPlate", "LargeBoxLid"
    ):
        old = doc.getObject(name)
        if old is not None:
            doc.removeObject(name)

    outer = Part.makeBox(L, W, H)
    inner = Part.makeBox(
        L - 2 * wall,
        W - 2 * wall,
        H - bottom,
        App.Vector(wall, wall, bottom)
    )
    base_shape = outer.cut(inner)

    base = doc.addObject("Part::Feature", "LargeBoxBase")
    base.Label = "Base 200x100x250 mm - wall 2 mm - bottom 2 mm"
    base.Shape = base_shape

    plate_shape = Part.makeBox(
        plate_L, plate_W, plate_t,
        App.Vector(0, 0, plate_z)
    )
    for x in x_centers:
        for y in y_centers:
            hole = Part.makeCylinder(
                hole_d / 2.0,
                plate_t + 2.0,
                App.Vector(x, y, plate_z - 1.0),
                App.Vector(0, 0, 1)
            )
            plate_shape = plate_shape.cut(hole)

    plate = doc.addObject("Part::Feature", "InternalTopPlate")
    plate.Label = "Internal TOP plate - touches all sides - 6x Ø50 mm"
    plate.Shape = plate_shape

    # Lid is a separate hollow cap. Its 2 mm top and side walls leave the
    # bottom open so it can fit over the 200x100 body.
    lid_z = H
    lid_outer = Part.makeBox(lid_L, lid_W, lid_H, App.Vector(-1.0, -1.0, lid_z))
    lid_inner = Part.makeBox(
        lid_L - 2 * lid_wall,
        lid_W - 2 * lid_wall,
        lid_H - lid_wall,
        App.Vector(-1.0 + lid_wall, -1.0 + lid_wall, lid_z)
    )
    lid_shape = lid_outer.cut(lid_inner)

    lid = doc.addObject("Part::Feature", "LargeBoxLid")
    lid.Label = "Lid 202x102x60 mm - wall 2 mm"
    lid.Shape = lid_shape

    # Metadata for inspection/verification.
    for obj, props in (
        (base, (
            ("Length", L), ("Width", W), ("Height", H),
            ("WallThickness", wall), ("BottomThickness", bottom),
        )),
        (plate, (
            ("Length", plate_L), ("Width", plate_W),
            ("Thickness", plate_t), ("CenterZ", plate_z_center),
            ("HoleDiameter", hole_d),
        )),
        (lid, (
            ("Length", lid_L), ("Width", lid_W),
            ("Height", lid_H), ("WallThickness", lid_wall),
        )),
    ):
        for name, value in props:
            obj.addProperty("App::PropertyLength", name, "Dimensions")
            setattr(obj, name, value)

    plate.addProperty("App::PropertyString", "Orientation", "Design")
    plate.Orientation = "TOP / holes vertical upward"
    plate.addProperty("App::PropertyString", "Mounting", "Design")
    plate.Mounting = "Plate edges touch all four enclosure sides"
    plate.addProperty("App::PropertyString", "HolePattern", "Design")
    plate.HolePattern = "3 columns x 2 rows, symmetric, 6 x Ø50 mm"

    lid.addProperty("App::PropertyString", "Fit", "Design")
    lid.Fit = "Separate removable hollow cap"

    doc.recompute()
    _fit_view(doc)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    doc.saveAs(output_path)

    return {
        "ok": True,
        "action": "create_large_enclosure",
        "document": doc.Name,
        "output_path": output_path,
        "box": {
            "length": L, "width": W, "height": H,
            "wall": wall, "bottom": bottom,
        },
        "internal_plate": {
            "length": plate_L, "width": plate_W,
            "thickness": plate_t,
            "center_z": plate_z_center,
            "touches_all_sides": True,
            "orientation": "TOP",
            "hole_diameter": hole_d,
            "hole_pattern": "3 x 2",
            "hole_count": 6,
        },
        "lid": {
            "length": lid_L, "width": lid_W, "height": lid_H,
            "wall": lid_wall, "separate": True,
        },
        "objects": ["LargeBoxBase", "InternalTopPlate", "LargeBoxLid"],
    }
