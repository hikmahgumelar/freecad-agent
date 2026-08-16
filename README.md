# FreeCAD Agent

**AI-driven CAD automation for creating and modifying 3D models in FreeCAD through natural-language prompting.**

FreeCAD Agent connects an AI agent to a running FreeCAD instance. Instead of manually translating every requirement into CAD operations, a user or AI can describe the desired model or modification in natural language. The request becomes a CAD job, the watchdog picks it up, and the FreeCAD listener executes the operation against the active FreeCAD document.

![FreeCAD Agent example 3D output](docs/images/CasingStd-v2-Body.svg)

> Example output: an enclosure model used as a representative CAD example for the FreeCAD Agent workflow.

## What is FreeCAD Agent?

FreeCAD Agent is a bridge between **AI prompting, job orchestration, and FreeCAD**.

A typical request can look like:

```text
Create an enclosure 90 mm × 60 mm × 11 mm.
Add a USB-C opening centered on one 60 mm side,
a 7 mm antenna opening on the opposite side,
corner mounting holes, and a 1.5 mm cover.
```

The request is translated into a CAD job and processed by the system:

```text
Natural-language prompt
        |
        v
     CAD Job
        |
        v
      GitHub
        |
        v
freecad-agent-watchdog
        |
        | TCP 127.0.0.1:8765
        v
 FreeCAD listener
        |
        v
  Active 3D model
        |
        v
Result / status
```

The actual CAD engine remains FreeCAD. FreeCAD Agent provides the automation and communication layer around it.

## What can it do?

FreeCAD Agent is designed to:

- Create 3D CAD geometry from AI-generated CAD jobs.
- Modify existing `.FCStd` models while working against the active FreeCAD document.
- Inspect models, features, geometry, and bounding boxes.
- Execute FreeCAD operations through the FreeCAD Python API.
- Verify that the FreeCAD listener is alive before executing a job.
- Report completed and failed jobs back to GitHub.
- Maintain a lightweight execution history in `status.log`.
- Recover from GitHub SHA conflicts.
- Handle GitHub API rate limits without continuously polling.
- Retry transient GitHub network failures using exponential backoff.

## Example: prompt to CAD

A high-level CAD requirement can be expressed as a normal prompt:

```text
Create a small electronics enclosure.

Dimensions:
- 90 mm long
- 60 mm wide
- 11 mm high

Features:
- USB-C opening centered on one 60 mm side
- 7 mm antenna opening on the opposite 60 mm side
- corner mounting holes
- removable 1.5 mm cover
```

The AI agent can turn that requirement into a structured CAD job. The watchdog retrieves the job, checks FreeCAD, sends the requested action to the listener, and records the result.

This makes the project useful as an automation layer for AI-assisted CAD rather than as another standalone CAD application.

## Prerequisites

Before running FreeCAD Agent, prepare the following:

### Required software

- **FreeCAD** — must be installed and available on the machine where the CAD model will be executed. FreeCAD must be running when a CAD job is processed.
- **Python 3** — used by the external watchdog. The repository includes a Python virtual environment under `bin/`.
- **Git** — required to clone and update the repository.
- **Supervisor** — optional, but recommended when running the watchdog as a background service.

### Python dependencies

The watchdog currently requires:

```text
requests>=2.32,<3
python-dotenv>=1.0,<2
```

They are defined in `requirements.txt` and should be installed into the repository's Python virtual environment.

From the repository root:

```bash
./bin/python3 -m pip install -r requirements.txt
```

Verify the environment with:

```bash
./bin/python3 -c 'import requests, dotenv; print("Python dependencies OK")'
```

### GitHub access

The watchdog uses the configured GitHub repository as the CAD job queue and reports job state/results back to GitHub.

Create a local `.env` file in the repository root:

```env
GITHUB_REPO=hikmahgumelar/freecad-agent
GITHUB_TOKEN=github_pat_*******************
POLL_INTERVAL=30
```

`GITHUB_TOKEN` must contain your own GitHub Personal Access Token (PAT). The value above is only a placeholder; never copy it as a real credential.

Do **not** commit `.env` or any real token to the repository. The repository `.gitignore` is configured to ignore `.env`.

A safe starting point is the included `.env.example`:

```bash
cp .env.example .env
```

Then replace the placeholder token with your own PAT.

### FreeCAD listener

The FreeCAD listener runs **inside FreeCAD**, not inside the watchdog virtual environment. It uses the FreeCAD Python API and exposes the local endpoint:

```text
127.0.0.1:8765
```

The listener must be started before the watchdog can execute CAD jobs.

## Architecture

The system has two primary runtime components:

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
GITHUB_TOKEN=github_pat_*******************
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

### Status log

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
1. Write or generate a CAD prompt
2. Convert the prompt into a CAD job
3. Start FreeCAD
4. Open the source .FCStd model if required
5. Make sure the correct document is active
6. View -> Panels -> Python console
7. Start the FreeCAD listener
8. Start/verify freecad-agent-watchdog
9. Submit the CAD job to GitHub
10. Watch watchdog stdout/logs
11. FreeCAD executes the requested operation
12. Watchdog reports the result back to GitHub
13. Check status.log for a quick execution summary
```

## Verified CAD result

The enclosure automation was verified end-to-end in FreeCAD using the `create_box_enclosure` CAD job.

Verified model:

```text
90 mm × 60 mm × 11 mm enclosure
1.5 mm removable cover
4 × Ø3 mm mounting holes
USB-C opening on a 60 mm face
Ø7 mm SMA antenna opening on the opposite 60 mm face
10 mm antenna clearance measured from the face edge to the opening edge
```

The final FreeCAD document was inspected directly through the FreeCAD Python console rather than relying only on the visual orientation of the viewport. The base bounding box was verified as:

```text
BoundBox (0, 0, 0, 90, 60, 11)
Length = 90 mm
Width  = 60 mm
Height = 11 mm
```

The successful result places the USB-C and antenna interfaces on the two opposite **60 mm × 11 mm end faces**, not on the 90 mm × 11 mm long faces.

The antenna requirement is specifically:

```text
Face: 60 mm × 11 mm
Opening: Ø7 mm
Clearance: 10 mm from the face edge to the opening edge
```

For a Ø7 mm opening, this means the opening center is 13.5 mm from the corresponding face edge.

The final model also keeps the cover as a separate FreeCAD object so the base and cover can be exported independently for 3D printing.

### Runtime verification

During debugging, the FreeCAD model topology was inspected directly using `Shape.Faces` and bounding boxes. This exposed an earlier listener/runtime problem where the generated result did not match the current geometry source.

The listener was subsequently changed so the enclosure module is loaded from the exact repository path and the enclosure function is resolved at job execution time. This prevents a stale imported function reference from being reused after source changes.

The verified runtime sequence is therefore:

```text
AI prompt
   |
   v
CAD job
   |
   v
GitHub queue
   |
   v
freecad-agent-watchdog
   |
   v
FreeCAD listener
   |
   v
create_box_enclosure()
   |
   v
FreeCAD document
   |
   v
Topology / geometry verification
   |
   v
Completed CAD result
```

This verification is an example of the intended FreeCAD Agent workflow: CAD generation is not considered complete merely because a job reports `completed`; the resulting FreeCAD geometry can also be inspected programmatically when dimensional or placement accuracy matters.
