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
        return [_value_to_json(item) for item in value]
    try:
        return str(value)
    except Exception:
        return repr(value)


def _inspect_feature(obj):
    result = {"name": obj.Name, "label": obj.Label, "type": obj.TypeId, "properties": {}}
    for prop_name in obj.PropertiesList:
        try:
            result["properties"][prop_name] = _value_to_json(getattr(obj, prop_name))
        except Exception as exc:
            result["properties"][prop_name] = f"<unavailable: {exc}>"
    if hasattr(obj, "GeometryCount"):
        try:
            result["geometry_count"] = int(obj.GeometryCount)
        except Exception:
            pass
    if hasattr(obj, "ConstraintCount"):
        try:
            result["constraint_count"] = int(obj.ConstraintCount)
        except Exception:
            pass
    return result


def _fit_view(doc):
    try:
        gui_doc = Gui.getDocument(doc.Name)
        if gui_doc is not None:
            gui_doc.activeView().viewAxonometric()
            gui_doc.activeView().fitAll()
    except Exception as exc:
        print(f"[freecad-agent] GUI update skipped: {exc}")


def _get_tip(source_doc, body_name="Body"):
    body = source_doc.getObject(body_name)
    if body is None:
        raise RuntimeError(f"Body '{body_name}' not found")
    tip = getattr(body, "Tip", None)
    if tip is None or not hasattr(tip, "Shape") or tip.Shape.isNull():
        raise RuntimeError(f"Body '{body_name}' Tip has no valid Shape")
    return body, tip


def _inspect_geometry(command):
    doc = App.ActiveDocument
    if doc is None:
        raise RuntimeError("No active FreeCAD document")
    body, tip = _get_tip(doc, command.get("body", "Body"))
    shape = tip.Shape
    bb = shape.BoundBox
    result = {
        "ok": True, "action": "inspect_geometry", "document": doc.Name,
        "body": body.Name, "tip": tip.Name, "tip_label": tip.Label, "tip_type": tip.TypeId,
        "bounding_box": {"xmin": bb.XMin, "xmax": bb.XMax, "ymin": bb.YMin, "ymax": bb.YMax,
                         "zmin": bb.ZMin, "zmax": bb.ZMax, "x_length": bb.XLength,
                         "y_length": bb.YLength, "z_length": bb.ZLength},
        "solids": len(shape.Solids), "shells": len(shape.Shells),
        "faces": len(shape.Faces), "edges": len(shape.Edges), "top_faces": [],
    }
    top_z = bb.ZMax
    tolerance = float(command.get("tolerance", 0.01))
    for index, face in enumerate(shape.Faces, start=1):
        fbb = face.BoundBox
        if abs(fbb.ZMax - top_z) > tolerance or abs(fbb.ZMin - top_z) > tolerance:
            continue
        result["top_faces"].append({
            "index": index, "area": face.Area,
            "center": {"x": face.CenterOfMass.x, "y": face.CenterOfMass.y, "z": face.CenterOfMass.z},
            "bounds": {"xmin": fbb.XMin, "xmax": fbb.XMax, "ymin": fbb.YMin, "ymax": fbb.YMax,
                       "zmin": fbb.ZMin, "zmax": fbb.ZMax},
            "wires": len(face.Wires),
        })
    return result


def _create_slider_cover(command):
    source_doc = App.ActiveDocument
    if source_doc is None:
        raise RuntimeError("No active FreeCAD document")

    output_path = os.path.abspath(command.get(
        "output_path", "/home/hikmah/projectx/freecad-agent/cad/output/case-v1-slider-v2.FCStd"))
    thickness = float(command.get("thickness", 2.0))
    rail_width = float(command.get("rail_width", 2.0))
    rail_height = float(command.get("rail_height", 2.0))
    clearance = float(command.get("clearance", 0.5))
    rail_inset = float(command.get("rail_inset", 2.5))
    body_name = command.get("body", "Body")
    if min(thickness, rail_width, rail_height, clearance, rail_inset) <= 0:
        raise RuntimeError("Slider parameters must be positive")

    source_body, source_tip = _get_tip(source_doc, body_name)
    source_shape = source_tip.Shape
    bb = source_shape.BoundBox
    top_z = bb.ZMax

    # Select the largest horizontal face on the final Body.Tip. Extruding the
    # actual face preserves its inner wires/cutouts instead of filling them.
    top_faces = []
    for face in source_shape.Faces:
        fbb = face.BoundBox
        if abs(fbb.ZMin - top_z) <= 0.01 and abs(fbb.ZMax - top_z) <= 0.01:
            top_faces.append(face)
    if not top_faces:
        raise RuntimeError("No horizontal top face found on Body.Tip")
    top_face = max(top_faces, key=lambda f: f.Area)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    doc_name = "case_v1_slider_v2"
    existing = App.listDocuments().get(doc_name)
    if existing is not None:
        App.closeDocument(doc_name)
    doc = App.newDocument(doc_name)

    base = doc.addObject("Part::Feature", "CaseBase")
    base.Label = "Existing case final reference"
    base.Shape = source_shape.copy()
    base.ViewObject.Visibility = False

    plate = top_face.extrude(App.Vector(0, 0, thickness))
    slider = doc.addObject("Part::Feature", "SliderCover")
    slider.Label = f"Slider cover {bb.XLength:.1f}x{bb.YLength:.1f} mm, {thickness:.1f} mm thick"
    slider.Shape = plate

    # Rails are separate solids so their mating grooves can be tuned on the case.
    rail_x = bb.XMin + rail_inset
    rail_len = max(0.1, bb.XLength - 2.0 * rail_inset)
    rail_y1 = bb.YMin + rail_inset
    rail_y2 = bb.YMax - rail_inset - rail_width
    rail_z = top_z - rail_height
    rail_left = Part.makeBox(rail_len, rail_width, rail_height, App.Vector(rail_x, rail_y1, rail_z))
    rail_right = Part.makeBox(rail_len, rail_width, rail_height, App.Vector(rail_x, rail_y2, rail_z))

    guide1 = doc.addObject("Part::Feature", "GuideRailLeft")
    guide1.Label = "Slider guide rail left"
    guide1.Shape = rail_left
    guide2 = doc.addObject("Part::Feature", "GuideRailRight")
    guide2.Label = "Slider guide rail right"
    guide2.Shape = rail_right

    doc.recompute()
    _fit_view(doc)
    doc.saveAs(output_path)
    return {
        "ok": True, "action": "create_slider_cover", "output_path": output_path, "document": doc.Name,
        "source_document": source_doc.Name, "source_body": source_body.Name, "source_tip": source_tip.Name,
        "case_dimensions": {"x": bb.XLength, "y": bb.YLength, "z": bb.ZLength},
        "cover_thickness": thickness, "top_face_area": top_face.Area,
        "top_face_wires": len(top_face.Wires), "rail_width": rail_width,
        "rail_height": rail_height, "clearance": clearance,
        "objects": ["CaseBase", "SliderCover", "GuideRailLeft", "GuideRailRight"],
    }


def execute_command(command):
    action = command.get("action")
    if action == "ping":
        return {"ok": True, "message": "FreeCAD agent is alive"}
    if action == "create_sphere":
        radius = float(command.get("radius", 10))
        doc = App.ActiveDocument
        if doc is None:
            doc = App.newDocument("AgentTest")
        sphere = doc.addObject("Part::Sphere", "AgentSphere")
        sphere.Label = "Created by freecad-agent"
        sphere.Radius = radius
        doc.recompute(); _fit_view(doc)
        return {"ok": True, "action": "create_sphere", "object": sphere.Name, "radius": radius, "document": doc.Name}
    if action == "open_model":
        path = command.get("path")
        if not path: raise RuntimeError("open_model requires path")
        path = os.path.abspath(path)
        if not os.path.isfile(path): raise RuntimeError(f"CAD file not found: {path}")
        doc = App.openDocument(path); _fit_view(doc)
        return {"ok": True, "action": "open_model", "path": path, "document": doc.Name, "label": doc.Label}
    if action == "inspect_model":
        doc = App.ActiveDocument
        if doc is None: raise RuntimeError("No active FreeCAD document")
        objects = [{"name": obj.Name, "label": obj.Label, "type": obj.TypeId} for obj in doc.Objects]
        return {"ok": True, "action": "inspect_model", "document": doc.Name, "label": doc.Label, "objects": objects}
    if action == "inspect_features":
        doc = App.ActiveDocument
        if doc is None: raise RuntimeError("No active FreeCAD document")
        names = command.get("objects", ["Sketch", "Sketch001", "Pad", "Sketch002"])
        features = []
        for name in names:
            obj = doc.getObject(name)
            if obj is None: features.append({"name": name, "error": "Object not found"}); continue
            features.append(_inspect_feature(obj))
        return {"ok": True, "action": "inspect_features", "document": doc.Name, "features": features}
    if action == "inspect_geometry": return _inspect_geometry(command)
    if action == "create_slider_cover": return _create_slider_cover(command)
    return {"ok": False, "error": f"Unsupported action: {action}"}


def _poll_server():
    global _server_socket
    if _server_socket is None: return
    while True:
        try:
            connection, address = _server_socket.accept()
        except BlockingIOError: break
        except OSError as exc:
            print(f"[freecad-agent] accept error: {exc}"); break
        try:
            connection.settimeout(0.5)
            data = connection.recv(65536)
            if not data: continue
            command = json.loads(data.decode("utf-8"))
            print("[freecad-agent] command:", command)
            result = execute_command(command)
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
