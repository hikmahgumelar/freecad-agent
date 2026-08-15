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


def _value_to_json(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (list, tuple)):
        return [_value_to_json(v) for v in value]
    try:
        return str(value)
    except Exception:
        return repr(value)


def _fit_view(doc):
    try:
        gui_doc = Gui.getDocument(doc.Name)
        if gui_doc is not None:
            gui_doc.activeView().viewAxonometric()
            gui_doc.activeView().fitAll()
    except Exception as exc:
        print(f"[freecad-agent] GUI update skipped: {exc}")


def _get_tip(doc, body_name="Body"):
    body = doc.getObject(body_name)
    if body is None:
        raise RuntimeError(f"Body '{body_name}' not found")
    tip = getattr(body, "Tip", None)
    if tip is None or not hasattr(tip, "Shape") or tip.Shape.isNull():
        raise RuntimeError(f"Body '{body_name}' Tip has no valid Shape")
    return body, tip


def _inspect_feature(obj):
    result = {"name": obj.Name, "label": obj.Label, "type": obj.TypeId, "properties": {}}
    for prop in obj.PropertiesList:
        try:
            result["properties"][prop] = _value_to_json(getattr(obj, prop))
        except Exception as exc:
            result["properties"][prop] = f"<unavailable: {exc}>"
    return result


def _inspect_geometry(command):
    doc = App.ActiveDocument
    if doc is None:
        raise RuntimeError("No active FreeCAD document")
    body, tip = _get_tip(doc, command.get("body", "Body"))
    shape = tip.Shape
    bb = shape.BoundBox
    top_z = bb.ZMax
    tol = float(command.get("tolerance", 0.01))
    top_faces = []
    for index, face in enumerate(shape.Faces, 1):
        fbb = face.BoundBox
        if abs(fbb.ZMin - top_z) <= tol and abs(fbb.ZMax - top_z) <= tol:
            top_faces.append({"index": index, "area": face.Area, "center": {"x": face.CenterOfMass.x, "y": face.CenterOfMass.y, "z": face.CenterOfMass.z}, "bounds": {"xmin": fbb.XMin, "xmax": fbb.XMax, "ymin": fbb.YMin, "ymax": fbb.YMax, "zmin": fbb.ZMin, "zmax": fbb.ZMax}, "wires": len(face.Wires)})
    return {"ok": True, "action": "inspect_geometry", "document": doc.Name, "body": body.Name, "tip": tip.Name, "tip_label": tip.Label, "tip_type": tip.TypeId, "bounding_box": {"xmin": bb.XMin, "xmax": bb.XMax, "ymin": bb.YMin, "ymax": bb.YMax, "zmin": bb.ZMin, "zmax": bb.ZMax, "x_length": bb.XLength, "y_length": bb.YLength, "z_length": bb.ZLength}, "solids": len(shape.Solids), "shells": len(shape.Shells), "faces": len(shape.Faces), "edges": len(shape.Edges), "top_faces": top_faces}


def _inner_bounds(shape, top_z, tol=0.01):
    candidates = []
    for face in shape.Faces:
        fbb = face.BoundBox
        if abs(fbb.ZMin - top_z) <= tol and abs(fbb.ZMax - top_z) <= tol and len(face.Wires) >= 2:
            candidates.append(face)
    if not candidates:
        raise RuntimeError("No horizontal top face with inner opening found on Body.Tip")
    top_face = max(candidates, key=lambda f: f.Area)
    wires = []
    for wire in top_face.Wires:
        wbb = wire.BoundBox
        wires.append((wbb.XLength * wbb.YLength, wbb))
    wires.sort(key=lambda item: item[0])
    inner = wires[0][1]
    return inner


def _floor_z(shape, top_z, tol=0.01):
    horizontal = []
    for face in shape.Faces:
        fbb = face.BoundBox
        if abs(fbb.ZMin - fbb.ZMax) <= tol and fbb.ZMax < top_z - tol:
            horizontal.append(face)
    if not horizontal:
        raise RuntimeError("Could not identify the case floor")
    floor_face = max(horizontal, key=lambda f: f.Area)
    return floor_face.BoundBox.ZMin


def _create_case_rails(command):
    doc = App.ActiveDocument
    if doc is None:
        raise RuntimeError("No active FreeCAD document")
    body, tip = _get_tip(doc, command.get("body", "Body"))
    shape = tip.Shape
    bb = shape.BoundBox
    top_z = bb.ZMax
    rail_width = float(command.get("rail_width", 1.6))
    rail_height = float(command.get("rail_height", 1.8))
    inset = float(command.get("inset", 2.0))
    clearance = float(command.get("clearance", 0.2))
    output_path = os.path.abspath(command.get("output_path", "/home/hikmah/projectx/freecad-agent/cad/output/case-v1-with-rails-v2.FCStd"))
    if min(rail_width, rail_height, inset) <= 0:
        raise RuntimeError("Rail parameters must be positive")

    inner = _inner_bounds(shape, top_z)
    floor_z = _floor_z(shape, top_z)
    x0 = inner.XMin + inset
    x1 = inner.XMax - inset
    y0 = inner.YMin + inset
    y1 = inner.YMax - inset
    length = x1 - x0
    if length <= 0 or y1 - y0 <= 2 * rail_width:
        raise RuntimeError("Calculated rail geometry is invalid")

    rail_left = Part.makeBox(length, rail_width, rail_height, App.Vector(x0, y0, floor_z))
    rail_right = Part.makeBox(length, rail_width, rail_height, App.Vector(x0, y1 - rail_width, floor_z))

    for name in ("SliderCaseRailLeft", "SliderCaseRailRight"):
        old = doc.getObject(name)
        if old is not None:
            doc.removeObject(name)
    left = doc.addObject("Part::Feature", "SliderCaseRailLeft")
    left.Label = "Slider case rail left (floor mounted)"
    left.Shape = rail_left
    right = doc.addObject("Part::Feature", "SliderCaseRailRight")
    right.Label = "Slider case rail right (floor mounted)"
    right.Shape = rail_right

    doc.recompute()
    _fit_view(doc)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    doc.saveAs(output_path)
    return {"ok": True, "action": "create_case_rails", "document": doc.Name, "source_body": body.Name, "source_tip": tip.Name, "output_path": output_path, "case_dimensions": {"x": bb.XLength, "y": bb.YLength, "z": bb.ZLength}, "inner_bounds": {"xmin": inner.XMin, "xmax": inner.XMax, "ymin": inner.YMin, "ymax": inner.YMax, "floor_z": floor_z}, "rail_width": rail_width, "rail_height": rail_height, "inset": inset, "clearance": clearance, "objects": ["SliderCaseRailLeft", "SliderCaseRailRight"]}


def _create_slider_cover(command):
    doc = App.ActiveDocument
    if doc is None:
        raise RuntimeError("No active FreeCAD document")
    body_name = command.get("body", "Body")
    body, tip = _get_tip(doc, body_name)
    shape = tip.Shape
    bb = shape.BoundBox
    top_z = bb.ZMax
    inner = _inner_bounds(shape, top_z)
    floor_z = _floor_z(shape, top_z)

    rail_width = float(command.get("rail_width", 1.6))
    rail_height = float(command.get("rail_height", 1.8))
    rail_inset = float(command.get("rail_inset", 2.0))
    side_clearance = float(command.get("clearance", 0.2))
    top_clearance = float(command.get("top_clearance", 0.2))
    thickness = float(command.get("thickness", 1.6))
    antenna_offset = float(command.get("antenna_offset", 10.0))
    end_clearance = float(command.get("end_clearance", 4.0))
    skirt_width = float(command.get("skirt_width", 1.6))
    output_path = os.path.abspath(command.get("output_path", "/home/hikmah/projectx/freecad-agent/cad/output/case-v1-with-slider-v1.FCStd"))

    if min(rail_width, rail_height, rail_inset, side_clearance, top_clearance, thickness, antenna_offset, end_clearance, skirt_width) <= 0:
        raise RuntimeError("Slider parameters must be positive")

    x0 = inner.XMin + rail_inset
    x1 = inner.XMax - rail_inset
    y0 = inner.YMin + rail_inset
    y1 = inner.YMax - rail_inset
    if x1 <= x0 or y1 <= y0:
        raise RuntimeError("Invalid inner case bounds")

    # The manual SMA opening is retained on the side of the case. The slider
    # deliberately starts 10 mm away from that end instead of moving the hole.
    slider_x0 = x0 + antenna_offset
    slider_x1 = x1 - end_clearance
    if slider_x1 - slider_x0 <= 10:
        raise RuntimeError("Slider travel is too short for the requested antenna/end clearances")

    rail_y_left = y0
    rail_y_right = y1 - rail_width
    rail_left_shape = Part.makeBox(x1 - x0, rail_width, rail_height, App.Vector(x0, rail_y_left, floor_z))
    rail_right_shape = Part.makeBox(x1 - x0, rail_width, rail_height, App.Vector(x0, rail_y_right, floor_z))

    # Correct any existing rails in-place so they are seated directly on the case floor.
    for name, rail_shape, label in (
        ("SliderCaseRailLeft", rail_left_shape, "Slider case rail left (floor mounted)"),
        ("SliderCaseRailRight", rail_right_shape, "Slider case rail right (floor mounted)"),
    ):
        obj = doc.getObject(name)
        if obj is None:
            obj = doc.addObject("Part::Feature", name)
        obj.Label = label
        obj.Shape = rail_shape

    plate_y0 = rail_y_left + rail_width + side_clearance
    plate_y1 = rail_y_right - side_clearance
    if plate_y1 <= plate_y0:
        raise RuntimeError("Rails leave no usable slider width")
    plate_z = floor_z + rail_height + top_clearance
    plate = Part.makeBox(slider_x1 - slider_x0, plate_y1 - plate_y0, thickness, App.Vector(slider_x0, plate_y0, plate_z))

    skirt_height = max(0.8, plate_z - floor_z - 0.2)
    skirt_z = floor_z + 0.2
    left_skirt_y = rail_y_left - skirt_width - side_clearance
    right_skirt_y = rail_y_right + rail_width + side_clearance
    left_skirt = Part.makeBox(slider_x1 - slider_x0, skirt_width, skirt_height, App.Vector(slider_x0, left_skirt_y, skirt_z))
    right_skirt = Part.makeBox(slider_x1 - slider_x0, skirt_width, skirt_height, App.Vector(slider_x0, right_skirt_y, skirt_z))

    slider_shape = plate.fuse(left_skirt).fuse(right_skirt).removeSplitter()
    old = doc.getObject("SliderCover")
    if old is not None:
        doc.removeObject("SliderCover")
    slider = doc.addObject("Part::Feature", "SliderCover")
    slider.Label = "Slider cover - manual case compatible"
    slider.Shape = slider_shape

    # Keep the original Body untouched: the antenna and USB-C openings remain
    # exactly as modeled manually. The cover is a separate moving component.
    slider.addProperty("App::PropertyLength", "AntennaOffset", "Slider")
    slider.AntennaOffset = antenna_offset
    slider.addProperty("App::PropertyLength", "SideClearance", "Slider")
    slider.SideClearance = side_clearance
    slider.addProperty("App::PropertyLength", "TopClearance", "Slider")
    slider.TopClearance = top_clearance
    slider.addProperty("App::PropertyString", "DesignNote", "Slider")
    slider.DesignNote = "Manual SMA side opening retained; slider starts 10 mm away from antenna side."

    doc.recompute()
    _fit_view(doc)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    doc.saveAs(output_path)
    return {"ok": True, "action": "create_slider_cover", "document": doc.Name, "source_body": body.Name, "source_tip": tip.Name, "output_path": output_path, "case_dimensions": {"x": bb.XLength, "y": bb.YLength, "z": bb.ZLength}, "inner_bounds": {"xmin": inner.XMin, "xmax": inner.XMax, "ymin": inner.YMin, "ymax": inner.YMax, "floor_z": floor_z}, "slider": {"xmin": slider_x0, "xmax": slider_x1, "ymin": plate_y0, "ymax": plate_y1, "z": plate_z, "thickness": thickness, "antenna_offset": antenna_offset, "side_clearance": side_clearance, "top_clearance": top_clearance}, "rails": {"width": rail_width, "height": rail_height, "inset": rail_inset, "floor_mounted": True}, "objects": ["SliderCaseRailLeft", "SliderCaseRailRight", "SliderCover"]}


def execute_command(command):
    action = command.get("action")
    if action == "ping":
        return {"ok": True, "message": "FreeCAD agent is alive"}
    if action == "create_sphere":
        doc = App.ActiveDocument or App.newDocument("AgentTest")
        sphere = doc.addObject("Part::Sphere", "AgentSphere")
        sphere.Radius = float(command.get("radius", 10))
        doc.recompute()
        _fit_view(doc)
        return {"ok": True, "action": action, "object": sphere.Name, "radius": sphere.Radius, "document": doc.Name}
    if action == "open_model":
        path = os.path.abspath(command.get("path", ""))
        if not path or not os.path.isfile(path):
            raise RuntimeError(f"CAD file not found: {path}")
        doc = App.openDocument(path)
        _fit_view(doc)
        return {"ok": True, "action": action, "path": path, "document": doc.Name, "label": doc.Label}
    if action == "inspect_model":
        doc = App.ActiveDocument
        if doc is None:
            raise RuntimeError("No active FreeCAD document")
        return {"ok": True, "action": action, "document": doc.Name, "label": doc.Label, "objects": [{"name": o.Name, "label": o.Label, "type": o.TypeId} for o in doc.Objects]}
    if action == "inspect_features":
        doc = App.ActiveDocument
        if doc is None:
            raise RuntimeError("No active FreeCAD document")
        names = command.get("objects", ["Sketch", "Sketch001", "Pad", "Sketch002"])
        features = []
        for name in names:
            obj = doc.getObject(name)
            features.append(_inspect_feature(obj) if obj else {"name": name, "error": "Object not found"})
        return {"ok": True, "action": action, "document": doc.Name, "features": features}
    if action == "inspect_geometry":
        return _inspect_geometry(command)
    if action == "create_case_rails":
        return _create_case_rails(command)
    if action == "create_slider_cover":
        return _create_slider_cover(command)
    return {"ok": False, "error": f"Unsupported action: {action}"}


def _poll_server():
    global _server_socket
    if _server_socket is None:
        return
    while True:
        try:
            connection, address = _server_socket.accept()
        except BlockingIOError:
            break
        except OSError as exc:
            print(f"[freecad-agent] accept error: {exc}")
            break
        try:
            connection.settimeout(0.5)
            data = connection.recv(65536)
            if not data:
                continue
            command = json.loads(data.decode("utf-8"))
            print("[freecad-agent] command:", command)
            result = execute_command(command)
            connection.sendall(json.dumps(result).encode("utf-8"))
        except Exception as exc:
            try:
                connection.sendall(json.dumps({"ok": False, "error": str(exc)}).encode("utf-8"))
            except Exception:
                pass
        finally:
            connection.close()


def start_server():
    global _server_socket, _server_timer
    if _server_socket is not None:
        print(f"[freecad-agent] already listening on {HOST}:{PORT}")
        return
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(5)
    server.setblocking(False)
    _server_socket = server
    _server_timer = QtCore.QTimer()
    _server_timer.timeout.connect(_poll_server)
    _server_timer.start(50)
    print(f"[freecad-agent] listening on {HOST}:{PORT}")


def stop_server():
    global _server_socket, _server_timer
    if _server_timer is not None:
        _server_timer.stop()
        _server_timer.deleteLater()
        _server_timer = None
    if _server_socket is not None:
        _server_socket.close()
        _server_socket = None
    print("[freecad-agent] stopped")


if __name__ == "__main__":
    print("Run start_server() from the FreeCAD Python console.")
