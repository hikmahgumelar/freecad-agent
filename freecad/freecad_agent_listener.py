import json
import os
import socket

import FreeCAD as App
import FreeCADGui as Gui
import Part
from PySide import QtCore

from agent.features import FlexureButton

HOST = "127.0.0.1"
PORT = 8765
_server_socket = None
_server_timer = None


def _fit_view(doc):
    try:
        Gui.getDocument(doc.Name).activeView().viewAxonometric()
        Gui.getDocument(doc.Name).activeView().fitAll()
    except Exception as exc:
        print(f"[freecad-agent] GUI update skipped: {exc}")


def _inspect_geometry(command):
    doc = App.ActiveDocument
    if doc is None:
        raise RuntimeError("No active FreeCAD document")
    name = command.get("body", "BottomCase")
    obj = doc.getObject(name)
    if obj is None or obj.Shape.isNull():
        raise RuntimeError(f"Object '{name}' has no valid shape")
    b = obj.Shape.BoundBox
    return {
        "ok": True,
        "action": "inspect_geometry",
        "document": doc.Name,
        "object": obj.Name,
        "bounding_box": {
            "xmin": b.XMin, "xmax": b.XMax, "ymin": b.YMin, "ymax": b.YMax,
            "zmin": b.ZMin, "zmax": b.ZMax,
            "x_length": b.XLength, "y_length": b.YLength, "z_length": b.ZLength,
        },
        "solids": len(obj.Shape.Solids),
        "faces": len(obj.Shape.Faces),
        "edges": len(obj.Shape.Edges),
    }


def _build_flexure_cut(button: FlexureButton, slot_z: float, slot_h: float):
    """Build the canonical imperfect-U cut for a reusable FlexureButton."""
    ox, oy = button.origin
    cut_depth = button.length - button.rear_bridge
    if cut_depth <= 0:
        raise RuntimeError("rear_bridge must be smaller than button length")

    left_slot = Part.makeBox(
        button.slot, cut_depth, slot_h,
        App.Vector(ox - button.slot, oy, slot_z),
    )
    right_slot = Part.makeBox(
        button.slot, cut_depth, slot_h,
        App.Vector(ox + button.width, oy, slot_z),
    )
    rear_slot = Part.makeBox(
        button.width + 2.0 * button.slot,
        button.slot,
        slot_h,
        App.Vector(ox - button.slot, oy + button.length - button.slot, slot_z),
    )
    return left_slot.fuse(right_slot).fuse(rear_slot)


def _create_snapfit_case(command):
    """ESP32-C3 Super Mini snap-fit enclosure using reusable flexure semantics."""
    board_w = float(command.get("board_width", 18.0))
    board_l = float(command.get("board_length", 22.5))
    board_clear = float(command.get("board_clearance", 0.25))
    wall = float(command.get("wall", 1.2))
    bottom = float(command.get("bottom_thickness", 1.2))
    body_h = float(command.get("body_height", 5.2))
    cover_t = float(command.get("cover_thickness", 1.2))
    cover_wall = float(command.get("cover_wall", 1.2))
    cover_clear = float(command.get("cover_clearance", 0.2))
    snap_r = float(command.get("snap_radius", 1.0))
    snap_z = float(command.get("snap_z", 2.8))
    snap_y = float(command.get("snap_offset_y", 4.0))

    button_len = float(command.get("button_length", 7.0))
    button_w = float(command.get("button_width", 2.0))
    button_slot_width = float(command.get("button_slot_width", command.get("button_cut_thickness", 0.5)))
    button_center_spacing = float(command.get("button_center_spacing", command.get("button_pair_center_to_center", 8.8)))
    button_rear_bridge = float(command.get("button_rear_bridge", 1.0))

    actuator_w = float(command.get("actuator_width", command.get("actuator_pad_width", 2.0)))
    actuator_l = float(command.get("actuator_length", command.get("actuator_pad_length", 2.0)))
    actuator_h = float(command.get("actuator_height", command.get("actuator_pad_thickness", 0.75)))

    usb_w = float(command.get("usb_opening_width", 10.0))
    usb_h = float(command.get("usb_opening_height", 4.0))
    usb_bottom = float(command.get("usb_opening_bottom", 1.0))
    antenna_l = float(command.get("antenna_keepout_length", 5.0))
    antenna_w = float(command.get("antenna_keepout_width", 12.0))
    output = os.path.abspath(command.get("output_path", "/home/hikmah/projectx/freecad-agent/cad/output/esp32-c3-super-mini-snapfit-v4.FCStd"))

    if button_slot_width != 0.5:
        raise RuntimeError("Snapfit FlexureButton requires a fixed 0.5 mm slot")
    if button_w != 2.0:
        raise RuntimeError("Snapfit FlexureButton requires a fixed 2.0 mm button width")
    if button_rear_bridge != 1.0:
        raise RuntimeError("Snapfit FlexureButton requires a fixed 1.0 mm rear bridge")
    if actuator_w != 2.0 or actuator_l != 2.0:
        raise RuntimeError("Snapfit actuator pad must be exactly 2.0 x 2.0 mm")
    if actuator_h != 0.75:
        raise RuntimeError("Snapfit actuator pad height must be exactly 0.75 mm")

    values = [
        board_w, board_l, board_clear, wall, bottom, body_h, cover_t,
        cover_wall, cover_clear, snap_r, snap_z, snap_y, button_len,
        button_w, button_slot_width, button_center_spacing, button_rear_bridge,
        actuator_w, actuator_l, actuator_h, usb_w, usb_h, antenna_l, antenna_w,
    ]
    if min(values) <= 0:
        raise RuntimeError("All snap-fit dimensions must be positive")
    if usb_w >= board_w + 2 * board_clear:
        raise RuntimeError("USB opening is too wide")
    if body_h <= bottom + 2.0:
        raise RuntimeError("body_height is too small for component clearance")

    inner_w = board_w + 2 * board_clear
    inner_l = board_l + 2 * board_clear
    outer_w = inner_w + 2 * wall
    outer_l = inner_l + 2 * wall
    doc = App.newDocument(command.get("document", "ESP32C3SnapFitCaseV4"))

    tray = Part.makeBox(outer_w, outer_l, body_h).cut(
        Part.makeBox(inner_w, inner_l, body_h - bottom, App.Vector(wall, wall, bottom))
    )

    center_x = outer_w / 2.0
    usb_x = center_x - usb_w / 2.0
    tray = tray.cut(
        Part.makeBox(usb_w, wall + 0.8, usb_h, App.Vector(usb_x, outer_l - wall - 0.4, usb_bottom))
    )

    ak_x = center_x - antenna_w / 2.0
    ak_y = outer_l - wall - antenna_l
    tray = tray.cut(
        Part.makeBox(
            antenna_w, antenna_l + 0.2,
            min(1.5, body_h - bottom),
            App.Vector(ak_x, ak_y, body_h - 1.5),
        )
    )

    body = doc.addObject("Part::Feature", "BottomCase")
    body.Label = "ESP32-C3 bottom case"
    body.Shape = tray
    body.addProperty("App::PropertyString", "Contract", "Design")
    body.Contract = "ESP32-C3 Super Mini; 2-piece snap-fit; centered USB-C; 4 round snaps; rear antenna relief; no screws."
    body.addProperty("App::PropertyLength", "BoardWidth", "Design")
    body.BoardWidth = board_w
    body.addProperty("App::PropertyLength", "BoardLength", "Design")
    body.BoardLength = board_l
    body.addProperty("App::PropertyLength", "BoardClearance", "Printability")
    body.BoardClearance = board_clear

    snap_centers = (snap_y, outer_l - snap_y)
    for side, x in (("Left", 0.0), ("Right", outer_w)):
        for idx, sy in enumerate(snap_centers, 1):
            cx = x + snap_r * 0.55 if side == "Left" else x - snap_r * 0.55
            sphere = Part.makeSphere(snap_r, App.Vector(cx, sy, snap_z))
            clip_x = -0.1 if side == "Left" else outer_w - snap_r - 0.1
            clip = Part.makeBox(
                snap_r + 0.2, 2 * snap_r + 0.4, 2 * snap_r + 0.4,
                App.Vector(clip_x, sy - snap_r - 0.2, snap_z - snap_r - 0.2),
            )
            boss = sphere.common(clip)
            body.Shape = body.Shape.fuse(boss).removeSplitter()
            obj = doc.addObject("Part::Feature", f"SnapBoss{side}{idx}")
            obj.Label = f"Round snap boss {side} {idx}"
            obj.Shape = boss

    # C-01: cover skirt must descend far enough to fully seat over the body,
    # leaving a small shoulder/lip so the cover stops on the body wall instead
    # of only overlapping the top. Derived from body_h, never hard-coded.
    cover_lip = float(command.get("cover_lip", 0.8))
    if cover_lip < 0 or cover_lip >= body_h:
        raise RuntimeError("cover_lip must be >= 0 and smaller than body_height")
    skirt_h = body_h - cover_lip
    if skirt_h <= snap_z:
        raise RuntimeError(
            "cover skirt is too short to capture the snap bosses; "
            "reduce cover_lip or raise body_height"
        )
    cover_outer_w = outer_w + 2 * (cover_wall + cover_clear)
    cover_outer_l = outer_l + 2 * (cover_wall + cover_clear)
    ox = -(cover_wall + cover_clear)
    oy = -(cover_wall + cover_clear)
    co = Part.makeBox(cover_outer_w, cover_outer_l, cover_t + skirt_h, App.Vector(ox, oy, body_h - skirt_h))
    ci = Part.makeBox(
        outer_w + 2 * cover_clear,
        outer_l + 2 * cover_clear,
        skirt_h + 0.2,
        App.Vector(-cover_clear, -cover_clear, body_h - skirt_h - 0.1),
    )
    cover_shape = co.cut(ci)

    cover_usb_y = oy + cover_outer_l - cover_wall - cover_clear - 0.6
    cover_shape = cover_shape.cut(
        Part.makeBox(
            usb_w, cover_wall + cover_clear + 0.8, usb_h,
            App.Vector(
                (cover_outer_w - usb_w) / 2.0,
                cover_usb_y,
                body_h - skirt_h + usb_bottom,
            ),
        )
    )

    for side in ("Left", "Right"):
        cx = -cover_clear if side == "Left" else outer_w + cover_clear
        for sy in snap_centers:
            cover_shape = cover_shape.cut(
                Part.makeSphere(snap_r + 0.15, App.Vector(cx, sy, snap_z))
            )

    center_xs = (
        center_x - button_center_spacing / 2.0,
        center_x + button_center_spacing / 2.0,
    )

    # Guard: both button U-slots must stay fully inside the case walls.
    # The outermost slot edge is at (button center) +/- (button_w/2 + slot).
    # A spacing that pushes a slot past [0, outer_w] would place the button in
    # or through the side wall (root cause of the "buttons at the edge" defect).
    half_span = button_w / 2.0 + button_slot_width
    left_slot_min = center_xs[0] - half_span
    right_slot_max = center_xs[1] + half_span
    edge_margin = wall  # keep at least one wall thickness from the outer edge
    if left_slot_min < edge_margin or right_slot_max > outer_w - edge_margin:
        raise RuntimeError(
            "button_center_spacing=%.2f places the flexure U-slots into the "
            "case wall (outer_w=%.2f). Reduce the spacing so both buttons stay "
            "inside [%.2f, %.2f]." % (
                button_center_spacing, outer_w, edge_margin, outer_w - edge_margin,
            )
        )

    button_front_y = outer_l - wall - board_clear - 3.2
    slot_z = body_h - 0.1
    slot_h = cover_t + 0.25

    left_button = FlexureButton(
        origin=(center_xs[0] - button_w / 2.0, button_front_y - button_len),
        width=button_w,
        length=button_len,
        slot=button_slot_width,
        rear_bridge=button_rear_bridge,
        pad_size=(actuator_w, actuator_l),
        pad_height=actuator_h,
    )
    right_button = left_button.mirrored(center_x)

    for name, button in (("BootButton", left_button), ("ResetButton", right_button)):
        u_cut = _build_flexure_cut(button, slot_z, slot_h)
        cover_shape = cover_shape.cut(u_cut).removeSplitter()

        pad_x, pad_y = button.pad_origin
        pad = Part.makeBox(
            actuator_w,
            actuator_l,
            actuator_h,
            App.Vector(pad_x, pad_y, body_h - actuator_h + 0.05),
        )
        cover_shape = cover_shape.fuse(pad).removeSplitter()

    cover = doc.addObject("Part::Feature", "TopCover")
    cover.Label = "ESP32-C3 top cover - centered narrow U-cut flexures"
    cover.Shape = cover_shape
    cover.addProperty("App::PropertyString", "ButtonDesign", "Design")
    cover.ButtonDesign = "Reusable FlexureButton; rectangular imperfect-U; 0.5 mm cut; 1.0 mm rear bridge; local pad origin."
    cover.addProperty("App::PropertyString", "ButtonPlacement", "Design")
    cover.ButtonPlacement = "Symmetric about enclosure centerline and USB-C center; behind USB-C; aligned to BOOT/RESET."
    cover.addProperty("App::PropertyString", "ActuatorDesign", "Design")
    cover.ActuatorDesign = "2.0 x 2.0 x 0.75 mm pad generated from FlexureButton.pad_origin at inner/base of U."
    cover.addProperty("App::PropertyString", "SnapDesign", "Design")
    cover.SnapDesign = "Four round snap bosses with matching spherical pockets."

    doc.recompute()
    _fit_view(doc)
    os.makedirs(os.path.dirname(output), exist_ok=True)
    doc.saveAs(output)

    return {
        "ok": True,
        "action": "create_snapfit_case",
        "document": doc.Name,
        "output_path": output,
        "parts": ["BottomCase", "TopCover"],
        "board": {"width": board_w, "length": board_l, "clearance": board_clear},
        "case": {"outer_width": outer_w, "outer_length": outer_l, "body_height": body_h, "cover_thickness": cover_t},
        "features": {
            "round_snap_count": 4,
            "button_count": 2,
            "button_style": "rectangular_imperfect_u_flexure",
            "button_orientation": "front_to_back",
            "button_floating": False,
            "button_placement": "behind_usb_c",
            "button_cut_width": button_slot_width,
            "button_center_spacing": button_center_spacing,
            "usb_c_opening": {"width": usb_w, "height": usb_h},
            "antenna_keepout": {"length": antenna_l, "width": antenna_w},
        },
    }


def _rounded_box(length, width, height, radius, origin):
    """Return a solid box with vertical edges filleted to ``radius``.

    ``origin`` is the lower corner (x, y, z). Falls back to a plain box if the
    fillet fails or the radius is non-positive.
    """
    ox, oy, oz = origin
    box = Part.makeBox(length, width, height, App.Vector(ox, oy, oz))
    if radius and radius > 0:
        try:
            vertical = [e for e in box.Edges
                        if abs(e.Vertexes[0].Point.z - e.Vertexes[1].Point.z) > 1e-6]
            box = box.makeFillet(radius, vertical)
        except Exception as exc:
            print(f"[freecad-agent] corner fillet skipped: {exc}")
    return box


def _keyhole_flexure_cut(head_cx, head_cy, z0, cut_h, radius, slot, tail_len, tail_dir=1):
    """Build a 'keyhole' flexure cut. The round actuator head sits at
    ``(head_cx, head_cy)`` and the tongue's two parallel side cuts run along y
    for ``tail_len`` in direction ``tail_dir`` (+1 = +y, -1 = -y). The pressable
    head is at ``head_cy`` and the tongue hinge is at the far end.

    ``slot`` is the cut-line thickness (kept at 0.5 mm).
    """
    head = Part.makeCylinder(radius + slot, cut_h, App.Vector(head_cx, head_cy, z0))
    head_inner = Part.makeCylinder(radius, cut_h, App.Vector(head_cx, head_cy, z0))
    ring = head.cut(head_inner)  # annular gap around the actuator head

    # IMPORTANT (printability): do NOT cut a full ring, or the head detaches
    # from the tongue and prints as a loose disc. Remove the half of the ring
    # on the tongue side so the head stays fused to the tongue -> one
    # continuous flexure (head + tongue + hinge). The opening faces tail_dir.
    keep_y = head_cy if tail_dir >= 0 else head_cy - (radius + slot)
    open_box = Part.makeBox(
        2 * (radius + slot) + 0.2, radius + slot + 0.1, cut_h + 0.2,
        App.Vector(head_cx - (radius + slot) - 0.1, keep_y, z0 - 0.1),
    )
    ring = ring.cut(open_box)  # now a U/horseshoe open toward the tongue

    # side cuts run from the head toward tail_dir; y0 is the lower y of the box
    y0 = head_cy if tail_dir >= 0 else head_cy - tail_len
    left_cut = Part.makeBox(
        slot, tail_len, cut_h,
        App.Vector(head_cx - radius - slot, y0, z0),
    )
    right_cut = Part.makeBox(
        slot, tail_len, cut_h,
        App.Vector(head_cx + radius, y0, z0),
    )
    return ring.fuse(left_cut).fuse(right_cut)


def _create_snapfit_case_v2(command):
    """Elongated ESP32-C3 snap-fit case with keyhole flexure buttons.

    Matches the physical reference: rounded rectangular case, USB-C on the
    short side, and two parallel keyhole flexures on the cover (round actuator
    head + two parallel cut-lines forming a pressable tongue).
    """
    board_w = float(command.get("board_width", 18.0))
    board_l = float(command.get("board_length", 22.5))
    board_clear = float(command.get("board_clearance", 0.25))
    wall = float(command.get("wall", 1.2))
    bottom = float(command.get("bottom_thickness", 1.2))
    body_h = float(command.get("body_height", 5.2))
    cover_t = float(command.get("cover_thickness", 1.2))
    cover_wall = float(command.get("cover_wall", 1.2))
    cover_clear = float(command.get("cover_clearance", 0.2))
    cover_lip = float(command.get("cover_lip", 0.8))
    corner_r = float(command.get("corner_radius", 2.5))

    snap_r = float(command.get("snap_radius", 1.0))
    snap_z = float(command.get("snap_z", 2.8))
    snap_y = float(command.get("snap_offset_y", 4.0))

    # keyhole flexure params
    btn_head_r = float(command.get("button_head_radius", 1.75))
    btn_tail_len = float(command.get("button_tail_length", 9.0))
    btn_slot = float(command.get("button_cut_thickness", 0.5))
    btn_spacing = float(command.get("button_row_spacing", 5.5))
    btn_head_from_left = float(command.get("button_head_from_left", 8.0))
    actuator_h = float(command.get("actuator_pad_thickness", 0.75))

    usb_w = float(command.get("usb_opening_width", 10.0))
    usb_h = float(command.get("usb_opening_height", 4.0))
    usb_bottom = float(command.get("usb_opening_bottom", 1.0))
    antenna_l = float(command.get("antenna_keepout_length", 5.0))
    antenna_w = float(command.get("antenna_keepout_width", 12.0))
    output = os.path.abspath(command.get(
        "output_path", "cad/output/esp32-c3-super-mini-snapfit-v6.FCStd"))

    if btn_slot != 0.5:
        raise RuntimeError("keyhole flexure requires a fixed 0.5 mm cut width")
    if cover_lip < 0 or cover_lip >= body_h:
        raise RuntimeError("cover_lip must be >= 0 and smaller than body_height")

    inner_w = board_w + 2 * board_clear
    inner_l = board_l + 2 * board_clear
    outer_w = inner_w + 2 * wall
    outer_l = inner_l + 2 * wall
    center_x = outer_w / 2.0

    doc = App.newDocument(command.get("document", "ESP32C3SnapFitCaseKeyhole"))

    # --- body: rounded shell, open top ---
    tray = _rounded_box(outer_w, outer_l, body_h, corner_r, (0, 0, 0)).cut(
        _rounded_box(inner_w, inner_l, body_h - bottom,
                     max(corner_r - wall, 0.0), (wall, wall, bottom))
    )
    # USB-C on the short (front) side, centered on width
    usb_x = center_x - usb_w / 2.0
    tray = tray.cut(
        Part.makeBox(usb_w, wall + 0.8, usb_h,
                     App.Vector(usb_x, outer_l - wall - 0.4, usb_bottom))
    )
    # antenna relief on the opposite short side
    ak_x = center_x - antenna_w / 2.0
    tray = tray.cut(
        Part.makeBox(antenna_w, antenna_l + 0.2, min(1.5, body_h - bottom),
                     App.Vector(ak_x, wall - 0.2, body_h - 1.5))
    )

    body = doc.addObject("Part::Feature", "BottomCase")
    body.Label = "ESP32-C3 bottom case (keyhole v2)"
    body.Shape = tray

    # snap bosses
    snap_centers = (snap_y, outer_l - snap_y)
    for side, x in (("Left", 0.0), ("Right", outer_w)):
        for idx, sy in enumerate(snap_centers, 1):
            cx = x + snap_r * 0.55 if side == "Left" else x - snap_r * 0.55
            sphere = Part.makeSphere(snap_r, App.Vector(cx, sy, snap_z))
            clip_x = -0.1 if side == "Left" else outer_w - snap_r - 0.1
            clip = Part.makeBox(snap_r + 0.2, 2 * snap_r + 0.4, 2 * snap_r + 0.4,
                                App.Vector(clip_x, sy - snap_r - 0.2, snap_z - snap_r - 0.2))
            boss = sphere.common(clip)
            body.Shape = body.Shape.fuse(boss).removeSplitter()
            o = doc.addObject("Part::Feature", f"SnapBoss{side}{idx}")
            o.Label = f"Round snap boss {side} {idx}"
            o.Shape = boss

    # --- cover: rounded lid with skirt derived from body_h ---
    skirt_h = body_h - cover_lip
    if skirt_h <= snap_z:
        raise RuntimeError("cover skirt too short to capture snaps")
    cover_outer_w = outer_w + 2 * (cover_wall + cover_clear)
    cover_outer_l = outer_l + 2 * (cover_wall + cover_clear)
    cox = -(cover_wall + cover_clear)
    coy = -(cover_wall + cover_clear)
    co = _rounded_box(cover_outer_w, cover_outer_l, cover_t + skirt_h,
                      corner_r + cover_wall + cover_clear,
                      (cox, coy, body_h - skirt_h))
    ci = _rounded_box(outer_w + 2 * cover_clear, outer_l + 2 * cover_clear,
                      skirt_h + 0.2, corner_r + cover_clear,
                      (-cover_clear, -cover_clear, body_h - skirt_h - 0.1))
    cover_shape = co.cut(ci)

    # snap pockets
    for side in ("Left", "Right"):
        cx = -cover_clear if side == "Left" else outer_w + cover_clear
        for sy in snap_centers:
            cover_shape = cover_shape.cut(
                Part.makeSphere(snap_r + 0.15, App.Vector(cx, sy, snap_z)))

    # USB-C opening in the cover, on the same short side as the body, centered
    cover_usb_y = coy + cover_outer_l - cover_wall - cover_clear - 0.6
    cover_shape = cover_shape.cut(
        Part.makeBox(
            usb_w, cover_wall + cover_clear + 0.8, usb_h,
            App.Vector(center_x - usb_w / 2.0, cover_usb_y,
                       body_h - skirt_h + usb_bottom),
        )
    )

    # --- keyhole flexures: two parallel tongues stacked across x, heads placed
    # just behind the USB-C side; tongues hinge toward the case interior. ---
    z0 = body_h - 0.1
    cut_h = cover_t + 0.3
    usb_side_y = outer_l - wall  # inner face of the USB (front) wall
    head_y = usb_side_y - btn_head_r - 2.0  # heads sit just behind USB
    tail_len = btn_tail_len
    # two heads aligned across x, symmetric about the case center
    head_xs = (center_x - btn_spacing / 2.0, center_x + btn_spacing / 2.0)
    # heads sit near the USB-C side; tongues hinge toward the interior (-y)
    for name, hx in (("BootFlexure", head_xs[0]), ("ResetFlexure", head_xs[1])):
        cut = _keyhole_flexure_cut(hx, head_y, z0, cut_h,
                                   btn_head_r, btn_slot, tail_len, tail_dir=-1)
        cover_shape = cover_shape.cut(cut).removeSplitter()
        # actuator bump under the round head (pad sits near USB-C)
        bump = Part.makeCylinder(btn_head_r, actuator_h,
                                 App.Vector(hx, head_y, body_h - actuator_h + 0.05))
        cover_shape = cover_shape.fuse(bump).removeSplitter()

    cover = doc.addObject("Part::Feature", "TopCover")
    cover.Label = "ESP32-C3 top cover (keyhole flexures v2)"
    cover.Shape = cover_shape.removeSplitter()

    doc.recompute()
    _fit_view(doc)
    os.makedirs(os.path.dirname(output), exist_ok=True)
    doc.saveAs(output)

    return {
        "ok": True,
        "action": "create_snapfit_case_v2",
        "document": doc.Name,
        "output_path": output,
        "parts": ["BottomCase", "TopCover"],
        "case": {"outer_width": outer_w, "outer_length": outer_l,
                 "body_height": body_h, "cover_thickness": cover_t,
                 "corner_radius": corner_r},
        "features": {
            "round_snap_count": 4,
            "button_count": 2,
            "button_style": "keyhole_flexure",
            "button_head_radius": btn_head_r,
            "button_tail_length": btn_tail_len,
            "button_row_spacing": btn_spacing,
            "button_cut_width": btn_slot,
            "usb_c_opening": {"width": usb_w, "height": usb_h},
            "antenna_keepout": {"length": antenna_l, "width": antenna_w},
        },
    }


def _render_view(command):
    """Save one or more PNG screenshots of a document's active view.

    command: {document?, path, views?=["top","iso"], width?, height?, background?}
    Returns the list of written image paths.
    """
    doc_name = command.get("document")
    gdoc = Gui.getDocument(doc_name) if doc_name else Gui.ActiveDocument
    if gdoc is None:
        raise RuntimeError("No active GUI document to render")
    view = gdoc.ActiveView
    width = int(command.get("width", 1400))
    height = int(command.get("height", 1000))
    bg = command.get("background", "White")
    base = command.get("path")
    if not base:
        raise RuntimeError("render_view needs a 'path'")
    views = command.get("views", ["top", "iso"])
    view_fns = {
        "top": getattr(view, "viewTop", None),
        "front": getattr(view, "viewFront", None),
        "iso": getattr(view, "viewIsometric", None),
        "rear": getattr(view, "viewRear", None),
    }
    written = []
    root, ext = os.path.splitext(base)
    ext = ext or ".png"
    for v in views:
        fn = view_fns.get(v)
        if fn:
            try:
                fn()
            except Exception:
                pass
        try:
            view.fitAll()
        except Exception:
            pass
        out = base if len(views) == 1 else f"{root}_{v}{ext}"
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        view.saveImage(out, width, height, bg)
        written.append(out)
    return {"ok": True, "action": "render_view", "document": gdoc.Document.Name,
            "images": written}


def _create_mac_mini_case(command):
    """Protective 3D-printable case for the Mac mini M4 (2024).

    Official device size: 127 x 127 mm footprint, 50 mm tall, rounded cuboid.
    This builds a two-part sleeve: an open-top tray that the Mac mini sits in,
    plus a lid. The rear wall has a full port cut-out, the bottom has a vent
    grille (the M4 intakes from the bottom perimeter), and the corners are
    rounded to echo the device.
    """
    # device dimensions (mm) — default to official Mac mini M4 numbers
    dev_w = float(command.get("device_width", 127.0))
    dev_d = float(command.get("device_depth", 127.0))
    dev_h = float(command.get("device_height", 50.0))
    clr = float(command.get("clearance", 0.4))          # per-side gap
    wall = float(command.get("wall", 2.4))
    bottom = float(command.get("bottom_thickness", 2.4))
    corner_r = float(command.get("corner_radius", 8.0))  # device has ~ rounded corners
    lid_t = float(command.get("lid_thickness", 2.4))
    lid_clear = float(command.get("lid_clearance", 0.3))
    lid_skirt = float(command.get("lid_skirt", 8.0))
    foot_h = float(command.get("foot_height", 3.0))
    rear_port_h = float(command.get("rear_port_height", 34.0))   # port band height
    rear_port_margin = float(command.get("rear_port_side_margin", 10.0))
    vent_hole = float(command.get("vent_hole", 5.0))
    vent_gap = float(command.get("vent_gap", 4.0))
    output = os.path.abspath(command.get(
        "output_path", "cad/output/mac-mini-m4-case.FCStd"))

    inner_w = dev_w + 2 * clr
    inner_d = dev_d + 2 * clr
    inner_h = dev_h + 2.0            # a little headroom above the device
    outer_w = inner_w + 2 * wall
    outer_d = inner_d + 2 * wall
    tray_h = bottom + inner_h

    for v, n in ((dev_w, "device_width"), (dev_d, "device_depth"),
                 (dev_h, "device_height"), (wall, "wall"), (bottom, "bottom")):
        if v <= 0:
            raise RuntimeError(f"{n} must be positive")
    if corner_r * 2 >= min(outer_w, outer_d):
        raise RuntimeError("corner_radius too large for the footprint")

    doc = App.newDocument(command.get("document", "MacMiniM4Case"))

    # --- tray: rounded outer shell minus rounded inner cavity ---
    tray = _rounded_box(outer_w, outer_d, tray_h, corner_r, (0, 0, 0)).cut(
        _rounded_box(inner_w, inner_d, inner_h + 0.1,
                     max(corner_r - wall, 1.0), (wall, wall, bottom))
    )

    cx = outer_w / 2.0

    # rear port opening: a wide band across the back wall (y = outer_d side)
    port_w = inner_w - 2 * rear_port_margin
    if port_w > 0:
        port_z0 = bottom + 3.0
        tray = tray.cut(
            Part.makeBox(port_w, wall + 1.0, min(rear_port_h, inner_h - 3.0),
                         App.Vector(cx - port_w / 2.0, outer_d - wall - 0.5, port_z0))
        )

    # bottom vent grille (device intakes air from the bottom)
    step = vent_hole + vent_gap
    gx0 = wall + step
    gy0 = wall + step
    x = gx0
    while x < outer_w - wall - step:
        y = gy0
        while y < outer_d - wall - step:
            tray = tray.cut(
                Part.makeCylinder(vent_hole / 2.0, bottom + 0.2,
                                  App.Vector(x, y, -0.1))
            )
            y += step
        x += step

    # four small feet under the tray
    foot_r = 6.0
    foot_inset = corner_r + 2.0
    feet_pos = [(foot_inset, foot_inset), (outer_w - foot_inset, foot_inset),
                (foot_inset, outer_d - foot_inset), (outer_w - foot_inset, outer_d - foot_inset)]
    for (fx, fy) in feet_pos:
        foot = Part.makeCylinder(foot_r, foot_h, App.Vector(fx, fy, -foot_h))
        tray = tray.fuse(foot)

    body = doc.addObject("Part::Feature", "MacMiniTray")
    body.Label = "Mac mini M4 case tray"
    body.Shape = tray.removeSplitter()

    # --- lid: rounded cap with a downward skirt that overlaps the tray ---
    lo_w = outer_w + 2 * (wall + lid_clear)
    lo_d = outer_d + 2 * (wall + lid_clear)
    lox = -(wall + lid_clear)
    loy = -(wall + lid_clear)
    lid_outer = _rounded_box(lo_w, lo_d, lid_t + lid_skirt,
                             corner_r + wall + lid_clear,
                             (lox, loy, tray_h - lid_skirt))
    lid_inner = _rounded_box(outer_w + 2 * lid_clear, outer_d + 2 * lid_clear,
                             lid_skirt + 0.2, corner_r + lid_clear,
                             (-lid_clear, -lid_clear, tray_h - lid_skirt - 0.1))
    lid_shape = lid_outer.cut(lid_inner)

    # top vent grille on the lid as well
    x = gx0
    while x < outer_w - wall - step:
        y = gy0
        while y < outer_d - wall - step:
            lid_shape = lid_shape.cut(
                Part.makeCylinder(vent_hole / 2.0, lid_t + 0.4,
                                  App.Vector(x, y, tray_h + lid_t - 0.2))
            )
            y += step
        x += step

    # match the rear port cut on the lid skirt so the back stays open
    if port_w > 0:
        lid_shape = lid_shape.cut(
            Part.makeBox(port_w, wall + lid_clear + 1.0, lid_skirt + 0.2,
                         App.Vector(cx - port_w / 2.0, outer_d - wall + lid_clear - 0.5,
                                    tray_h - lid_skirt))
        )

    lid = doc.addObject("Part::Feature", "MacMiniLid")
    lid.Label = "Mac mini M4 case lid"
    lid.Shape = lid_shape.removeSplitter()

    doc.recompute()
    _fit_view(doc)
    os.makedirs(os.path.dirname(output), exist_ok=True)
    doc.saveAs(output)

    return {
        "ok": True,
        "action": "create_mac_mini_case",
        "document": doc.Name,
        "output_path": output,
        "parts": ["MacMiniTray", "MacMiniLid"],
        "device": {"width": dev_w, "depth": dev_d, "height": dev_h,
                   "source": "Apple Mac mini M4 (2024) official: 127 x 127 x 50 mm"},
        "case": {"outer_width": outer_w, "outer_depth": outer_d,
                 "tray_height": tray_h, "wall": wall, "clearance": clr,
                 "corner_radius": corner_r},
        "features": {"rear_port_opening": {"width": port_w, "height": rear_port_h},
                     "bottom_vent": True, "top_vent": True, "feet": 4},
    }


def execute_command(command):
    action = command.get("action")
    if action == "ping":
        return {"ok": True, "message": "FreeCAD agent is alive"}
    if action == "version":
        return {"ok": True, "action": "version",
                "actions": ["ping", "version", "reload", "create_sphere",
                            "open_model", "inspect_model", "inspect_geometry",
                            "render_view",
                            "create_snapfit_case", "create_snapfit_case_v2",
                            "create_mac_mini_case"]}
    if action == "reload":
        # In-place code refresh. The running QTimer holds a reference to the OLD
        # _poll_server object, so after exec we must reconnect it to the new one,
        # otherwise the timer keeps running stale code. We then self-verify by
        # checking a sentinel and report honestly if the swap did not take.
        path = command.get("path")
        if not path:
            path = globals().get("__file__")
            if path:
                path = os.path.abspath(path)
        if not path or not os.path.isfile(path):
            return {"ok": False, "error": f"reload needs a valid 'path'; got {path!r}"}
        try:
            with open(path, "r", encoding="utf-8") as fh:
                source = fh.read()
            g = globals()
            saved_sock = g.get("_server_socket")
            saved_timer = g.get("_server_timer")
            g["__file__"] = path
            exec(compile(source, path, "exec"), g)
            g["_server_socket"] = saved_sock
            g["_server_timer"] = saved_timer
            # reconnect the live timer to the freshly-defined poller
            if saved_timer is not None:
                try:
                    saved_timer.timeout.disconnect()
                except Exception:
                    pass
                saved_timer.timeout.connect(g["_poll_server"])
            swapped = "_render_view" in g  # sentinel from the new code
        except Exception as exc:
            return {"ok": False, "error": f"reload failed: {exc}"}
        return {"ok": True, "action": "reload", "path": path,
                "reconnected_timer": saved_timer is not None,
                "has_render_view": swapped,
                "note": ("code swapped in place" if swapped else
                         "exec ran but sentinel missing; a FreeCAD restart may be needed")}
        return {"ok": True, "action": "reload", "path": path,
                "has_v2": "_create_snapfit_case_v2" in globals()}
    if action == "create_sphere":
        doc = App.ActiveDocument or App.newDocument("AgentTest")
        sphere = doc.addObject("Part::Sphere", "AgentSphere")
        sphere.Radius = float(command.get("radius", 10))
        doc.recompute()
        _fit_view(doc)
        return {"ok": True, "action": action, "object": sphere.Name, "radius": sphere.Radius, "document": doc.Name}
    if action == "open_model":
        path = os.path.abspath(command.get("path", ""))
        if not os.path.isfile(path):
            raise RuntimeError(f"CAD file not found: {path}")
        doc = App.openDocument(path)
        _fit_view(doc)
        return {"ok": True, "action": action, "path": path, "document": doc.Name, "label": doc.Label}
    if action == "inspect_model":
        doc = App.ActiveDocument
        if doc is None:
            raise RuntimeError("No active FreeCAD document")
        return {"ok": True, "action": action, "document": doc.Name,
                "objects": [{"name": o.Name, "label": o.Label, "type": o.TypeId} for o in doc.Objects]}
    if action == "inspect_geometry":
        return _inspect_geometry(command)
    if action == "render_view":
        return _render_view(command)
    if action == "create_snapfit_case":
        return _create_snapfit_case(command)
    if action == "create_snapfit_case_v2":
        return _create_snapfit_case_v2(command)
    if action == "create_mac_mini_case":
        return _create_mac_mini_case(command)
    return {"ok": False, "error": f"Unsupported action: {action}"}


def _poll_server():
    global _server_socket
    if _server_socket is None:
        return
    while True:
        try:
            connection, _ = _server_socket.accept()
            data = connection.recv(65536)
            if not data:
                connection.close()
                continue
            try:
                command = json.loads(data.decode("utf-8"))
                result = execute_command(command)
            except Exception as exc:
                result = {"ok": False, "error": str(exc)}
            connection.sendall(json.dumps(result).encode("utf-8"))
            connection.close()
        except Exception as exc:
            print(f"[freecad-agent] listener error: {exc}")
            break


def start_server(force=True):
    """Start (or restart) the TCP listener.

    Reload-safe: by default it tears down any existing socket/timer first so
    that re-importing a fresh copy of this module always takes over the port
    with the newest code, instead of leaving a stale listener bound.
    """
    global _server_socket, _server_timer
    if _server_socket is not None:
        if not force:
            print(f"[freecad-agent] already listening on {HOST}:{PORT}")
            return
        # tear down the previous listener before rebinding
        try:
            stop_server()
        except Exception as exc:
            print(f"[freecad-agent] stop before restart failed: {exc}")

    last_exc = None
    for _ in range(20):
        try:
            _server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            _server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            _server_socket.bind((HOST, PORT))
            break
        except OSError as exc:
            last_exc = exc
            try:
                _server_socket.close()
            except Exception:
                pass
            _server_socket = None
            import time as _t
            _t.sleep(0.1)
    if _server_socket is None:
        raise RuntimeError(f"could not bind {HOST}:{PORT}: {last_exc}")

    _server_socket.listen(8)
    _server_socket.setblocking(False)

    print(f"[freecad-agent] listening on {HOST}:{PORT}")
    _server_timer = QtCore.QTimer()
    _server_timer.timeout.connect(_poll_server)
    _server_timer.start(100)


def stop_server():
    global _server_socket, _server_timer
    if _server_timer is not None:
        _server_timer.stop()
        _server_timer.deleteLater()
        _server_timer = None
    if _server_socket is not None:
        try:
            _server_socket.close()
        finally:
            _server_socket = None
    print("[freecad-agent] stopped")
