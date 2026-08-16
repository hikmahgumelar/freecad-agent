import FreeCAD as App
import FreeCADGui as Gui
import Part
import os


def _fit_view(doc):
    try:
        gui_doc = Gui.getDocument(doc.Name)
        if gui_doc is not None:
            gui_doc.activeView().viewAxonometric()
            gui_doc.activeView().fitAll()
    except Exception:
        pass


def create_box_enclosure(command):
    doc = App.ActiveDocument
    if doc is None:
        doc = App.newDocument("Box90x60x11")

    L = float(command.get("length", 90.0))
    W = float(command.get("width", 60.0))
    H = float(command.get("height", 11.0))
    wall = float(command.get("wall", 1.5))
    cover_t = float(command.get("cover_thickness", 1.5))
    screw_d = float(command.get("screw_diameter", 3.0))
    screw_margin = float(command.get("screw_margin", 5.0))
    antenna_d = float(command.get("antenna_diameter", 7.0))
    antenna_left = float(command.get("antenna_left_offset", 10.0))
    usb_w = float(command.get("usb_width", 12.0))
    usb_h = float(command.get("usb_height", 5.0))
    post_outer_d = float(command.get("post_outer_diameter", 6.0))
    output_path = os.path.abspath(command.get(
        "output_path",
        "/home/hikmah/projectx/freecad-agent/cad/output/box-90x60x11.FCStd"
    ))

    if min(L, W, H, wall, cover_t, screw_d, screw_margin,
           antenna_d, antenna_left, usb_w, usb_h, post_outer_d) <= 0:
        raise RuntimeError("All enclosure dimensions must be positive")
    if wall * 2 >= min(L, W) or wall >= H:
        raise RuntimeError("Invalid wall thickness")

    # The USB-C and antenna interfaces are on the two opposite
    # short faces (60 mm wide), not on the 90 mm faces.
    if usb_w >= W or usb_h >= H:
        raise RuntimeError("USB-C opening is too large for the 60 mm side")
    if antenna_left + antenna_d / 2 > W or antenna_left - antenna_d / 2 < 0:
        raise RuntimeError("Antenna position is outside the 60 mm side")

    for name in (
        "BoxBase", "BoxCover",
        "ScrewPost1", "ScrewPost2", "ScrewPost3", "ScrewPost4"
    ):
        obj = doc.getObject(name)
        if obj is not None:
            doc.removeObject(name)

    outer = Part.makeBox(L, W, H)
    inner = Part.makeBox(
        L - 2 * wall,
        W - 2 * wall,
        H - wall,
        App.Vector(wall, wall, wall)
    )
    base_shape = outer.cut(inner)

    # USB-C: centered on the first 60 mm side (x = 0).
    usb_y = (W - usb_w) / 2.0
    usb = Part.makeBox(
        wall + 2.0,
        usb_w,
        usb_h,
        App.Vector(-1.0, usb_y, (H - usb_h) / 2.0)
    )
    base_shape = base_shape.cut(usb)

    # Antenna: on the opposite 60 mm side (x = L),
    # 10 mm from the left edge of that 60 mm face.
    antenna_y = antenna_left
    antenna_z = H / 2.0
    antenna = Part.makeCylinder(
        antenna_d / 2.0,
        wall + 2.0,
        App.Vector(L - wall - 1.0, antenna_y, antenna_z),
        App.Vector(1, 0, 0)
    )
    base_shape = base_shape.cut(antenna)

    base = doc.addObject("Part::Feature", "BoxBase")
    base.Label = "Base 90x60x11 mm - Type-C + SMA"
    base.Shape = base_shape

    screw_positions = [
        (screw_margin, screw_margin),
        (L - screw_margin, screw_margin),
        (screw_margin, W - screw_margin),
        (L - screw_margin, W - screw_margin),
    ]
    for index, (x, y) in enumerate(screw_positions, 1):
        outer_post = Part.makeCylinder(
            post_outer_d / 2.0,
            H - wall,
            App.Vector(x, y, wall)
        )
        inner_hole = Part.makeCylinder(
            screw_d / 2.0,
            H + 1.0,
            App.Vector(x, y, 0)
        )
        post_shape = outer_post.cut(inner_hole)
        post = doc.addObject("Part::Feature", f"ScrewPost{index}")
        post.Label = f"Screw post {index} - hole Ø{int(screw_d)} mm"
        post.Shape = post_shape

    # Cover remains a separate FreeCAD object. It can be exported as
    # its own STL later, independently from the body.
    cover_shape = Part.makeBox(L, W, cover_t, App.Vector(0, 0, H))
    for x, y in screw_positions:
        hole = Part.makeCylinder(
            screw_d / 2.0,
            cover_t + 2.0,
            App.Vector(x, y, H - 1.0)
        )
        cover_shape = cover_shape.cut(hole)

    cover = doc.addObject("Part::Feature", "BoxCover")
    cover.Label = "Cover 90x60x1.5 mm - 4x Ø3 mm"
    cover.Shape = cover_shape
    cover.addProperty("App::PropertyLength", "Thickness", "Cover")
    cover.Thickness = cover_t
    cover.addProperty("App::PropertyLength", "ScrewHoleDiameter", "Cover")
    cover.ScrewHoleDiameter = screw_d

    base.addProperty("App::PropertyLength", "Length", "Dimensions")
    base.Length = L
    base.addProperty("App::PropertyLength", "Width", "Dimensions")
    base.Width = W
    base.addProperty("App::PropertyLength", "Height", "Dimensions")
    base.Height = H
    base.addProperty("App::PropertyLength", "WallThickness", "Dimensions")
    base.WallThickness = wall
    base.addProperty("App::PropertyLength", "AntennaDiameter", "Interfaces")
    base.AntennaDiameter = antenna_d
    base.addProperty("App::PropertyLength", "AntennaLeftOffset", "Interfaces")
    base.AntennaLeftOffset = antenna_left
    base.addProperty("App::PropertyLength", "UsbCutoutWidth", "Interfaces")
    base.UsbCutoutWidth = usb_w
    base.addProperty("App::PropertyLength", "UsbCutoutHeight", "Interfaces")
    base.UsbCutoutHeight = usb_h
    base.addProperty("App::PropertyString", "DesignNote", "Interfaces")
    base.DesignNote = (
        "USB-C centered on one 60 mm side; Ø7 mm antenna opening "
        "on the opposite 60 mm side, 10 mm from the left edge."
    )

    doc.recompute()
    _fit_view(doc)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    doc.saveAs(output_path)

    return {
        "ok": True,
        "action": "create_box_enclosure",
        "document": doc.Name,
        "output_path": output_path,
        "dimensions": {"length": L, "width": W, "height": H},
        "wall_thickness": wall,
        "cover": {
            "length": L,
            "width": W,
            "thickness": cover_t,
            "screw_hole_diameter": screw_d,
            "separate_object": True,
        },
        "usb_c": {
            "side": "60 mm side",
            "position": "center",
            "width": usb_w,
            "height": usb_h,
        },
        "antenna": {
            "side": "opposite 60 mm side",
            "diameter": antenna_d,
            "left_offset": antenna_left,
        },
        "screw_posts": {
            "count": 4,
            "hole_diameter": screw_d,
            "outer_diameter": post_outer_d,
        },
        "objects": [
            "BoxBase", "BoxCover",
            "ScrewPost1", "ScrewPost2", "ScrewPost3", "ScrewPost4"
        ],
    }
