import importlib
import importlib.util
import os
import sys

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_BASE_PATH = os.path.join(_BASE_DIR, "freecad_agent_listener.py")

_BASE_SPEC = importlib.util.spec_from_file_location(
    "freecad_agent_listener_base_large", _BASE_PATH
)
base_listener = importlib.util.module_from_spec(_BASE_SPEC)
_BASE_SPEC.loader.exec_module(base_listener)

if _BASE_DIR not in sys.path:
    sys.path.insert(0, _BASE_DIR)


def _create_large_enclosure(command):
    module = importlib.import_module("large_enclosure")
    module = importlib.reload(module)
    return module.create_large_enclosure(command)


def _create_character_figurine(command):
    module = importlib.import_module("character_figurine")
    module = importlib.reload(module)
    return module.create_character_figurine(command)


_original_execute_command = base_listener.execute_command


def execute_command(command):
    action = command.get("action")
    if action == "create_large_enclosure":
        return _create_large_enclosure(command)
    if action == "create_character_figurine":
        return _create_character_figurine(command)
    return _original_execute_command(command)


base_listener.execute_command = execute_command

HOST = base_listener.HOST
PORT = base_listener.PORT
start_server = base_listener.start_server
stop_server = base_listener.stop_server

if __name__ == "__main__":
    start_server()
