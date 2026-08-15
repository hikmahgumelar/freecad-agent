import json
import socket

import FreeCAD as App
import Part


HOST = "127.0.0.1"
PORT = 8765


def execute_command(command):
    action = command.get("action")

    if action == "ping":
        return {
            "ok": True,
            "message": "FreeCAD agent is alive",
        }

    if action == "create_sphere":
        radius = float(
            command.get("radius", 10)
        )

        doc = App.ActiveDocument

        if doc is None:
            doc = App.newDocument(
                "AgentTest"
            )

        sphere = doc.addObject(
            "Part::Sphere",
            "AgentSphere",
        )

        sphere.Label = (
            "Created by freecad-agent"
        )

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
        "error": (
            f"Unsupported action: {action}"
        ),
    }


def start_server():
    server = socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM,
    )

    server.setsockopt(
        socket.SOL_SOCKET,
        socket.SO_REUSEADDR,
        1,
    )

    server.bind(
        (HOST, PORT)
    )

    server.listen(5)

    print(
        "[freecad-agent] listening on "
        f"{HOST}:{PORT}"
    )

    while True:
        connection, address = (
            server.accept()
        )

        try:
            data = connection.recv(
                65536
            )

            if not data:
                continue

            command = json.loads(
                data.decode("utf-8")
            )

            print(
                "[freecad-agent] command:",
                command,
            )

            result = execute_command(
                command
            )

            response = json.dumps(
                result
            ).encode("utf-8")

            connection.sendall(
                response
            )

        except Exception as exc:
            response = {
                "ok": False,
                "error": str(exc),
            }

            try:
                connection.sendall(
                    json.dumps(
                        response
                    ).encode("utf-8")
                )
            except Exception:
                pass

        finally:
            connection.close()


start_server()
