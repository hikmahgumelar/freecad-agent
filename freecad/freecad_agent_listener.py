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
    result = {
        "name": obj.Name,
        "label": obj.Label,
        "type": obj.TypeId,
        "properties": {},
    }

    for prop_name in obj.PropertiesList:
        try:
            result["properties"][prop_name] = _value_to_json(
                getattr(obj, prop_name)
            )
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
    """Best-effort GUI update; CAD operation must not fail if GUI lookup is unavailable."""
    try:
        gui_doc = Gui.getDocument(doc.Name)
        if gui_doc is not None:
            gui_doc.activeView().viewAxonometric()
            gui_doc.activeView().fitAll()
    except Exception as exc:
        print(f"[freecad-agent] GUI update skipped: {exc}")


def _create_slider_cover(command):
    source_doc = App.ActiveDocument
    if source_doc is None:
        raise RuntimeError("No active FreeCAD document")

    output_path = os.path.abspath(command.get(
        "output_path",
        "/home/hikmah/projectx/freecad-agent/cad/output/tutup-case-slider-v1.FCStd",
    ))
    width = float(command.get("width", 84))
    depth = float(command.get("depth", 63))
    thickness = float(command.get("thickness", 2))
    rail_width = float(command.get("rail_width", 2))
    rail_height = float(command.get("rail_height", 2))
    clearance = float(command.get("clearance", 0.5))

    if min(width, depth, thickness, rail_width, rail_height) <= 0:
        raise RuntimeError("Slider dimensions must be positive")
    if rail_width >= depth / 2:
        raise RuntimeError("rail_width is too large for slider depth")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    doc_name = "tutup_case_slider_v1"
    existing = App.getDocument(doc_name)
    if existing is not None:
        App.closeDocument(doc_name)
    doc = App.newDocument(doc_name)

    # Preserve the existing case geometry as a reference/base in the new file.
    source_obj = source_doc.getObject("Pad")
    if source_obj is not None and hasattr(source_obj, "Shape") and not source_obj.Shape.isNull():
        base = doc.addObject("Part::Feature", "CaseBase")
        base.Label = "Existing case base (reference)"
        base.Shape = source_obj.Shape.copy()

    # Slider plate: 84 x 63 x 2 mm, centered on the existing model origin.
    x0 = -width / 2.0
    y0 = -depth / 2.0
    z0 = 3.0
    plate = Part.makeBox(width, depth, thickness, App.Vector(x0, y0, z0))

    # Two underside guide rails. The 0.5 mm clearance keeps the prototype
    # from sitting directly on the reference base.
    rail_z = z0 - rail_height - clearance
    rail_left = Part.makeBox(
        width,
        rail_width,
        rail_height,
        App.Vector(x0, y0 + rail_width, rail_z),
    )
    rail_right = Part.makeBox(
        width,
        rail_width,
        rail_height,
        App.Vector(x0, y0 + depth - 2 * rail_width, rail_z),
    )

    slider = doc.addObject("Part::Feature", "SliderCover")
    slider.Label = "Slider cover 84x63x2 mm"
    slider.Shape = plate.fuse(rail_left).fuse(rail_right)

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
        "ok": True,
        "action": "create_slider_cover",
        "output_path": output_path,
        "document": doc.Name,
        "dimensions": {
            "width": width,
            "depth": depth,
            "thickness": thickness,
            "rail_width": rail_width,
            "rail_height": rail_height,
            "clearance": clearance,
        },
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
        doc.recompute()
        _fit_view(doc)

        return {
            "ok": True,
            "action": "create_sphere",
            "object": sphere.Name,
            "radius": radius,
            "document": doc.Name,
        }

    if action == "open_model":
        path = command.get("path")
        if not path:
            raise RuntimeError("open_model requires path")
        path = os.path.abspath(path)
        if not os.path.isfile(path):
            raise RuntimeError(f"CAD file not found: {path}")

        doc = App.openDocument(path)
        _fit_view(doc)

        return {
            "ok": True,
            "action": "open_model",
            "path": path,
            "document": doc.Name,
            "label": doc.Label,
        }

    if action == "inspect_model":
        doc = App.ActiveDocument
        if doc is None:
            raise RuntimeError("No active FreeCAD document")

        objects = [
            {"name": obj.Name, "label": obj.Label, "type": obj.TypeId}
            for obj in doc.Objects
        ]

        return {
            "ok": True,
            "action": "inspect_model",
            "document": doc.Name,
            "label": doc.Label,
            "objects": objects,
        }

    if action == "inspect_features":
        doc = App.ActiveDocument
        if doc is None:
            raise RuntimeError("No active FreeCAD document")

        names = command.get(
            "objects",
            ["Sketch", "Sketch001", "Pad", "Sketch002"],
        )
        features = []
        for name in names:
            obj = doc.getObject(name)
            if obj is None:
                features.append({
                    "name": name,
                    "error": "Object not found",
                })
                continue
            features.append(_inspect_feature(obj))

        return {
            "ok": True,
            "action": "inspect_features",
            "document": doc.Name,
            "features": features,
        }

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
                connection.sendall(
                    json.dumps({"ok": False, "error": str(exc)}).encode("utf-8")
                )
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
