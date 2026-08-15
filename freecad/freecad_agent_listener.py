import json
import socket

import FreeCAD as App
import Part
from PySide import QtCore


HOST = "127.0.0.1"
PORT = 8765

_server_socket = None
_server_timer = None


def execute_command(command):
    action = command.get("action")

    if action == "ping":
        return {
            "ok": True,
            "message": "FreeCAD agent is alive",
        }

    if action == "create_sphere":
        radius = float(command.get("radius", 10))

        doc = App.ActiveDocument
        if doc is None:
            doc = App.newDocument("AgentTest")

        sphere = doc.addObject("Part::Sphere", "AgentSphere")
        sphere.Label = "Created by freecad-agent"
        sphere.Radius = radius
        doc.recompute()

        return {
            "ok": True,
            "action": "create_sphere",
            "object": sphere.Name,
            "radius": radius,
            "document": doc.Name,
        }

    return {
        "ok": False,
        "error": f"Unsupported action: {action}",
    }


def _poll_server():
    global _server_socket, _server_timer

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
            response = json.dumps(result).encode("utf-8")
            connection.sendall(response)

        except Exception as exc:
            response = {"ok": False, "error": str(exc)}
            try:
                connection.sendall(json.dumps(response).encode("utf-8"))
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
        try:
            _server_socket.close()
        finally:
            _server_socket = None

    print("[freecad-agent] stopped")


if __name__ == "__main__":
    print("Run start_server() from the FreeCAD Python console.")
