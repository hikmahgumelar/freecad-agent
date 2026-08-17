# How to Run FreeCAD Agent

This document explains how to install and run FreeCAD Agent using the same architecture used in the reference setup: Linux/Debian, FreeCAD 1.0.0, a local Python virtual environment, the FreeCAD startup listener, and Supervisor managing the external watchdog.

The intended runtime is:

```text
AI / LLM
   |
   | creates a CAD job
   v
GitHub job queue
   |
   v
freecad-agent-watchdog
   |
   | TCP 127.0.0.1:8765
   v
FreeCAD listener
   |
   v
FreeCAD document
```

FreeCAD is the CAD engine. The watchdog is the external worker that polls GitHub and sends CAD actions to the listener running inside FreeCAD.

## 1. Reference environment

The reference environment used while developing and testing this project is:

- OS: Linux / Debian
- User: `hikmah`
- FreeCAD: `1.0.0`
- Python: Python 3
- Process supervisor: Supervisor
- Watchdog: `freecad-agent-watchdog`
- FreeCAD listener: TCP `127.0.0.1:8765`
- Repository path used in the reference setup: `/home/hikmah/projectx/freecad-agent`

The exact username and repository path are not requirements. Replace them with the values for your machine.

## 2. Prerequisites

Install the basic tools needed by the project:

- Git
- Python 3
- Python virtual environment support
- FreeCAD
- Supervisor
- Bash

On Debian-based systems, the base packages can be installed with:

```bash
sudo apt update
sudo apt install -y git python3 python3-venv supervisor
```

Install FreeCAD using the package/source method appropriate for your Debian release. This project was developed and tested with FreeCAD 1.0.0.

Verify the important tools:

```bash
git --version
python3 --version
freecad --version
supervisorctl version
```

If FreeCAD is installed under a different command or location, use the appropriate command for your installation.

## 3. Clone the repository

Clone the repository and enter the project directory:

```bash
git clone https://github.com/hikmahgumelar/freecad-agent.git
cd freecad-agent
```

If you are working from your own fork, clone your fork instead.

## 4. Python environment

The repository uses a project-local Python virtual environment. The watchdog launcher activates it from:

```text
bin/activate
```

If you are setting up a fresh clone and the environment does not exist yet, create it in the project root:

```bash
python3 -m venv .
```

Then install the Python dependencies:

```bash
./bin/python3 -m pip install -r requirements.txt
```

Verify the environment:

```bash
./bin/python3 -c 'import requests, dotenv; print("Python dependencies OK")'
```

The `freecad-agent-watchdog` launcher automatically activates this project-local environment before starting the Python watchdog.

## 5. Configure GitHub access

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env`:

```env
GITHUB_REPO=your-user/your-freecad-agent
GITHUB_TOKEN=github_pat_*******************
POLL_INTERVAL=30
```

`GITHUB_REPO` is the repository containing the CAD job queue.

`GITHUB_TOKEN` is the GitHub token used by the watchdog to read and update job files.

`POLL_INTERVAL` controls how often the watchdog checks for new jobs. `30` seconds is the recommended reference value.

Never commit a real GitHub token. Keep it in `.env` only.

## 6. Install the FreeCAD startup listener

The project includes a startup installer so users do not need to manually paste listener code into the FreeCAD Python console every time.

Run:

```bash
bash scripts/install-freecad-startup.sh
```

The installer creates this FreeCAD module link:

```text
~/.local/share/FreeCAD/Mod/freecad-agent
```

which points to the repository's `freecad` directory.

The startup hook is loaded by FreeCAD when the GUI starts. It loads the large listener module and starts the server on `127.0.0.1:8765`.

The installer itself prints a message telling you to restart FreeCAD after installation.

## 7. Start FreeCAD

Close any old FreeCAD instance and start FreeCAD normally:

```bash
freecad
```

You can also start it from the desktop/application launcher.

The startup module should automatically start the listener. The current startup hook intentionally avoids relying on FreeCAD's `__file__` behavior because FreeCAD's startup loader does not guarantee normal module semantics.

A successful startup should print a message similar to:

```text
[freecad-agent] startup listener ready on 127.0.0.1:8765
```

Verify from another terminal:

```bash
ss -ltnp | grep 8765
```

Expected result:

```text
LISTEN ... 127.0.0.1:8765 ... freecad ...
```

If `8765` is not listening, do not start the watchdog yet. Fix the FreeCAD startup/listener problem first.

## 8. Manual listener fallback

The normal method is automatic startup. Manual startup is only a troubleshooting fallback.

Open FreeCAD's Python console:

```text
View → Panels → Python console
```

Then load the listener from the repository. Replace the repository path with your own path:

```python
import importlib.util

try:
    listener.stop_server()
except Exception:
    pass

path = "/home/hikmah/projectx/freecad-agent/freecad/freecad_agent_listener_large.py"
spec = importlib.util.spec_from_file_location("freecad_agent_listener_latest", path)
listener = importlib.util.module_from_spec(spec)
spec.loader.exec_module(listener)
listener.start_server()
```

A successful manual start should result in:

```text
[freecad-agent] stopped
[freecad-agent] listening on 127.0.0.1:8765
```

Again, this is a fallback. A normal installation should start the listener automatically when FreeCAD launches.

## 9. Start the watchdog manually

Before using Supervisor, test the watchdog directly so that configuration problems are easy to see.

From the repository root:

```bash
./freecad-agent-watchdog
```

The launcher activates the local virtual environment and runs:

```text
python3 -m agent.main
```

Typical startup information includes:

```text
Polling interval: 30s
FreeCAD endpoint: 127.0.0.1:8765
Health check: enabled
GitHub rate-limit handling: enabled
GitHub SHA-conflict recovery: enabled
GitHub network retry/backoff: enabled
```

Leave this running while testing jobs.

## 10. Run the watchdog under Supervisor

For a permanent setup, Supervisor can keep the watchdog running and restart it if it exits.

Install Supervisor if it is not already installed:

```bash
sudo apt install -y supervisor
```

Create a configuration file such as:

```text
/etc/supervisor/conf.d/freecad.conf
```

Use the following reference configuration:

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
user=hikmah
```

Replace the `directory`, `command`, and `user` values with your own environment.

Then load the configuration:

```bash
sudo supervisorctl reread
sudo supervisorctl update
```

Start the program:

```bash
sudo supervisorctl start freecad
```

Check it:

```bash
sudo supervisorctl status freecad
```

Expected state:

```text
freecad    RUNNING
```

The Supervisor program is named `freecad`, even though the actual command it launches is `freecad-agent-watchdog`.

## 11. Normal daily startup

Once the installation is complete, the normal workflow is simple:

1. Start FreeCAD.
2. Let the FreeCAD startup hook start the listener automatically.
3. Verify `127.0.0.1:8765` is listening if you are troubleshooting.
4. Keep the Supervisor-managed watchdog running.
5. Create or submit a CAD job through the configured GitHub job queue.
6. The watchdog detects the pending job.
7. The watchdog health-checks FreeCAD.
8. The watchdog sends the action to FreeCAD.
9. FreeCAD creates or modifies the CAD document.
10. The watchdog writes the job result back to GitHub.

You should not normally need to paste Python code into FreeCAD for every job.

## 12. Checking the complete runtime

Use these checks when debugging:

Check FreeCAD:

```bash
pgrep -a freecad
```

Check the listener:

```bash
ss -ltnp | grep 8765
```

Check Supervisor:

```bash
sudo supervisorctl status freecad
```

Check watchdog logs:

```bash
sudo tail -f /var/log/freecad-agent-out.log
```

Check watchdog errors:

```bash
sudo tail -f /var/log/freecad-agent-err.log
```

## 13. Common failure: FreeCAD opens but port 8765 is not listening

This means the FreeCAD startup hook did not successfully start the listener.

First run:

```bash
freecad
```

and inspect the terminal output.

Then check:

```bash
ss -ltnp | grep 8765
```

If nothing is returned, use the manual listener fallback from section 8. If manual startup works, the problem is specifically in the startup hook/module loading path.

The startup hook is designed to print an explicit error when it cannot load the listener.

## 14. Common failure: `__file__` or `_module_dir` startup errors

Older versions of the startup integration relied on variables that FreeCAD's startup loader does not guarantee. Errors such as:

```text
name '__file__' is not defined
```

or:

```text
name '_module_dir' is not defined
```

indicate that an older startup implementation is being loaded.

Update the repository and reinstall the startup module:

```bash
git pull
bash scripts/install-freecad-startup.sh
```

Then completely restart FreeCAD.

The current `InitGui.py` resolves the module directory through FreeCAD's user application directory and `sys.path`, rather than depending on `__file__`.

## 15. Common failure: `Connection refused`

If a CAD job fails with:

```text
[Errno 111] Connection refused
```

check the listener first:

```bash
ss -ltnp | grep 8765
```

If the port is not listening, FreeCAD is not exposing the execution endpoint. Start/restart FreeCAD and verify the listener before retrying the job.

Do not change the CAD job specification just because the connection failed. A connection failure is an execution/infrastructure problem, not necessarily a CAD design problem.

## 16. Common failure: FreeCAD GUI does not appear

Run FreeCAD directly from a terminal:

```bash
freecad
```

This exposes startup messages that may not be visible when launching from the desktop.

On the reference environment, FreeCAD may report a Wayland message similar to:

```text
Wayland detected. Forcing Qt to use X11 backend (xcb) to avoid Coin3D EGL issue.
```

That message by itself is not the FreeCAD Agent listener failure. Continue checking whether FreeCAD stays open and whether port `8765` is listening.

## 17. Common failure: Supervisor reports an error

Check the program state:

```bash
sudo supervisorctl status freecad
```

Then inspect:

```bash
sudo tail -100 /var/log/freecad-agent-out.log
sudo tail -100 /var/log/freecad-agent-err.log
```

After changing the Supervisor configuration, reload it:

```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl restart freecad
```

The Supervisor `freecad` process is the watchdog. It is not the GUI FreeCAD process itself.

FreeCAD must still be running separately so that the watchdog can connect to `127.0.0.1:8765`.

## 18. Architecture and process ownership

There are two independent processes:

```text
Supervisor
    |
    v
freecad-agent-watchdog
    |
    | TCP 127.0.0.1:8765
    v
FreeCAD GUI
    |
    v
FreeCAD listener
```

Supervisor does not replace FreeCAD. It keeps the external watchdog alive.

FreeCAD owns the CAD document and the listener.

This distinction is important when diagnosing failures:

- Watchdog down → GitHub jobs are not processed.
- FreeCAD down → listener is unavailable.
- FreeCAD running but listener down → watchdog receives connection errors.
- Both running and listener available → jobs can be executed.

## 19. Job lifecycle

A typical job moves through states such as:

```text
pending
   ↓
running
   ↓
completed
```

or:

```text
pending
   ↓
running
   ↓
failed
```

The CAD job JSON in `cad/jobs/` is the authoritative record for the individual job.

## 20. Example prompt-to-CAD workflow

A user can describe a design in natural language, for example:

```text
Create a 90 × 60 × 11 mm electronics enclosure.

- Put a USB-C opening on one 60 mm face.
- Put the SMA antenna opening on the opposite 60 mm face.
- Put the antenna opening 10 mm from the edge of that 60 mm face.
- Add four Ø3 mm mounting holes.
- Create a separate removable cover.
- Keep the geometry suitable for 3D printing.
```

The AI layer turns the intent into a structured CAD job. The watchdog queues and executes it. FreeCAD creates the actual geometry.

The important workflow is:

```text
Natural language
      ↓
AI interpretation
      ↓
Structured CAD job
      ↓
GitHub queue
      ↓
Watchdog
      ↓
FreeCAD listener
      ↓
Real CAD geometry
      ↓
FCStd / STEP / STL
      ↓
3D printing
```

## 21. Production-style recommendation

For a machine that is always available for CAD jobs:

- Keep Supervisor enabled for the watchdog.
- Start FreeCAD when the desktop session is available.
- Keep the FreeCAD listener on `127.0.0.1:8765`.
- Keep the repository `.env` protected.
- Monitor Supervisor logs.
- Verify the listener before submitting important jobs.
- Keep generated CAD files under version control or another appropriate artifact store when they need to be preserved.

## 22. Security notes

The listener binds to:

```text
127.0.0.1:8765
```

This keeps the CAD execution endpoint local to the machine by default.

Do not expose the listener directly to an untrusted network without adding an appropriate authentication and transport-security layer.

Protect the GitHub token in `.env` and never commit it to the repository.

## 23. Updating FreeCAD Agent

Stop the watchdog if it is managed by Supervisor:

```bash
sudo supervisorctl stop freecad
```

Update the repository:

```bash
git pull
```

Update Python dependencies if required:

```bash
./bin/python3 -m pip install -r requirements.txt
```

Reinstall the FreeCAD startup module if the listener/startup code changed:

```bash
bash scripts/install-freecad-startup.sh
```

Start FreeCAD again and verify:

```bash
ss -ltnp | grep 8765
```

Then start the watchdog:

```bash
sudo supervisorctl start freecad
sudo supervisorctl status freecad
```

## 24. Summary

A complete working installation has these pieces:

```text
Debian Linux
    |
    +-- FreeCAD 1.0.0
    |      |
    |      +-- startup module
    |      +-- listener :8765
    |
    +-- freecad-agent repository
    |      |
    |      +-- Python virtual environment
    |      +-- CAD jobs
    |      +-- watchdog
    |
    +-- Supervisor
           |
           +-- freecad
                |
                +-- freecad-agent-watchdog
```

Once this is running, the user-facing experience is intentionally simple: describe the CAD design, create the job, and let the agent execute it through FreeCAD.
