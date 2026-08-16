"""FreeCAD GUI startup hook for freecad-agent.

FreeCAD executes InitGui.py from a Mod module without guaranteeing the
normal Python ``__file__`` global. Resolve the installed module directory
from FreeCAD's user Mod path instead of relying on ``__file__``.
"""

import importlib.util
import os

import FreeCAD as App


_listener_module = None


def _module_dir():
    user_mod_dir = os.path.join(App.getUserAppDataDir(), "Mod", "freecad-agent")
    if os.path.isdir(user_mod_dir):
        return user_mod_dir

    import sys
    for path in sys.path:
        candidate = os.path.join(path, "freecad-agent")
        if os.path.isdir(candidate):
            return candidate

    return None


def _start_freecad_agent_listener():
    global _listener_module

    module_dir = _module_dir()
    if module_dir is None:
        print("[freecad-agent] startup listener failed: module directory not found")
        return

    listener_path = os.path.join(module_dir, "freecad_agent_listener.py")

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
