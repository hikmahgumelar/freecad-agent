# FreeCAD Agent

This repository coordinates FreeCAD agent jobs between GitHub, the local watchdog, and a running FreeCAD instance.

## Architecture

The system has two runtime components:

1. **FreeCAD listener** — runs inside the FreeCAD Python Console. It opens a local TCP endpoint at `127.0.0.1:8765` and executes CAD commands against the currently active FreeCAD document.
2. **freecad-agent-watchdog** — runs outside FreeCAD. It polls the GitHub job queue, takes pending CAD jobs, sends them to the FreeCAD listener, and reports the result back to GitHub.

The watchdog does not replace FreeCAD and does not contain the FreeCAD CAD engine. FreeCAD must be running with the listener active whenever a job needs to be executed.

```text
GitHub CAD Job
      |
      v
freecad-agent-watchdog
      |
      | TCP 127.0.0.1:8765
      v
FreeCAD Python listener
      |
      v
Active FreeCAD document
      |
      v
CAD result / modified model
      |
      v
GitHub job result
```

## Start the FreeCAD listener

The listener must be started **inside FreeCAD** because it uses the FreeCAD Python API.

### 1. Open FreeCAD

Start FreeCAD normally and open the `.FCStd` model that the CAD job is supposed to work on.

For an existing model, the source file should normally be opened from:

```text
cad/source/
```

Make sure the intended document is the **active document** in FreeCAD.

### 2. Open the Python Console

In FreeCAD, use the menu:

```text
View -> Panels -> Python console
```

The Python Console appears at the bottom of the FreeCAD window.

### 3. Start the listener

Paste the following into the FreeCAD Python Console and press Enter:

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

A successful startup should print:

```text
[freecad-agent] stopped
[freecad-agent] listening on 127.0.0.1:8765
```

The listener is now waiting for commands from the watchdog.

**Keep FreeCAD open and keep the listener running.** Do not close FreeCAD or stop the listener while CAD jobs are being processed.

### What does the listener do?

The listener is the bridge between the external agent and FreeCAD. It receives a CAD command from `freecad-agent-watchdog`, executes it through the FreeCAD Python API, and returns the result.

Examples of commands supported by the current listener include:

- `ping` — verifies that the FreeCAD agent endpoint is alive.
- `inspect_model` — reads the active document and its objects.
- `inspect_features` — inspects selected FreeCAD features and their properties.
- `inspect_geometry` — inspects the active model geometry and bounding box.
- `create_case_rails` — creates the case slider rails in the active model.
- `create_slider_cover` — creates the slider cover while preserving the manually modeled case features such as the SMA antenna opening and USB-C cutout.

## Start the watchdog

The watchdog runs **outside FreeCAD**. Its job is to continuously poll GitHub for pending jobs and forward them to the FreeCAD listener.

The watchdog itself does not create a CAD model unless FreeCAD is running and the listener is available.

### Manual start

From a terminal:

```bash
cd /home/hikmah/projectx/freecad-agent
./freecad-agent-watchdog
```

Expected startup output:

```text
================================
 freecad-agent-watchdog v0.2
================================
Polling interval: 5s
FreeCAD endpoint: 127.0.0.1:8765
```

### Supervisor start

For the production/background setup, the watchdog can run under Supervisor.

Example:

```ini
[program:freecad]
directory=/home/hikmah/projectx/freecad-agent

command=/home/hikmah/projectx/freecad-agent/freecad-agent-watchdog

autostart=true
autorestart=true
startsecs=5

stdout_logfile=/var/log/freecad-agent-out.log
stderr_logfile=/var/log/freecad-agent-err.log

stdout_logfile_maxbytes=10MB
stderr_logfile_maxbytes=10MB

stdout_logfile_backups=5
stderr_logfile_backups=5

stopasgroup=true
killasgroup=true
```

For this setup, use the **absolute path** in `command`. The `directory` setting remains the working directory, but the executable path should be explicit.

After changing the Supervisor configuration:

```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl restart freecad
sudo supervisorctl status freecad
```

To watch watchdog stdout:

```bash
sudo supervisorctl tail -f freecad stdout
```

Or directly watch the configured log:

```bash
tail -f /var/log/freecad-agent-out.log
```

Watchdog errors are written to:

```text
/var/log/freecad-agent-err.log
```

## What does the watchdog do?

The watchdog is the external job runner. Every polling cycle it checks GitHub for pending CAD jobs.

For each job it:

1. Finds the pending job in the GitHub queue.
2. Marks the job as running.
3. Sends the requested action to the FreeCAD listener at `127.0.0.1:8765`.
4. Waits for FreeCAD to execute the command.
5. Marks the job as completed and stores the result when successful.
6. Marks the job as failed and stores the error when execution fails.
7. Appends the final execution result to `status.log` so the external agent can quickly determine whether the task completed or failed.

### Execution status log

The watchdog maintains:

```text
status.log
```

Each completed or failed job adds one line, for example:

```text
2026-08-16T01:30:00+00:00 | job=CAD-030 | action=ping | status=completed
2026-08-16T01:31:00+00:00 | job=CAD-031 | action=create_case_rails | status=failed | error=No active FreeCAD document
```

The `cad/jobs/CAD-xxx.json` file remains the authoritative per-job record. `status.log` is a lightweight execution history that makes it easy to see the latest watchdog results without inspecting every job file.

A failure to write `status.log` does **not** override the actual job result. The watchdog will still report the job status through `cad/jobs/*.json`.

Typical watchdog output looks like:

```text
[QUEUE] 1 pending job(s)
[JOB] CAD-029 status=pending
[JOB] CAD-029 action=ping
[JOB] CAD-029 status=completed
[STATUS] CAD-029 status=completed logged
```

If FreeCAD or the listener is not running, the watchdog cannot execute the CAD command. A typical error is:

```text
[Errno 111] Connection refused
```

This means the watchdog is alive, but nothing is listening on `127.0.0.1:8765`.

## FreeCAD source model

For CAD jobs that modify an existing model, open the source `.FCStd` file from `cad/source/` in FreeCAD and make sure it is the active document before processing the job.

Example:

```text
/home/hikmah/projectx/freecad-agent/cad/source/case-V1.FCStd
```

Do not open a previously generated output file when the job is intended to modify the source model.

For existing CAD models, preserve the source model and its feature history whenever possible. Generated geometry should be added to the active source document rather than flattening the source into a new reference-only model unless the job explicitly requires that behavior.

## Typical workflow

```text
1. Start FreeCAD
2. Open the source .FCStd model
3. Make sure the correct document is active
4. View -> Panels -> Python console
5. Start the FreeCAD listener
6. Start/verify freecad-agent-watchdog
7. Submit a CAD job to GitHub
8. Watch watchdog stdout/logs
9. FreeCAD executes the requested operation
10. Watchdog reports the result back to GitHub
11. Check status.log for a quick execution summary
```
