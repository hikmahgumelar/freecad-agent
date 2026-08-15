import json
import socket


class FreeCADExecutor:
    def __init__(
        self,
        host: str,
        port: int,
        timeout: int = 15,
    ):
        self.host = host
        self.port = port
        self.timeout = timeout

    def execute(self, job):
        action = job.get("action")

        if action == "ping":
            return self._send({
                "action": "ping",
            })

        if action == "create_sphere":
            parameters = job.get("parameters", {})
            radius = parameters.get("radius", 10)
            return self._send({
                "action": "create_sphere",
                "radius": radius,
            })

        if action == "open_model":
            parameters = job.get("parameters", {})
            path = parameters.get("path")
            if not path:
                raise RuntimeError("open_model requires parameters.path")
            return self._send({
                "action": "open_model",
                "path": path,
            })

        if action == "inspect_model":
            return self._send({
                "action": "inspect_model",
            })

        if action == "inspect_features":
            parameters = job.get("parameters", {})
            objects = parameters.get(
                "objects",
                ["Sketch", "Sketch001", "Pad", "Sketch002"],
            )
            return self._send({
                "action": "inspect_features",
                "objects": objects,
            })

        raise RuntimeError(f"Unsupported action: {action}")

    def _send(self, command):
        payload = json.dumps(command).encode("utf-8")

        with socket.create_connection(
            (self.host, self.port),
            timeout=self.timeout,
        ) as sock:
            sock.sendall(payload)
            response = sock.recv(65536)

        if not response:
            raise RuntimeError("FreeCAD returned empty response")

        result = json.loads(response.decode("utf-8"))

        if not result.get("ok"):
            raise RuntimeError(
                result.get("error", "Unknown FreeCAD error")
            )

        return result
