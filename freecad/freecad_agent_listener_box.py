import importlib.util
import os

_BASE_PATH = os.path.join(os.path.dirname(__file__), "freecad_agent_listener.py")
_SPEC = importlib.util.spec_from_file_location("freecad_agent_listener_base", _BASE_PATH)
base_listener = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(base_listener)

from box_enclosure import create_box_enclosure

_original_execute_command = base_listener.execute_command


def execute_command(command):
    if command.get("action") == "create_box_enclosure":
        return create_box_enclosure(command)
    return _original_execute_command(command)


base_listener.execute_command = execute_command

HOST = base_listener.HOST
PORT = base_listener.PORT
start_server = base_listener.start_server
stop_server = base_listener.stop_server

if __name__ == "__main__":
    start_server()
