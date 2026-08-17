# GPT-FreeCad-Agent

## Purpose

This document is the session handoff / operating manual for an AI assistant working on the `freecad-agent` repository.

If a new ChatGPT session starts, read this file first. It is intended to prevent the workflow, architecture, repository rules, job lifecycle, and project decisions from being reconstructed from zero.

Repository:

`https://github.com/hikmahgumelar/freecad-agent`

Default branch:

`master`

The project goal is:

**Natural-language prompt → structured CAD job → GitHub queue → FreeCAD Agent → real `.FCStd` result → STL/STEP → 3D printing.**

The project is an execution layer around FreeCAD. The AI does not replace FreeCAD as the geometry source of truth.

---

## 1. Working relationship and rules

The user is Gugum. In conversation use an informal style such as `bro` / `lo`.

The assistant acts as the engineering partner / software architect for this repository. Be proactive and hands-on: inspect the repository, create or modify implementation artifacts, create CAD jobs, review results, and keep the workflow moving.

### Critical Git workflow rule

**Never push experimental work directly to `master` unless the user explicitly asks for a master change.**

Normal development workflow:

1. Create a dedicated branch.
2. Implement the change.
3. Create a PR into `master`.
4. User reviews it.
5. Only after both sides agree, merge the PR.

Documentation / real-use-case work should normally use a dedicated branch such as:

`docs/real-use-cases`

The user explicitly wants to review before merging.

### Exception

The user may explicitly request a small, intentional master update, for example maintaining this handoff document. In that case the direct master change is allowed.

---

## 2. Current project concept

FreeCAD Agent has two runtime sides.

### A. External watchdog

`freecad-agent-watchdog` runs outside FreeCAD.

Its responsibility is to:

1. Read pending CAD jobs from GitHub.
2. Mark the job `running`.
3. Health-check the FreeCAD listener.
4. Send the requested action to FreeCAD.
5. Receive the result.
6. Mark the job `completed` or `failed`.
7. Write execution status to `status.log`.
8. Recover from GitHub SHA conflicts.
9. Handle GitHub API rate limits.
10. Retry transient GitHub network errors with backoff.

The current watchdog identifies itself as `v0.5` and has health checks, SHA-conflict recovery, rate-limit handling, and network retry/backoff enabled.

### B. FreeCAD-side listener

`freecad/freecad_agent_listener.py` runs inside FreeCAD and uses the FreeCAD Python API.

Current endpoint:

`127.0.0.1:8765`

The watchdog checks it with:

```json
{"action":"ping"}
```

A healthy listener returns an `ok` response.

The listener currently supports actions including:

- `ping`
- `create_sphere`
- `open_model`
- `inspect_model`
- `inspect_features`
- `inspect_geometry`
- `create_case_rails`
- `create_slider_cover`
- other CAD actions implemented by the current listener source

Always inspect the current listener before assuming an action exists or has a particular schema.

---

## 3. GitHub is the current job queue

GitHub repository files are currently used as the lightweight job queue and state store.

The watchdog polls for pending job JSON files under the repository's CAD job area.

A normal lifecycle is:

```text
pending
   ↓
running
   ↓
FreeCAD execution
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

A successful CAD execution is not the same thing as successful GitHub status reporting. A job can complete in FreeCAD and then encounter a transient GitHub error while writing status. Always distinguish CAD execution from reporting/network errors.

---

## 4. Runtime configuration

Configuration is loaded from environment variables using `python-dotenv`.

Current configuration fields are:

```text
GITHUB_TOKEN
GITHUB_REPO
POLL_INTERVAL
FREECAD_AGENT_HOST
FREECAD_AGENT_PORT
```

Defaults in the current code:

```text
POLL_INTERVAL=5
FREECAD_AGENT_HOST=127.0.0.1
FREECAD_AGENT_PORT=8765
```

`GITHUB_REPO` can be supplied as either `owner/repo` or a GitHub HTTP(S) repository URL; the current config normalizes it.

Never put a real GitHub token into tracked files.

---

## 5. Python environment

The project uses Python 3.

Current `requirements.txt` contains:

```text
requests>=2.32,<3
python-dotenv>=1.0,<2
```

The local virtual environment is intentionally **not tracked by Git**.

Important repository cleanup decision:

```text
bin/
lib/
lib64/
```

must remain ignored / local-only. Do not commit the local Python virtual environment to the repository.

If the local virtual environment disappears after a clean checkout or cleanup, recreate it instead of restoring `bin/`, `lib/`, or `lib64/` to Git:

```bash
cd /home/hikmah/projectx/freecad-agent
python3 -m venv .
source bin/activate
pip3 install -r requirements.txt
```

The exact FreeCAD Python environment may be separate from the watchdog venv. Do not assume the two runtimes use the same Python executable.

---

## 6. Known TLS / certifi lesson

We previously recreated the Python virtual environment and then saw a watchdog error referring to:

```text
.../lib/python3.13/site-packages/certifi/cacert.pem
```

The eventual verification showed that the venv itself was healthy:

```text
certifi.where() -> /home/hikmah/projectx/freecad-agent/lib/python3.13/site-packages/certifi/cacert.pem
CA exists -> True
requests.get('https://api.github.com') -> 200
```

The system Python also successfully reached GitHub.

Therefore, if this type of error appears again:

1. Do not immediately modify TLS environment variables.
2. Check `certifi.where()`.
3. Check that the file exists.
4. Test `requests.get('https://api.github.com')` from the same venv.
5. Remember Supervisor may be running an older process/environment.
6. Restart the Supervisor process after repairing the venv.

Useful diagnostics:

```bash
python3 -c "import requests, certifi; print('requests:', requests.__version__); print('certifi:', certifi.where()); print('CA exists:', __import__('os').path.exists(certifi.where())); r=requests.get('https://api.github.com', timeout=10); print(r.status_code)"
```

Check for unexpected TLS variables:

```bash
env | grep -Ei 'SSL|REQUESTS|CURL'
```

Normally these should not be manually set for this project.

---

## 7. Supervisor operation

For long-running operation the watchdog can be managed by Supervisor.

Typical checks:

```bash
sudo supervisorctl status freecad
```

Restart after environment or runtime changes:

```bash
sudo supervisorctl restart freecad
sudo supervisorctl status freecad
```

Follow logs:

```bash
sudo supervisorctl tail -f freecad
```

Confirm the FreeCAD listener is actually listening:

```bash
ss -ltnp | grep 8765
```

Expected shape:

```text
127.0.0.1:8765 ... LISTEN ... freecad
```

A `RUNNING` Supervisor process alone is not enough; verify that the listener is healthy too.

---

## 8. How to submit a CAD job

The assistant should create a job JSON in the repository's CAD job area using a unique job ID.

A job should contain enough information that another session can understand the requested CAD operation without relying on hidden conversation context.

Typical fields include:

```json
{
  "id": "CAD-XXX",
  "action": "<listener action>",
  "status": "pending",
  "created_by": "ChatGPT",
  "parameters": {
    "...": "..."
  },
  "revision": 1,
  "revision_note": "..."
}
```

The exact schema must follow the current repository's job files and queue implementation. Do not invent fields that conflict with the current implementation.

Before creating a new job:

1. Check the existing job IDs.
2. Do not reuse an old job ID accidentally.
3. If an existing job is already `completed`, prefer a revision/new job rather than overwriting its historical result.
4. Clearly describe the requested geometry in `revision_note`.
5. Include printability constraints when they materially affect the requested design.

After submission, the user-side watchdog should pick it up automatically when it is running.

The assistant should report the job ID and then wait for the user to provide or confirm execution logs when live machine access is not available.

---

## 9. CAD job review discipline

Do not treat this as sufficient:

```text
[JOB] CAD-XXX status=completed
```

A completed job only proves that the FreeCAD action returned successfully.

For important geometry, inspect the actual result.

The preferred validation loop is:

```text
Prompt
  ↓
CAD job
  ↓
FreeCAD completed
  ↓
Open/inspect result
  ↓
Visual review
  ↓
Geometry validation
  ↓
Printability review
  ↓
User approval
  ↓
Real Use Case documentation
```

For geometry-heavy jobs, explicitly verify:

- dimensions
- orientation
- hole diameter
- hole count
- hole spacing / overlap
- plate placement
- wall thickness
- lid/body relationship
- clearances
- whether parts are separate objects
- whether the result is suitable for STL export / 3D printing

Do not rely on a generated sketch or verbal description when the user wants a real CAD result. The goal is a real FreeCAD model.

---

## 10. CAD Printability Skill — mandatory

**Every CAD creation, modification, or print request must be reviewed from the real FDM/3D-printing point of view before the design is considered ready.**

CAD-valid is not automatically FDM-printable.

The mandatory workflow is:

```text
Prompt
  ↓
CAD requirements
  ↓
FreeCAD geometry
  ↓
Printability review
  ↓
STL / STEP
  ↓
Slicer validation
  ↓
3D print
  ↓
Assembly / fit validation
```

### 10.1 Print orientation

Determine the sensible print orientation for each part. Check build-plate contact, layer direction, unsupported surfaces, and whether rotating the part eliminates unnecessary support.

Never assume the CAD orientation is the correct printing orientation.

### 10.2 Overhangs and floating geometry

Explicitly identify:

- ceiling / roof surfaces
- horizontal shelves or plates
- bridges
- deep recesses
- underside features
- lid geometry
- any geometry effectively floating above empty space

A large horizontal enclosure ceiling attached to vertical walls is a common FDM support problem.

If a feature floats in the intended print orientation, solve it by changing orientation, splitting the part, redesigning the feature, adding permanent structure, or using slicer-generated support when appropriate.

### 10.3 Support strategy

If support is required, evaluate whether it is practical to remove.

Prefer minimal support volume, accessible contact interfaces, breakaway-friendly surfaces, and tree support when it materially improves removal.

Do not automatically model temporary slicer support as permanent CAD geometry.

### 10.4 Part separation

Split a design into separate printable parts when a one-piece design creates avoidable support problems.

Common examples:

- body + lid
- body + internal perforated plate
- enclosure + mounting bracket
- shell + removable panel

Every separate part must have a clear insertion/removal direction and appropriate assembly clearance.

### 10.5 FDM clearance

Do not make mating parts exactly the same nominal dimension unless the fit requirement and manufacturing process are known.

For initial FDM fit testing, around **0.3 mm clearance per side** is a reasonable starting point, not a universal guarantee. Actual fit depends on printer, nozzle, material, layer height, cooling, extrusion calibration, and slicer settings.

Treat clearance as a design parameter and document it in the CAD job.

### 10.6 Wall thickness and small features

Check whether wall thickness, bosses, ribs, ledges, holes, gaps, and other small features are realistic for the intended FDM process.

Do not claim a feature is printable solely because FreeCAD accepts the geometry.

### 10.7 Assembly and fit

For multi-part designs explicitly verify:

- which part enters which part
- insertion direction
- insertion depth
- stop/shoulder location
- supporting ledge or rail
- clearance for insertion and removal
- whether the user can physically assemble it after printing

For example, if the requirement says the body enters an outer lid, the lid must not accidentally be designed to enter the body.

### 10.8 Example: enclosure with removable perforated plate

For an enclosure with a horizontal internal plate containing six Ø35 mm holes:

```text
             TOP / LID
          separate part
               ↓
      ┌─────────────────┐
      │                 │
      │  ○    ○    ○    │  ← removable plate
      │  ○    ○    ○    │     facing TOP
      │─────────────────│
      │                 │
      │      BODY       │
      │                 │
      └─────────────────┘
        ↑             ↑
        └── 1 mm ─────┘
            ledge
```

If a one-piece enclosure causes the top ceiling to float during normal FDM printing, do not force it. A better solution may be:

1. print the body open at the top;
2. print the perforated plate separately;
3. provide a 1 mm supporting ledge on all four sides of the body;
4. give the plate a small FDM clearance, initially around 0.3 mm per side;
5. print the top/lid as a separate part;
6. assemble the parts after printing.

The six holes remain in the horizontal plate and face upward in the assembled design. They must not accidentally become holes in the enclosure side walls.

---

## 11. Important CAD design lesson: hole placement

One of the recent real cases exposed an important bug: using fixed percentage positions for large holes can cause requested circles to overlap.

For a plate with six Ø35 mm holes in a 3×2 pattern, hole centers must be calculated from the actual plate dimensions and requested hole diameter, with validation that circles do not overlap.

For the 120 × 85 mm plate and Ø35 mm holes, the corrected X centers were:

```text
22.5 mm
60.0 mm
97.5 mm
```

The Y centers were:

```text
25.0 mm
60.0 mm
```

This produces six complete circular holes without overlap.

General rule:

**Never hard-code hole positions in a way that ignores requested diameter and available plate dimensions.**

---

## 12. Real Use Cases

Successful, verified real-world CAD jobs should be documented under the dedicated Real Use Cases workspace:

`docs/real-use-cases`

A case should ideally contain the prompt/specification and the resulting artifact or images. Failed attempts and useful iterations can also be documented when they teach an engineering or printability lesson.

The objective is to demonstrate:

**Prompt → CAD → Printability → STL/STEP → Real print → Result.**

---

## 13. Final assistant behavior

Before declaring a CAD job successful, ask internally:

1. Is the geometry what the user requested?
2. Are dimensions and feature positions correct?
3. Are mating parts oriented correctly?
4. Can the intended printer actually manufacture the geometry?
5. Are there floating surfaces or large overhangs?
6. Is support required, and if so, can it be removed easily?
7. Should the design be split into separate printable parts?
8. Are clearances realistic for FDM?
9. Can the printed parts actually be assembled?
10. Has the real result been inspected or verified?

If any answer is uncertain, do not silently assume success. State the risk and resolve it before treating the design as print-ready.

The core philosophy is:

> **Do not stop at “the CAD looks right.” Make sure the design can actually be printed, assembled, and used.**
