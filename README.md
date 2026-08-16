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

The repository path used in this example is `/app/freecad-agent`. If you clone the repository somewhere else, replace `/app/freecad-agent` with your local repository path.

Paste the following into the FreeCAD Python Console and press Enter:

```python
import importlib.util

try:
    listener.stop_server()
except Exception:
    pass

path = "/app/freecad-agent/freecad/freecad_agent_listener.py"

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

From a terminal, assuming the repository is located at `/app/freecad-agent`:

```bash
cd /app/freecad-agent
./freecad-agent-watchdog
```

The watchdog uses the Python virtual environment contained in the repository (`bin/`) and starts the agent with `python3`.

The polling interval is configured through `.env`:

```env
GITHUB_REPO=hikmahgumelar/freecad-agent
POLL_INTERVAL=30
```

`POLL_INTERVAL` is the normal idle polling interval in seconds. A value of `30` is recommended for normal operation to reduce unnecessary GitHub API traffic.

Expected startup output for v0.5:

```text
================================
 freecad-agent-watchdog v0.5
================================
Polling interval: 30s
FreeCAD endpoint: 127.0.0.1:8765
Health check: enabled
GitHub rate-limit handling: enabled
GitHub SHA-conflict recovery: enabled
GitHub network retry/backoff: enabled
```

### Supervisor start

For the production/background setup, the watchdog can run under Supervisor.

Example:

```ini
[program:freecad]
directory=/app/freecad-agent

command=/app/freecad-agent/freecad-agent-watchdog

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

## Watchdog v0.5 reliability features

Version 0.5 adds reliability controls around GitHub API communication so temporary network failures and API rate limits do not cause the watchdog to repeatedly hammer GitHub or terminate unnecessarily.

### 30-second normal polling

The normal polling interval is controlled by `POLL_INTERVAL` in `.env`. The recommended value is `30` seconds instead of the previous 5-second interval.

This reduces the number of GitHub API requests while keeping the job queue responsive enough for normal CAD work.

### GitHub rate-limit handling

When GitHub returns a rate-limit response, the watchdog detects the condition and enters a cooldown instead of continuing to poll at the normal interval.

The watchdog uses GitHub's `X-RateLimit-Reset` value when available to determine when the rate-limit window should recover. If the reset time cannot be determined, a safe fallback cooldown is used.

During cooldown, the watchdog does not continuously issue GitHub queue requests. After the cooldown expires, normal polling resumes.

Conceptually:

```text
normal polling
      |
      v
GitHub request
      |
      +-- normal --> continue every POLL_INTERVAL
      |
      +-- rate limit --> cooldown until reset
                              |
                              v
                       resume polling
```

### SHA-conflict recovery

GitHub Contents API updates require the current blob SHA. If another update changes the job file before the watchdog writes its result, GitHub can return HTTP 409.

The watchdog handles this conflict by refreshing the latest job state/SHA and retrying the state transition rather than immediately losing the result.

### Network retry and backoff

Transient GitHub connection failures such as `RemoteDisconnected`, connection errors, and timeouts are treated differently from permanent API errors.

The watchdog retries with increasing delays instead of exiting immediately:

```text
network error
    |
    +--> 30s
          |
          +--> 60s
                |
                +--> 120s
                      |
                      +--> 240s
                            |
                            +--> max 300s
```

A successful request resets the retry backoff.

### FreeCAD health check

Before executing a real CAD job, the watchdog checks the FreeCAD listener using the `ping` action.

If the listener is unavailable, the watchdog can report the execution failure instead of blindly sending the CAD command to a dead endpoint.

### Status log is best-effort

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

## What does the watchdog do?

The watchdog is the external job runner. Every polling cycle it checks GitHub for pending CAD jobs.

For each job it:

1. Finds the pending job in the GitHub queue.
2. Marks the job as running.
3. Checks that the FreeCAD listener is healthy.
4. Sends the requested action to the FreeCAD listener at `127.0.0.1:8765`.
5. Waits for FreeCAD to execute the command.
6. Marks the job as completed and stores the result when successful.
7. Marks the job as failed and stores the error when execution fails.
8. Appends the final execution result to `status.log` so the external agent can quickly determine whether the task completed or failed.

Typical watchdog output looks like:

```text
[QUEUE] 1 pending job(s)
[JOB] CAD-029 status=pending
[JOB] CAD-029 action=ping
[FREECAD] listener healthy
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
/app/freecad-agent/cad/source/case-V1.FCStd
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
