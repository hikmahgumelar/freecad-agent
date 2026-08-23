import json
import os
import socket

import FreeCAD as App
import FreeCADGui as Gui
import Part
from PySide import QtCore

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


def _get_tip(doc, body_name="Body"):
    body = doc.getObject(body_name)
    if body is None or getattr(body, "Tip", None) is None or body.Tip.Shape.isNull():
        raise RuntimeError(f"Body '{body_name}' has no valid Tip shape")
    return body, body.Tip


def _inspect_geometry(command):
    doc = App.ActiveDocument
    if doc is None:
        raise RuntimeError("No active FreeCAD document")
    body, tip = _get_tip(doc, command.get("body", "Body"))
    s = tip.Shape
    b = s.BoundBox
    return {
        "ok": True,
        "action": "inspect_geometry",
        "document": doc.Name,
        "body": body.Name,
        "tip": tip.Name,
        "bounding_box": {"xmin": b.XMin, "xmax": b.XMax, "ymin": b.YMin, "ymax": b.YMax, "zmin": b.ZMin, "zmax": b.ZMax,
                         "x_length": b.XLength, "y_length": b.YLength, "z_length": b.ZLength},
        "solids": len(s.Solids), "shells": len(s.Shells), "faces": len(s.Faces), "edges": len(s.Edges)
    }


def _create_case_rails(command):
    doc = App.ActiveDocument
    if doc is None:
        raise RuntimeError("No active FreeCAD document")
    _, tip = _get_tip(doc, command.get("body", "Body"))
    b = tip.Shape.BoundBox
    width = float(command.get("rail_width", 1.6))
    height = float(command.get("rail_height", 1.8))
    inset = float(command.get("inset", 2.0))
    output = os.path.abspath(command.get("output_path", "/home/hikmah/projectx/freecad-agent/cad/output/case-rails.FCStd"))
    for name in ("SliderCaseRailLeft", "SliderCaseRailRight"):
        old = doc.getObject(name)
        if old:
            doc.removeObject(name)
    z = b.ZMin
    left = doc.addObject("Part::Feature", "SliderCaseRailLeft")
    left.Label = "Slider case rail left"
    left.Shape = Part.makeBox(max(0.1, b.XLength - 2 * inset), width, height, App.Vector(b.XMin + inset, b.YMin + inset, z))
    right = doc.addObject("Part::Feature", "SliderCaseRailRight")
    right.Label = "Slider case rail right"
    right.Shape = Part.makeBox(max(0.1, b.XLength - 2 * inset), width, height, App.Vector(b.XMin + inset, b.YMax - inset - width, z))
    doc.recompute(); _fit_view(doc); os.makedirs(os.path.dirname(output), exist_ok=True); doc.saveAs(output)
    return {"ok": True, "action": "create_case_rails", "output_path": output, "objects": [left.Name, right.Name]}


def _create_slider_cover(command):
    doc = App.ActiveDocument
    if doc is None:
        raise RuntimeError("No active FreeCAD document")
    _, tip = _get_tip(doc, command.get("body", "Body"))
    b = tip.Shape.BoundBox
    width = float(command.get("width", b.XLength))
    depth = float(command.get("depth", b.YLength))
    thickness = float(command.get("thickness", 1.6))
    clearance = float(command.get("clearance", 0.2))
    output = os.path.abspath(command.get("output_path", "/home/hikmah/projectx/freecad-agent/cad/output/slider-cover.FCStd"))
    old = doc.getObject("SliderCover")
    if old:
        doc.removeObject(old)
    cover = doc.addObject("Part::Feature", "SliderCover")
    cover.Label = "Slider cover"
    cover.Shape = Part.makeBox(width, depth, thickness, App.Vector(b.XMin, b.YMin, b.ZMax + clearance))
    doc.recompute(); _fit_view(doc); os.makedirs(os.path.dirname(output), exist_ok=True); doc.saveAs(output)
    return {"ok": True, "action": "create_slider_cover", "output_path": output, "objects": [cover.Name]}


def _create_smoke_test_box(command):
    outer_x, outer_y = 120.0, 85.0
    wall = float(command.get("wall", 3.0))
    bottom = float(command.get("bottom_thickness", 3.0))
    height = float(command.get("body_height", 50.0))
    cover_height = float(command.get("cover_height", 40.0))
    cover_wall = float(command.get("cover_wall", 3.0))
    cover_clear = float(command.get("cover_clearance_per_side", 0.3))
    cover_top = float(command.get("cover_top_thickness", 3.0))
    output = os.path.abspath(command.get("output_path", "/home/hikmah/projectx/freecad-agent/cad/output/smoke-test-box.FCStd"))
    doc = App.newDocument(command.get("document", "SmokeTestBox"))
    inner_x, inner_y = outer_x - 2 * wall, outer_y - 2 * wall
    body = doc.addObject("Part::Feature", "Body")
    body.Label = "Smoke test body"
    body.Shape = Part.makeBox(outer_x, outer_y, height).cut(Part.makeBox(inner_x, inner_y, height - bottom, App.Vector(wall, wall, bottom)))
    plate = doc.addObject("Part::Feature", "Plate")
    plate.Label = "Removable plate"
    plate.Shape = Part.makeBox(inner_x - 0.6, inner_y - 0.6, 3.0, App.Vector(wall + 0.3, wall + 0.3, height / 2))
    cover_x, cover_y = outer_x + 2 * cover_clear, outer_y + 2 * cover_clear
    cover = doc.addObject("Part::Feature", "Cover")
    cover.Label = "Separate cover"
    co = Part.makeBox(cover_x, cover_y, cover_height, App.Vector(-cover_clear, -cover_clear, 0))
    ci = Part.makeBox(cover_x - 2 * cover_wall, cover_y - 2 * cover_wall, cover_height - cover_top, App.Vector(-cover_clear + cover_wall, -cover_clear + cover_wall, 0))
    cover.Shape = co.cut(ci)
    doc.recompute(); _fit_view(doc); os.makedirs(os.path.dirname(output), exist_ok=True); doc.saveAs(output)
    return {"ok": True, "action": "create_smoke_test_box", "output_path": output, "parts": ["Body", "Plate", "Cover"]}


def _capsule(length, width, height):
    if length < width:
        raise RuntimeError("button_length must be >= button_width")
    r = width / 2.0
    straight = length - width
    s = Part.makeBox(straight, width, height, App.Vector(0, 0, 0))
    c1 = Part.makeCylinder(r, height, App.Vector(0, r, 0))
    c2 = Part.makeCylinder(r, height, App.Vector(straight, r, 0))
    return s.fuse(c1).fuse(c2).removeSplitter()


def _create_snapfit_case(command):
    """Compact ESP32-C3 Super Mini enclosure: 2-piece, USB-C opening, solid buttons, round snaps."""
    board_w = float(command.get("board_width", 18.0))
    board_l = float(command.get("board_length", 22.5))
    board_clear = float(command.get("board_clearance", 0.45))
    wall = float(command.get("wall", 1.2))
    bottom = float(command.get("bottom_thickness", 1.2))
    body_h = float(command.get("body_height", 5.2))
    cover_t = float(command.get("cover_thickness", 1.2))
    cover_wall = float(command.get("cover_wall", 1.2))
    cover_clear = float(command.get("cover_clearance", 0.2))
    snap_r = float(command.get("snap_radius", 1.0))
    snap_z = float(command.get("snap_z", 2.8))
    snap_y = float(command.get("snap_offset_y", 4.0))
    button_len = float(command.get("button_length", 5.2))
    button_w = float(command.get("button_width", 2.8))
    button_h = float(command.get("button_height", 0.8))
    button_gap = float(command.get("button_gap", 1.2))
    button_y = float(command.get("button_y", 2.7))
    usb_w = float(command.get("usb_opening_width", 10.0))
    usb_h = float(command.get("usb_opening_height", 4.0))
    usb_bottom = float(command.get("usb_opening_bottom", 1.0))
    antenna_l = float(command.get("antenna_keepout_length", 5.0))
    antenna_w = float(command.get("antenna_keepout_width", 12.0))
    output = os.path.abspath(command.get("output_path", "/home/hikmah/projectx/freecad-agent/cad/output/esp32-c3-super-mini-snapfit-v1.FCStd"))

    if min(board_w, board_l, board_clear, wall, bottom, body_h, cover_t, cover_wall, cover_clear, snap_r, snap_z, snap_y, button_len, button_w, button_h, button_gap, usb_w, usb_h, antenna_l, antenna_w) <= 0:
        raise RuntimeError("All snap-fit dimensions must be positive")
    if button_len < button_w or button_y + button_w > board_l:
        raise RuntimeError("Button geometry is outside the board envelope")
    if usb_w >= board_w + 2 * board_clear:
        raise RuntimeError("USB opening is too wide")
    if body_h <= bottom + 2.0:
        raise RuntimeError("body_height is too small for component clearance")

    inner_w = board_w + 2 * board_clear
    inner_l = board_l + 2 * board_clear
    outer_w = inner_w + 2 * wall
    outer_l = inner_l + 2 * wall
    doc = App.newDocument(command.get("document", "ESP32C3SnapFitCaseV1"))

    # Bottom tray. Board sits on the floor; top is open. USB-C is exposed through a front wall cutout.
    tray = Part.makeBox(outer_w, outer_l, body_h).cut(Part.makeBox(inner_w, inner_l, body_h - bottom, App.Vector(wall, wall, bottom)))
    usb_x = (outer_w - usb_w) / 2.0
    tray = tray.cut(Part.makeBox(usb_w, wall + 0.8, usb_h, App.Vector(usb_x, outer_l - wall - 0.4, usb_bottom)))

    # Local RF relief at the rear/antenna end. It does not create a button hole.
    ak_x = (outer_w - antenna_w) / 2.0
    ak_y = outer_l - wall - antenna_l
    tray = tray.cut(Part.makeBox(antenna_w, antenna_l + 0.2, min(1.5, body_h - bottom), App.Vector(ak_x, ak_y, body_h - 1.5)))
    body = doc.addObject("Part::Feature", "BottomCase")
    body.Label = "ESP32-C3 bottom case"
    body.Shape = tray
    body.addProperty("App::PropertyString", "Contract", "Design")
    body.Contract = "ESP32-C3 Super Mini; compact fit; USB-C exposed; 4 round snaps; no screws."
    body.addProperty("App::PropertyLength", "BoardWidth", "Design"); body.BoardWidth = board_w
    body.addProperty("App::PropertyLength", "BoardLength", "Design"); body.BoardLength = board_l
    body.addProperty("App::PropertyLength", "BoardClearance", "Printability"); body.BoardClearance = board_clear

    # Four rounded snap bosses, two on each side wall.
    snap_centers = (snap_y, outer_l - snap_y)
    for side, x in (("Left", 0.0), ("Right", outer_w)):
        for idx, sy in enumerate(snap_centers, 1):
            cx = x + snap_r * 0.55 if side == "Left" else x - snap_r * 0.55
            sphere = Part.makeSphere(snap_r, App.Vector(cx, sy, snap_z))
            # Keep only the part attached to the wall so the snap remains printable.
            clip_x = -0.1 if side == "Left" else outer_w - snap_r - 0.1
            clip = Part.makeBox(snap_r + 0.2, 2 * snap_r + 0.4, 2 * snap_r + 0.4, App.Vector(clip_x, sy - snap_r - 0.2, snap_z - snap_r - 0.2))
            boss = sphere.common(clip)
            body.Shape = body.Shape.fuse(boss).removeSplitter()
            obj = doc.addObject("Part::Feature", f"SnapBoss{side}{idx}")
            obj.Label = f"Round snap boss {side} {idx}"
            obj.Shape = boss

    # Top cap with an outside skirt. The skirt receives the round bosses in blind spherical pockets.
    skirt_h = 3.2
    cover_outer_w = outer_w + 2 * (cover_wall + cover_clear)
    cover_outer_l = outer_l + 2 * (cover_wall + cover_clear)
    ox, oy = -(cover_wall + cover_clear), -(cover_wall + cover_clear)
    co = Part.makeBox(cover_outer_w, cover_outer_l, cover_t + skirt_h, App.Vector(ox, oy, body_h - skirt_h))
    ci = Part.makeBox(outer_w + 2 * cover_clear, outer_l + 2 * cover_clear, skirt_h + 0.2, App.Vector(-cover_clear, -cover_clear, body_h - skirt_h - 0.1))
    cover_shape = co.cut(ci)
    cover_shape = cover_shape.cut(Part.makeBox(usb_w, cover_wall + cover_clear + 0.8, usb_h, App.Vector((cover_outer_w - usb_w) / 2.0, oy - 0.2, body_h - skirt_h + usb_bottom)))
    for side in ("Left", "Right"):
        cx = cover_wall + cover_clear if side == "Left" else cover_outer_w - cover_wall - cover_clear
        for sy in snap_centers:
            cover_shape = cover_shape.cut(Part.makeSphere(snap_r + 0.15, App.Vector(cx, sy, snap_z)))

    # Solid elongated buttons, integral with the top cover, plus underside plungers.
    bx1 = (board_w - 2 * button_len - button_gap) / 2.0
    bx2 = bx1 + button_len + button_gap
    top_z = body_h + cover_t
    for name, bx in (("BootButton", bx1), ("ResetButton", bx2)):
        button = _capsule(button_len, button_w, button_h)
        button.translate(App.Vector(bx + wall + board_clear, wall + board_clear + button_y, top_z))
        plunger = Part.makeCylinder(0.9, cover_t + 0.05, App.Vector(bx + wall + board_clear + button_len / 2.0, wall + board_clear + button_y + button_w / 2.0, body_h - 0.05))
        cover_shape = cover_shape.fuse(button).fuse(plunger).removeSplitter()

    cover = doc.addObject("Part::Feature", "TopCover")
    cover.Label = "ESP32-C3 top cover - solid buttons"
    cover.Shape = cover_shape
    cover.addProperty("App::PropertyString", "ButtonDesign", "Design")
    cover.ButtonDesign = "Solid elongated buttons; integral to cover; no open button holes."
    cover.addProperty("App::PropertyString", "SnapDesign", "Design")
    cover.SnapDesign = "Four round snap bosses with matching spherical pockets."
    cover.addProperty("App::PropertyLength", "AntennaKeepoutLength", "RF"); cover.AntennaKeepoutLength = antenna_l
    cover.addProperty("App::PropertyLength", "AntennaKeepoutWidth", "RF"); cover.AntennaKeepoutWidth = antenna_w

    doc.recompute(); _fit_view(doc); os.makedirs(os.path.dirname(output), exist_ok=True); doc.saveAs(output)
    return {
        "ok": True,
        "action": "create_snapfit_case",
        "document": doc.Name,
        "output_path": output,
        "parts": ["BottomCase", "TopCover"],
        "board": {"width": board_w, "length": board_l, "clearance": board_clear},
        "case": {"outer_width": outer_w, "outer_length": outer_l, "body_height": body_h, "cover_thickness": cover_t},
        "features": {"round_snap_count": 4, "solid_button_count": 2, "usb_c_opening": {"width": usb_w, "height": usb_h}, "antenna_keepout": {"length": antenna_l, "width": antenna_w}}
    }


def execute_command(command):
    action = command.get("action")
    if action == "ping":
        return {"ok": True, "message": "FreeCAD agent is alive"}
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
        return {"ok": True, "action": action, "document": doc.Name, "objects": [{"name": o.Name, "label": o.Label, "type": o.TypeId} for o in doc.Objects]}
    if action == "inspect_features":
        doc = App.ActiveDocument
        if doc is None: raise RuntimeError("No active FreeCAD document")
        names = command.get("objects", [])
        features = []
        for name in names:
            obj = doc.getObject(name)
            features.append({"name": name, "type": obj.TypeId, "label": obj.Label} if obj else {"name": name, "error": "Object not found"})
        return {"ok": True, "action": action, "document": doc.Name, "features": features}
    if action == "inspect_geometry": return _inspect_geometry(command)
    if action == "create_case_rails": return _create_case_rails(command)
    if action == "create_slider_cover": return _create_slider_cover(command)
    if action == "create_smoke_test_box": return _create_smoke_test_box(command)
    if action == "create_snapfit_case": return _create_snapfit_case(command)
    return {"ok": False, "error": f"Unsupported action: {action}"}


def _poll_server():
    global _server_socket
    if _server_socket is None: return
    while True:
        try: connection, _ = _server_socket.accept()
        except BlockingIOError: break
        except OSError as exc:
            print(f"[freecad-agent] accept error: {exc}"); break
        try:
            connection.settimeout(0.5)
            data = connection.recv(65536)
            if not data: continue
            result = execute_command(json.loads(data.decode("utf-8")))
            connection.sendall(json.dumps(result).encode("utf-8"))
        except Exception as exc:
            try: connection.sendall(json.dumps({"ok": False, "error": str(exc)}).encode("utf-8"))
            except Exception: pass
        finally: connection.close()


def start_server():
    global _server_socket, _server_timer
    if _server_socket is not None:
        print(f"[freecad-agent] already listening on {HOST}:{PORT}"); return
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT)); server.listen(5); server.setblocking(False)
    _server_socket = server
    _server_timer = QtCore.QTimer(); _server_timer.timeout.connect(_poll_server); _server_timer.start(50)
    print(f"[freecad-agent] listening on {HOST}:{PORT}")


def stop_server():
    global _server_socket, _server_timer
    if _server_timer is not None:
        _server_timer.stop(); _server_timer.deleteLater(); _server_timer = None
    if _server_socket is not None:
        _server_socket.close(); _server_socket = None
    print("[freecad-agent] stopped")


if __name__ == "__main__":
    print("Run start_server() from the FreeCAD Python console.")
