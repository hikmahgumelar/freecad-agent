"""FreeCAD GUI startup hook for freecad-agent.

FreeCAD executes this file during GUI startup. Keep the startup hook flat and
avoid relying on ``__file__`` or helper globals because FreeCAD's startup
loader does not guarantee normal module semantics.
"""

import importlib.util
import os
import sys

import FreeCAD as App

module_dir = os.path.join(App.getUserAppDataDir(), "Mod", "freecad-agent")

if not os.path.isdir(module_dir):
    for path in sys.path:
        candidate = os.path.join(path, "freecad-agent")
        if os.path.isdir(candidate):
            module_dir = candidate
            break

listener_path = os.path.join(module_dir, "freecad_agent_listener.py")

if not os.path.isfile(listener_path):
    print(f"[freecad-agent] startup listener not found: {listener_path}")
else:
    try:
        spec = importlib.util.spec_from_file_location(
            "freecad_agent_listener_startup",
            listener_path,
        )
        if spec is None or spec.loader is None:
            raise RuntimeError("Unable to create listener import specification")

        listener_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(listener_module)

        # Startup is idempotent. If FreeCAD reloads this module, don't leave
        # an older listener socket behind.
        try:
            listener_module.stop_server()
        except Exception:
            pass

        listener_module.start_server()
        print("[freecad-agent] startup listener ready on 127.0.0.1:8765")
    except Exception as exc:
        print(f"[freecad-agent] startup listener failed: {exc}")
