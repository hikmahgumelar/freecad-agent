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
            return self._send({
                "action": "create_case_rails",
                "body": p.get("body", "Body"),
                "rail_width": p.get("rail_width", 1.6),
                "rail_height": p.get("rail_height", 1.8),
                "inset": p.get("inset", 2.0),
                "clearance": p.get("clearance", 0.2),
                "output_path": p.get("output_path", "/home/hikmah/projectx/freecad-agent/cad/output/case-v1-with-rails-v2.FCStd"),
            })
        if action == "create_slider_cover":
            p = job.get("parameters", {})
            return self._send({
                "action": "create_slider_cover",
                "body": p.get("body", "Body"),
                "rail_width": p.get("rail_width", 1.6),
                "rail_height": p.get("rail_height", 1.8),
                "rail_inset": p.get("rail_inset", 2.0),
                "clearance": p.get("clearance", 0.2),
                "top_clearance": p.get("top_clearance", 0.2),
                "thickness": p.get("thickness", 1.6),
                "antenna_offset": p.get("antenna_offset", 10.0),
                "end_clearance": p.get("end_clearance", 4.0),
                "skirt_width": p.get("skirt_width", 1.6),
                "output_path": p.get("output_path", "/home/hikmah/projectx/freecad-agent/cad/output/case-v1-with-slider-v1.FCStd"),
            })
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
