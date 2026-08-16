"""FreeCAD GUI startup hook for freecad-agent.

This file is loaded automatically when the repository's ``freecad``
directory is installed/linked as a FreeCAD user Mod module.
"""

import importlib.util
import os


_listener_module = None


def _start_freecad_agent_listener():
    global _listener_module

    listener_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "freecad_agent_listener.py")

    if not os.path.isfile(listener_path):
        print(f"[freecad-agent] listener not found: {listener_path}")
        return

    try:
        spec = importlib.util.spec_from_file_location(
            "freecad_agent_listener_startup",
            listener_path,
        )
        if spec is None or spec.loader is None:
            raise RuntimeError("Unable to create listener import specification")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Idempotent startup: a repeated FreeCAD module initialization should
        # not create multiple listener sockets.
        try:
            module.stop_server()
        except Exception:
            pass

        module.start_server()
        _listener_module = module
        print("[freecad-agent] startup listener ready on 127.0.0.1:8765")
    except Exception as exc:
        print(f"[freecad-agent] startup listener failed: {exc}")


_start_freecad_agent_listener()
