import json
import socket


class FreeCADExecutor:
    def __init__(self, host: str, port: int, timeout: int = 15):
        self.host = host
        self.port = port
        self.timeout = timeout

    def execute(self, job):
        action = job.get("action")
        if action == "ping":
            return self._send({"action": "ping"})
        if action == "create_sphere":
            p = job.get("parameters", {})
            return self._send({"action": "create_sphere", "radius": p.get("radius", 10)})
        if action == "open_model":
            p = job.get("parameters", {})
            path = p.get("path")
            if not path:
                raise RuntimeError("open_model requires parameters.path")
            return self._send({"action": "open_model", "path": path})
        if action == "inspect_model":
            return self._send({"action": "inspect_model"})
        if action == "inspect_features":
            p = job.get("parameters", {})
            return self._send({"action": "inspect_features", "objects": p.get("objects", ["Sketch", "Sketch001", "Pad", "Sketch002"])})
        if action == "inspect_geometry":
            p = job.get("parameters", {})
            return self._send({"action": "inspect_geometry", "body": p.get("body", "Body"), "tolerance": p.get("tolerance", 0.01)})
        if action == "create_case_rails":
            p = job.get("parameters", {})
            return self._send({"action": "create_case_rails", "body": p.get("body", "Body"), "rail_width": p.get("rail_width", 1.6), "rail_height": p.get("rail_height", 1.8), "inset": p.get("inset", 2.0), "clearance": p.get("clearance", 0.2), "output_path": p.get("output_path", "/home/hikmah/projectx/freecad-agent/cad/output/case-v1-with-rails-v2.FCStd")})
        if action == "create_slider_cover":
            p = job.get("parameters", {})
            return self._send({"action": "create_slider_cover", "body": p.get("body", "Body"), "rail_width": p.get("rail_width", 1.6), "rail_height": p.get("rail_height", 1.8), "rail_inset": p.get("rail_inset", 2.0), "clearance": p.get("clearance", 0.2), "top_clearance": p.get("top_clearance", 0.2), "thickness": p.get("thickness", 1.6), "antenna_offset": p.get("antenna_offset", 10.0), "end_clearance": p.get("end_clearance", 4.0), "skirt_width": p.get("skirt_width", 1.6), "output_path": p.get("output_path", "/home/hikmah/projectx/freecad-agent/cad/output/case-v1-with-slider-v1.FCStd")})
        if action == "create_box_enclosure":
            p = job.get("parameters", {})
            return self._send({"action": "create_box_enclosure", "length": p.get("length", 90.0), "width": p.get("width", 60.0), "height": p.get("height", 11.0), "wall": p.get("wall", 1.5), "cover_thickness": p.get("cover_thickness", 1.5), "screw_diameter": p.get("screw_diameter", 3.0), "screw_margin": p.get("screw_margin", 5.0), "antenna_diameter": p.get("antenna_diameter", 7.0), "antenna_left_offset": p.get("antenna_left_offset", 10.0), "usb_width": p.get("usb_width", 12.0), "usb_height": p.get("usb_height", 5.0), "post_outer_diameter": p.get("post_outer_diameter", 6.0), "output_path": p.get("output_path", "/app/freecad-agent/cad/output/box-90x60x11.FCStd")})
        if action == "create_large_enclosure":
            p = job.get("parameters", {})
            return self._send({"action": "create_large_enclosure", "length": p.get("length", 200.0), "width": p.get("width", 100.0), "height": p.get("height", 250.0), "wall": p.get("wall", 2.0), "bottom_thickness": p.get("bottom_thickness", 2.0), "lid_length": p.get("lid_length", 202.0), "lid_width": p.get("lid_width", 102.0), "lid_height": p.get("lid_height", 60.0), "lid_wall": p.get("lid_wall", 2.0), "plate_center_z": p.get("plate_center_z", 125.0), "plate_thickness": p.get("plate_thickness", 2.0), "hole_diameter": p.get("hole_diameter", 50.0), "hole_columns": p.get("hole_columns", 3), "hole_rows": p.get("hole_rows", 2), "output_path": p.get("output_path", "/home/hikmah/projectx/freecad-agent/cad/output/enclosure-200x100x250.FCStd")})
        if action == "create_medicine_box":
            p = job.get("parameters", {})
            command = dict(p)
            command["action"] = "create_large_enclosure"
            command["design"] = "medicine_box"
            return self._send(command)
        if action == "create_medicine_cover":
            p = job.get("parameters", {})
            return self._send({"action": "create_medicine_cover", "output_path": p.get("output_path", "cad/output/medicine-box-cover-v1.FCStd")})
        if action == "create_medicine_plate":
            p = job.get("parameters", {})
            return self._send({"action": "create_medicine_plate", "output_path": p.get("output_path", "cad/output/medicine-box-plate-6holes-v1.FCStd")})
        if action == "create_medicine_body":
            p = job.get("parameters", {})
            return self._send({"action": "create_medicine_body", "output_path": p.get("output_path", "cad/output/medicine-box-body-v1.FCStd")})
        if action == "create_character_figurine":
            p = job.get("parameters", {})
            return self._send({"action": "create_character_figurine", "height": p.get("height", 120.0), "base_diameter": p.get("base_diameter", 46.0), "base_thickness": p.get("base_thickness", 3.0), "output_path": p.get("output_path", "/app/freecad-agent/cad/output/character-figurine-120mm.FCStd"), "stl_path": p.get("stl_path", "/app/freecad-agent/cad/output/character-figurine-120mm.stl")})
        raise RuntimeError(f"Unsupported action: {action}")

    def _send(self, command):
        payload = json.dumps(command).encode("utf-8")
        with socket.create_connection((self.host, self.port), timeout=self.timeout) as sock:
            sock.sendall(payload)
            response = sock.recv(65536)
        if not response:
            raise RuntimeError("FreeCAD returned empty response")
        result = json.loads(response.decode("utf-8"))
        if not result.get("ok"):
            raise RuntimeError(result.get("error", "Unknown FreeCAD error"))
        return result
