# FreeCAD Agent

**Prompt → CAD → 3D Print.**

FreeCAD Agent is an open-source AI agent infrastructure for turning natural-language CAD requests into real FreeCAD models through a lightweight, local execution pipeline.

You describe what you want to build. An AI agent turns the intent into a structured CAD job. FreeCAD executes it. The result is a real `.FCStd` model that can be inspected, modified, and exported for manufacturing or 3D printing.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

![Real FreeCAD enclosure with removable cover](docs/images/case-with-cover.jpg)

> **From a prompt to a real CAD result — without manually rebuilding the model from scratch.**

## See it in action

This repository is built around a real workflow, not a mock demo.

A real enclosure requirement was described in natural language:

```text
Create a 90 × 60 × 11 mm electronics enclosure.

Requirements:
- USB-C opening centered on one 60 mm side.
- SMA antenna opening Ø7 mm on the opposite 60 mm side.
- Four Ø3 mm mounting holes at the corners.
- Separate removable 1.5 mm cover.
- Keep the geometry suitable for 3D printing.
```

The important part is that the design starts as **intent expressed in a prompt**, not as a hand-written FreeCAD script. The AI agent translates the request into a CAD job, the watchdog delivers it, and FreeCAD creates the actual geometry.

### Real result

**TARUH GAMBAR HASIL DI SINI**

Use the real result image here — ideally the screenshot showing the finished enclosure with the **SMA antenna opening, USB-C opening, mounting holes, and removable cover**.

The workflow is:

```text
Prompt
  ↓
AI understands the design intent
  ↓
Structured CAD job
  ↓
FreeCAD Agent
  ↓
Real FreeCAD geometry
  ↓
STL / STEP
  ↓
3D print
```

The enclosure example is only one possibility. The same infrastructure can be used for brackets, adapters, mechanical parts, robotics components, fixtures, electronics cases, and other CAD workflows.

## Why this project exists

FreeCAD is already a powerful CAD engine. The difficult part for an AI system is turning a user's intent into reliable operations against a real CAD document.

FreeCAD Agent provides that execution layer.

```text
Natural-language prompt
        |
        v
     AI Agent
        |
        | intent → structured CAD job
        v
    GitHub Job
        |
        v
freecad-agent-watchdog
        |
        | TCP 127.0.0.1:8765
        v
 FreeCAD listener
        |
        v
Active FreeCAD document
        |
        v
  CAD result / status
        |
        v
.FCStd → STEP / STL → 3D print
```

The goal is not to replace FreeCAD. The goal is to make FreeCAD **programmable by AI through natural language** while keeping FreeCAD itself as the source of truth for geometry and document state.

## Why fork it?

This project is intentionally designed to be **forked, modified, and extended**.

Fork it if you want to build:

- Your own AI-powered CAD assistant.
- A local LLM → FreeCAD workflow.
- A prompt-to-3D-print pipeline.
- A CAD automation agent for electronics enclosures.
- A robotics or manufacturing CAD pipeline.
- A custom FreeCAD tool server.
- An experimental parametric-modeling agent.

The core infrastructure does not care which AI model generates the intent. You can connect your own LLM, agent framework, UI, or workflow on top of the same execution layer.

**Fork the infrastructure. Add your own CAD actions. Bring your own ideas.**

The more people build on top of it, the more useful the ecosystem becomes.

## What can it do?

- Create CAD geometry from structured AI-generated jobs.
- Modify existing `.FCStd` documents through the active FreeCAD instance.
- Inspect models, features, geometry, and bounding boxes.
- Execute operations through the FreeCAD Python API.
- Check FreeCAD health before executing a job.
- Report completed and failed jobs back to GitHub.
- Keep a lightweight execution history in `status.log`.
- Recover from GitHub SHA conflicts.
- Handle GitHub API rate limits without aggressive polling.
- Retry transient GitHub network failures with exponential backoff.
- Provide an extension point for export and manufacturing workflows such as STEP/STL.

## The core idea

You should be able to say:

```text
Make this enclosure 200 × 100 × 150 mm.
Use 2 mm walls and a 2 mm bottom.
Put a 2 mm internal plate in the middle.
Add six Ø50 mm holes in a 3 × 2 pattern.
Create a separate lid that fits over the body.
```

…and let the agent deal with the CAD execution details.

The same workflow can then handle iterative changes:

```text
Make the lid fit with 0.2 mm clearance.
Keep everything else unchanged.
```

Or:

```text
Move the antenna opening 10 mm from the edge.
Do not change the USB-C opening.
```

This is the direction of the project: **natural-language design iteration against real CAD geometry.**

## Architecture

There are two primary runtime components.

### FreeCAD listener

Runs **inside FreeCAD** and uses the FreeCAD Python API.

Endpoint:

```text
127.0.0.1:8765
```

It receives an action, executes it against the active FreeCAD document, and returns the result.

### `freecad-agent-watchdog`

Runs **outside FreeCAD**. It:

1. Finds pending CAD jobs in GitHub.
2. Marks the job as running.
3. Checks the FreeCAD listener with `ping`.
4. Sends the requested action to FreeCAD.
5. Waits for the result.
6. Writes the completed or failed state back to GitHub.
7. Records the result in `status.log`.

GitHub is currently used as the lightweight job queue and state store. This keeps the infrastructure simple and makes CAD jobs inspectable as normal repository artifacts.

## Repository layout

```text
freecad-agent/
├── agent/                         # External watchdog runtime
│   ├── config.py
│   ├── freecad_executor.py
│   ├── github.py
│   ├── jobs.py
│   └── main.py
├── freecad/                       # FreeCAD-side listener
│   └── freecad_agent_listener.py
├── cad/
│   ├── jobs/                      # CAD job definitions/results
│   └── source/                    # Source FreeCAD documents
├── docs/images/                   # Real CAD result examples
├── .env.example
├── requirements.txt
├── freecad-agent-watchdog
└── README.md
```

## Quick start

### Prerequisites

You need FreeCAD, Python 3, Git, and a GitHub token with permission to read/update the job files. Supervisor is optional for long-running watchdog operation.

### 1. Clone

```bash
git clone https://github.com/hikmahgumelar/freecad-agent.git
cd freecad-agent
```

If you fork first, replace the URL with your fork.

### 2. Configure GitHub

```bash
cp .env.example .env
```

Set your own values:

```env
GITHUB_REPO=your-user/your-freecad-agent
GITHUB_TOKEN=github_pat_*******************
POLL_INTERVAL=30
```

Never commit a real token. `.env` is ignored by Git.

### 3. Install dependencies

```bash
./bin/python3 -m pip install -r requirements.txt
./bin/python3 -c 'import requests, dotenv; print("Python dependencies OK")'
```

### 4. Start FreeCAD

Open FreeCAD and the `.FCStd` document you want to work on. Make sure it is the **active document**.

### 5. Start the listener

Open:

```text
View → Panels → Python console
```

Replace `/app/freecad-agent` with your clone path and paste:

```python
import importlib.util

try:
    listener.stop_server()
except Exception:
    pass

path = "/app/freecad-agent/freecad/freecad_agent_listener.py"
spec = importlib.util.spec_from_file_location("freecad_agent_listener_latest", path)
listener = importlib.util.module_from_spec(spec)
spec.loader.exec_module(listener)
listener.start_server()
```

Successful startup:

```text
[freecad-agent] stopped
[freecad-agent] listening on 127.0.0.1:8765
```

Keep FreeCAD open while jobs are being processed.

### 6. Start the watchdog

In another terminal:

```bash
./freecad-agent-watchdog
```

Typical startup output:

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

The infrastructure is now ready to receive and execute CAD jobs.

## Creating a CAD job

Jobs live under:

```text
cad/jobs/
```

The AI layer can generate the job JSON, while the watchdog remains responsible for execution and state transitions.

```text
AI / LLM
   |
   | generates intent
   v
CAD Job
   |
   | queue
   v
Watchdog
   |
   | execute
   v
FreeCAD
```

This separation means you can replace the AI layer without replacing the FreeCAD execution infrastructure.

## Reliability

The watchdog includes protections for long-running operation.

**Rate limits:** normal polling uses `POLL_INTERVAL`; `30` seconds is recommended. When GitHub reports a rate limit, the watchdog enters a cooldown and resumes after the limit recovers.

**SHA conflicts:** GitHub Contents API updates use the current blob SHA. If another update changes a job before the watchdog writes the result, the watchdog refreshes the state and retries.

**Network failures:** transient connection failures and timeouts use increasing retry delays instead of immediately terminating the watchdog.

**FreeCAD health:** before executing a real CAD action, the watchdog checks the listener with `ping`.

**Execution history:** `status.log` records completed and failed executions. The individual `cad/jobs/CAD-xxx.json` file remains the authoritative job record.

## Supervisor

For a long-running setup, the watchdog can run under Supervisor:

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

Use an absolute path for `command`.

```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl restart freecad
sudo supervisorctl status freecad
```

## Extending FreeCAD Agent

The most useful extension point is the CAD action layer:

```text
AI request
   ↓
structured CAD job
   ↓
watchdog
   ↓
FreeCAD listener
   ↓
new CAD action
   ↓
FreeCAD API
   ↓
result
```

Possible actions include:

- Create parametric parts.
- Modify dimensions.
- Add or move holes.
- Create mounting features.
- Inspect topology.
- Measure geometry.
- Export STEP/STL.
- Validate clearances.
- Generate manufacturing variants.

The actions stay separate from the queue and transport infrastructure so contributors can experiment without rewriting the whole system.

## Current status

The core execution infrastructure is operational:

- GitHub job queue
- Watchdog
- FreeCAD listener
- Local TCP execution path
- Job state/result reporting
- Health checks
- Rate-limit handling
- SHA-conflict recovery
- Network retry/backoff
- Real CAD example workflow

The project is moving from **infrastructure construction** toward **useful CAD actions, AI integrations, reusable examples, and community contributions**.

## Roadmap

```text
Prompt-to-CAD infrastructure
            ↓
Reliable CAD execution
            ↓
More CAD actions
            ↓
AI / local-LLM integrations
            ↓
STEP / STL manufacturing workflows
            ↓
Reusable examples
            ↓
Community contributions
```

Good contribution areas include new FreeCAD actions, model inspection, CAD examples, AI/local-LLM integrations, job schema improvements, testing, reliability, manufacturing workflows, and documentation.

## Contributing

Fork the repository, create a branch, make your change, test it against FreeCAD, and open a pull request.

Small focused contributions are especially useful: new CAD actions, reproducible examples, integrations, and documentation.

If you build something interesting on top of FreeCAD Agent, share it so others can fork and extend it too.

### Community direction

The long-term goal is bigger than one CAD assistant.

Different people will want different things from the same infrastructure: electronics enclosures, mechanical parts, robotics components, brackets, adapters, manufacturing fixtures, or completely new AI-driven CAD workflows.

**Fork it. Try a different prompt. Add a CAD action. Share the result.**

That is how this project can grow from an automation tool into a community-driven prompt-to-CAD platform.

## Design principle

> **AI decides what should happen. FreeCAD decides how CAD actually happens.**

The agent describes intent and generates structured operations. FreeCAD remains the source of truth for geometry and document state.

## License

FreeCAD Agent is released under the **MIT License**. See [`LICENSE`](LICENSE) for the full license text.

Copyright (c) 2026 Gugum.
