import importlib.util
import os

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_BASE_PATH = os.path.join(_BASE_DIR, "freecad_agent_listener.py")
_BOX_PATH = os.path.join(_BASE_DIR, "box_enclosure.py")

# Load the base listener from this exact directory.
_BASE_SPEC = importlib.util.spec_from_file_location(
    "freecad_agent_listener_base", _BASE_PATH
)
base_listener = importlib.util.module_from_spec(_BASE_SPEC)
_BASE_SPEC.loader.exec_module(base_listener)

# Load box_enclosure.py explicitly from the same repository directory.
# Do not use a plain `from box_enclosure import ...` here because FreeCAD
# may resolve another module with the same name or keep an older module in
# sys.modules after a listener reload.
_BOX_SPEC = importlib.util.spec_from_file_location(
    "freecad_agent_box_enclosure_latest", _BOX_PATH
)
box_enclosure = importlib.util.module_from_spec(_BOX_SPEC)
_BOX_SPEC.loader.exec_module(box_enclosure)

_original_execute_command = base_listener.execute_command


def execute_command(command):
    if command.get("action") == "create_box_enclosure":
        return box_enclosure.create_box_enclosure(command)
    return _original_execute_command(command)


base_listener.execute_command = execute_command

HOST = base_listener.HOST
PORT = base_listener.PORT
start_server = base_listener.start_server
stop_server = base_listener.stop_server


if __name__ == "__main__":
    start_server()
