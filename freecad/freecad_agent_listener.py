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


def _create_case_rails(command):
    doc = App.ActiveDocument
    if doc is None:
        raise RuntimeError("No active FreeCAD document")
    body, tip = _get_tip(doc, command.get("body", "Body"))
    shape = tip.Shape
    bb = shape.BoundBox
    top_z = bb.ZMax
    rail_width = float(command.get("rail_width", 2.0))
    rail_height = float(command.get("rail_height", 2.0))
    inset = float(command.get("inset", 2.0))
    clearance = float(command.get("clearance", 0.2))
    output_path = os.path.abspath(command.get("output_path", "/home/hikmah/projectx/freecad-agent/cad/output/case-v1-with-rails-v1.FCStd"))
    if min(rail_width, rail_height, inset) <= 0:
        raise RuntimeError("Rail parameters must be positive")

    candidates = []
    for face in shape.Faces:
        fbb = face.BoundBox
        if abs(fbb.ZMin - top_z) <= 0.01 and abs(fbb.ZMax - top_z) <= 0.01:
            candidates.append(face)
    if not candidates:
        raise RuntimeError("No horizontal top face found on Body.Tip")
    top_face = max(candidates, key=lambda f: f.Area)
    if len(top_face.Wires) < 2:
        raise RuntimeError("Top face does not expose an inner opening wire")

    wire_data = []
    for wire in top_face.Wires:
        wbb = wire.BoundBox
        wire_data.append((wbb.XLength * wbb.YLength, wbb))
    wire_data.sort(key=lambda item: item[0])
    inner = wire_data[0][1]

    x0 = inner.XMin + inset
    x1 = inner.XMax - inset
    y1 = inner.YMin + inset
    y2 = inner.YMax - inset - rail_width
    length = x1 - x0
    if length <= 0 or y2 <= y1:
        raise RuntimeError("Calculated rail geometry is invalid")
    rail_z = top_z - rail_height - clearance
    left_shape = Part.makeBox(length, rail_width, rail_height, App.Vector(x0, y1, rail_z))
    right_shape = Part.makeBox(length, rail_width, rail_height, App.Vector(x0, y2, rail_z))

    for name in ("SliderCaseRailLeft", "SliderCaseRailRight"):
        old = doc.getObject(name)
        if old is not None:
            doc.removeObject(name)
    left = doc.addObject("Part::Feature", "SliderCaseRailLeft")
    left.Label = "Slider case rail left"
    left.Shape = left_shape
    right = doc.addObject("Part::Feature", "SliderCaseRailRight")
    right.Label = "Slider case rail right"
    right.Shape = right_shape

    doc.recompute()
    _fit_view(doc)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    doc.saveAs(output_path)
    return {"ok": True, "action": "create_case_rails", "document": doc.Name, "source_body": body.Name, "source_tip": tip.Name, "output_path": output_path, "case_dimensions": {"x": bb.XLength, "y": bb.YLength, "z": bb.ZLength}, "inner_bounds": {"xmin": inner.XMin, "xmax": inner.XMax, "ymin": inner.YMin, "ymax": inner.YMax}, "rail_width": rail_width, "rail_height": rail_height, "inset": inset, "clearance": clearance, "objects": ["SliderCaseRailLeft", "SliderCaseRailRight"]}


def _create_slider_cover(command):
    source_doc = App.ActiveDocument
    if source_doc is None:
        raise RuntimeError("No active FreeCAD document")
    output_path = os.path.abspath(command.get("output_path", "/home/hikmah/projectx/freecad-agent/cad/output/case-v1-slider-v2.FCStd"))
    thickness = float(command.get("thickness", 2.0))
    body_name = command.get("body", "Body")
    _, tip = _get_tip(source_doc, body_name)
    shape = tip.Shape
    bb = shape.BoundBox
    top_z = bb.ZMax
    top_faces = [f for f in shape.Faces if abs(f.BoundBox.ZMin-top_z) <= 0.01 and abs(f.BoundBox.ZMax-top_z) <= 0.01]
    if not top_faces:
        raise RuntimeError("No horizontal top face found on Body.Tip")
    top_face = max(top_faces, key=lambda f: f.Area)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    name = "case_v1_slider_v2"
    old = App.listDocuments().get(name)
    if old is not None:
        App.closeDocument(name)
    doc = App.newDocument(name)
    base = doc.addObject("Part::Feature", "CaseBase")
    base.Label = "Existing case final reference"
    base.Shape = shape.copy()
    base.ViewObject.Visibility = False
    slider = doc.addObject("Part::Feature", "SliderCover")
    slider.Label = f"Slider cover {bb.XLength:.1f}x{bb.YLength:.1f} mm, {thickness:.1f} mm thick"
    slider.Shape = top_face.extrude(App.Vector(0, 0, thickness))
    doc.recompute(); _fit_view(doc); doc.saveAs(output_path)
    return {"ok": True, "action": "create_slider_cover", "output_path": output_path, "document": doc.Name, "source_tip": tip.Name}


def execute_command(command):
    action = command.get("action")
    if action == "ping": return {"ok": True, "message": "FreeCAD agent is alive"}
    if action == "create_sphere":
        doc = App.ActiveDocument or App.newDocument("AgentTest")
        sphere = doc.addObject("Part::Sphere", "AgentSphere"); sphere.Radius = float(command.get("radius", 10)); doc.recompute(); _fit_view(doc)
        return {"ok": True, "action": action, "object": sphere.Name, "radius": sphere.Radius, "document": doc.Name}
    if action == "open_model":
        path = os.path.abspath(command.get("path", ""))
        if not path or not os.path.isfile(path): raise RuntimeError(f"CAD file not found: {path}")
        doc = App.openDocument(path); _fit_view(doc)
        return {"ok": True, "action": action, "path": path, "document": doc.Name, "label": doc.Label}
    if action == "inspect_model":
        doc = App.ActiveDocument
        if doc is None: raise RuntimeError("No active FreeCAD document")
        return {"ok": True, "action": action, "document": doc.Name, "label": doc.Label, "objects": [{"name": o.Name, "label": o.Label, "type": o.TypeId} for o in doc.Objects]}
    if action == "inspect_features":
        doc = App.ActiveDocument
        if doc is None: raise RuntimeError("No active FreeCAD document")
        names = command.get("objects", ["Sketch", "Sketch001", "Pad", "Sketch002"])
        features = []
        for name in names:
            obj = doc.getObject(name)
            features.append(_inspect_feature(obj) if obj else {"name": name, "error": "Object not found"})
        return {"ok": True, "action": action, "document": doc.Name, "features": features}
    if action == "inspect_geometry": return _inspect_geometry(command)
    if action == "create_case_rails": return _create_case_rails(command)
    if action == "create_slider_cover": return _create_slider_cover(command)
    return {"ok": False, "error": f"Unsupported action: {action}"}


def _poll_server():
    global _server_socket
    if _server_socket is None: return
    while True:
        try: connection, address = _server_socket.accept()
        except BlockingIOError: break
        except OSError as exc: print(f"[freecad-agent] accept error: {exc}"); break
        try:
            connection.settimeout(0.5); data = connection.recv(65536)
            if not data: continue
            command = json.loads(data.decode("utf-8")); print("[freecad-agent] command:", command)
            result = execute_command(command); connection.sendall(json.dumps(result).encode("utf-8"))
        except Exception as exc:
            try: connection.sendall(json.dumps({"ok": False, "error": str(exc)}).encode("utf-8"))
            except Exception: pass
        finally: connection.close()


def start_server():
    global _server_socket, _server_timer
    if _server_socket is not None:
        print(f"[freecad-agent] already listening on {HOST}:{PORT}"); return
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM); server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1); server.bind((HOST, PORT)); server.listen(5); server.setblocking(False)
    _server_socket = server; _server_timer = QtCore.QTimer(); _server_timer.timeout.connect(_poll_server); _server_timer.start(50)
    print(f"[freecad-agent] listening on {HOST}:{PORT}")


def stop_server():
    global _server_socket, _server_timer
    if _server_timer is not None: _server_timer.stop(); _server_timer.deleteLater(); _server_timer = None
    if _server_socket is not None: _server_socket.close(); _server_socket = None
    print("[freecad-agent] stopped")


if __name__ == "__main__": print("Run start_server() from the FreeCAD Python console.")
