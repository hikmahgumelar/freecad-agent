import json
import os
import socket
from dataclasses import replace

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
    """Build the exact rectangular imperfect-U cut from a reusable feature."""
    ox, oy = button.origin
    cut_depth = button.length - button.rear_bridge
    if cut_depth <= 0:
        raise RuntimeError("rear_bridge must be smaller than button length")

    left_slot = Part.makeBox(
        button.slot,
        cut_depth,
        slot_h,
        App.Vector(ox - button.slot, oy, slot_z),
    )
    right_slot = Part.makeBox(
        button.slot,
        cut_depth,
        slot_h,
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

    values = [board_w, board_l, board_clear, wall, bottom, body_h, cover_t, cover_wall, cover_clear,
              snap_r, snap_z, snap_y, button_len, button_w, button_slot_width,
              button_center_spacing, button_rear_bridge, actuator_w, actuator_l, actuator_h,
              usb_w, usb_h, antenna_l, antenna_w]
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
        Part.makeBox(usb_w, wall + 0.8, usb_h,
                     App.Vector(usb_x, outer_l - wall - 0.4, usb_bottom))
    )

    ak_x = center_x - antenna_w / 2.0
    ak_y = outer_l - wall - antenna_l
    tray = tray.cut(
        Part.makeBox(antenna_w, antenna_l + 0.2,
                     min(1.5, body_h - bottom),
                     App.Vector(ak_x, ak_y, body_h - 1.5))
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

    skirt_h = 3.2
    cover_outer_w = outer_w + 2 * (cover_wall + cover_clear)
    cover_outer_l = outer_l + 2 * (cover_wall + cover_clear)
    ox = -(cover_wall + cover_clear)
    oy = -(cover_wall + cover_clear)
    co = Part.makeBox(cover_outer_w, cover_outer_l, cover_t + skirt_h,
                      App.Vector(ox, oy, body_h - skirt_h))
    ci = Part.makeBox(outer_w + 2 * cover_clear, outer_l + 2 * cover_clear,
                      skirt_h + 0.2,
                      App.Vector(-cover_clear, -cover_clear, body_h - skirt_h - 0.1))
    cover_shape = co.cut(ci)

    cover_usb_y = oy + cover_outer_l - cover_wall - cover_clear - 0.6
    cover_shape = cover_shape.cut(
        Part.makeBox(usb_w, cover_wall + cover_clear + 0.8, usb_h,
                     App.Vector((cover_outer_w - usb_w) / 2.0, cover_usb_y,
                                body_h - skirt_h + usb_bottom))
    )

    for side in ("Left", "Right"):
        cx = -cover_clear if side == "Left" else outer_w + cover_clear
        for sy in snap_centers:
            cover_shape = cover_shape.cut(Part.makeSphere(snap_r + 0.15,
                                                           App.Vector(cx, sy, snap_z)))

    center_xs = (center_x - button_center_spacing / 2.0,
                 center_x + button_center_spacing / 2.0)
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
        "features": {"round_snap_count": 4, "button_count": 2,
                     "button_style": "rectangular_imperfect_u_flexure",
                     "button_orientation": "front_to_back", "button_floating": False,
                     "button_placement": "behind_usb_c", "button_cut_width": button_slot_width,
                     "button_center_spacing": button_center_spacing,
                     "usb_c_opening": {"width": usb_w, "height": usb_h},
                     "antenna_keepout": {"length": antenna_l, "width": antenna_w}}
    }


def execute_command(command):
    action = command.get("action")
    if action == "ping": return {"ok": True, "message": "FreeCAD agent is alive"}
    if action == "create_sphere":
        doc = App.ActiveDocument or App.newDocument("AgentTest")
        sphere = doc.addObject("Part::Sphere", "AgentSphere")
        sphere.Radius = float(command.get("radius", 10)); doc.recompute(); _fit_view(doc)
        return {"ok": True, "action": action, "object": sphere.Name, "radius": sphere.Radius, "document": doc.Name}
    if action == "open_model":
        path = os.path.abspath(command.get("path", ""))
        if not os.path.isfile(path): raise RuntimeError(f"CAD file not found: {path}")
        doc = App.openDocument(path); _fit_view(doc)
        return {"ok": True, "action": action, "path": path, "document": doc.Name, "label": doc.Label}
    if action == "inspect_model":
        doc = App.ActiveDocument
        if doc is None: raise RuntimeError("No active FreeCAD document")
        return {"ok": True, "action": action, "document": doc.Name,
                "objects": [{"name": o.Name, "label": o.Label, "type": o.TypeId} for o in doc.Objects]}
    if action == "inspect_geometry": return _inspect_geometry(command)
    if action == "create_snapfit_case": return _create_snapfit_case(command)
    return {"ok": False, "error": f"Unsupported action: {action}"}


def _poll_server():
    global _server_socket
    if _server_socket is None: return
    while True:
        try: connection, _ = _server_socket.accept()