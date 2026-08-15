# FreeCAD Agent

This repository is used to coordinate FreeCAD agent jobs between GitHub, the local watchdog, and FreeCAD.

## Start the FreeCAD listener

Open FreeCAD and make sure the Python Console is enabled. The listener must run inside FreeCAD because it uses the FreeCAD Python API.

Load the listener from the repository with:

```python
import importlib.util

try:
    listener.stop_server()
except Exception:
    pass

path = "/home/hikmah/projectx/freecad-agent/freecad/freecad_agent_listener.py"

spec = importlib.util.spec_from_file_location(
    "freecad_agent_listener_latest",
    path
)

listener = importlib.util.module_from_spec(spec)
spec.loader.exec_module(listener)

listener.start_server()
```

A successful startup prints:

```text
[freecad-agent] stopped
[freecad-agent] listening on 127.0.0.1:8765
```

Keep FreeCAD running while the watchdog processes jobs.

## FreeCAD source model

For CAD jobs that modify an existing model, open the source `.FCStd` file from `cad/source/` in FreeCAD and make sure it is the active document before starting the watchdog.

Example:

```text
/home/hikmah/projectx/freecad-agent/cad/source/case-V1.FCStd
```

Do not open a previously generated output file when the job is intended to modify the source model.

## Start the watchdog

From a separate terminal:

```bash
cd /home/hikmah/projectx/freecad-agent
./freecad-agent-watchdog
```

The watchdog connects to the FreeCAD listener at `127.0.0.1:8765` and polls GitHub for pending CAD jobs.

## Typical workflow

```text
GitHub CAD Job
      |
      v
freecad-agent-watchdog
      |
      v
FreeCAD listener :8765
      |
      v
Active FreeCAD source document
      |
      v
Generated / modified CAD output
```

For existing CAD models, preserve the source model and its feature history whenever possible. Generated geometry should be added to the active source document rather than flattening the source into a new reference-only model unless the job explicitly requires that behavior.
<img width="1914" height="1051" alt="image" src="https://github.com/user-attachments/assets/2b3b2da6-701d-4007-a8f3-6c471347a659" />
