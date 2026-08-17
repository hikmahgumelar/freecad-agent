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

## 10. Important CAD design lesson: hole placement

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

The generator should validate the geometry before saving the `.FCStd` result.

---

## 11. Current verified real-use case

The first major Real Use Case is:

**AI-Generated Enclosure Box — 6-Hole Internal Plate & Outer Cover**

Requirements:

- Body: 120 mm length
- Body: 85 mm width
- Body: 130 mm height
- Wall thickness: 1 mm
- Bottom thickness: 1 mm
- Horizontal internal plate at Z=70 mm
- Plate thickness: 1 mm
- Plate attached to all four sides
- Six Ø35 mm holes
- Hole pattern: 3 columns × 2 rows
- Holes face TOP
- Holes are complete circles and do not overlap
- Lid is an outer cap
- Body enters inside the lid
- Lid insertion depth: 60 mm
- Lid wall thickness: 1 mm
- Practical fit clearance

The result contains these conceptual objects:

```text
LargeBoxBase
InternalTopPlate
LargeBoxLid
```

The result was visually inspected and accepted by the user as the correct design direction.

The STL was also sent to a 3D-print service for physical validation.

The final real-use-case documentation lives on the `docs/real-use-cases` branch until the user approves the PR.

---

## 12. Real Use Case documentation strategy

The project is intentionally trying to attract forks and collaborators.

The Real Use Case section should show that the project is not just an AI/CAD concept. It should demonstrate:

```text
Prompt
  ↓
AI interpretation
  ↓
CAD job
  ↓
FreeCAD model
  ↓
STL / slicer
  ↓
3D print
```

Each Real Use Case should contain, where available:

```text
real_use_case/<case-name>/
├── README.md
├── PROMPT.md
└── result/
    └── <job-result>.json
```

Images should be added by the project owner when the final screenshots/physical results are available.

The user wants the main README to have a section titled:

`Real Use Case`

with numbered, clickable case titles. Example:

`1. AI-Generated Enclosure Box — 6-Hole Internal Plate & Outer Cover`

Clicking the title should open the corresponding Real Use Case directory, where readers can see the full prompting and result.

The user will provide the final images. Do not invent or replace them with generated sketches.

---

## 13. README positioning / project goal

The README is intended to make people want to fork the project.

Core message:

**Prompt → CAD → 3D Print.**

The project should demonstrate that a user can describe a design in natural language and get a real FreeCAD result instead of manually rebuilding the geometry from scratch.

The README should emphasize:

- real CAD execution
- natural-language design intent
- FreeCAD as the geometry source of truth
- local execution
- extensible AI/model layer
- real 3D-print workflows
- practical examples
- easy forking and experimentation

The Real Use Cases are especially important because they provide concrete evidence and invite people to add their own designs.

Potential future examples discussed:

1. Raspberry Pi enclosure.
2. Cyberdeck / phone-oriented case.
3. Additional community-generated CAD examples.

---

## 14. FreeCAD vs slicer presentation

FreeCAD is the design/geometry environment.

A slicer such as Bambu Studio, OrcaSlicer, or PrusaSlicer is used after STL export for print preparation and layer preview.

For documentation, both can be useful:

- FreeCAD screenshot: proves the CAD result and geometry.
- Slicer screenshot: proves the STL has moved into a real 3D-print preparation workflow.
- Physical print photo: strongest evidence that the pipeline reached manufacturing.

The user already sent the current STL to a print service. When the physical result is available, it should be added to the Real Use Case.

---

## 15. Do not confuse CAD execution with generated images

The user specifically values real CAD results.

When the task is to create a FreeCAD model, do not answer with a conceptual sketch as a substitute for the actual CAD workflow.

The expected artifact is a real `.FCStd` result generated through the FreeCAD listener.

A visual screenshot is evidence/documentation, not the CAD source itself.

---

## 16. Existing repository hygiene decisions

Keep these out of Git:

```text
bin/
lib/
lib64/
```

These are local runtime / virtual-environment directories.

The repository should contain source code, configuration examples, documentation, CAD job definitions/results where intentionally tracked, and other project artifacts—not a developer's local Python environment.

Do not accidentally re-add these directories during environment repair.

---

## 17. How a new ChatGPT session should start

When a new session starts, do this before proposing changes:

1. Read `GPT-FreeCad-Agent.md`.
2. Read the current `README.md`.
3. Inspect the current branch / PR state.
4. Inspect the relevant current source files before making implementation assumptions.
5. Check whether the user's requested work belongs on a new branch or is an explicit master maintenance change.
6. For CAD jobs, inspect the current listener and existing job schema.
7. Never assume a previous job succeeded just because the conversation says it did; verify repository state or ask the user for the current machine status when necessary.

Useful first questions when continuing an active CAD task:

```text
Is FreeCAD listener listening on 127.0.0.1:8765?
Is Supervisor RUNNING?
What is the current job ID/status?
Has the user already reviewed the generated model?
```

Do not restart a completed workflow from scratch merely because the session changed.

---

## 18. Safe operational checklist

Before sending a CAD job:

- [ ] Understand the exact geometry request.
- [ ] Confirm the intended action exists in the current listener.
- [ ] Choose a unique job ID.
- [ ] Write an explicit revision note.
- [ ] Keep experimental changes on a branch.

After sending:

- [ ] Confirm watchdog is running.
- [ ] Confirm listener is healthy.
- [ ] Wait for the job to be picked up.
- [ ] Check `running` → `completed` / `failed`.
- [ ] Inspect the actual CAD result.
- [ ] Validate geometry, not just status.
- [ ] Ask the user to review visual output.

Before merging documentation:

- [ ] User reviewed the result.
- [ ] Real Use Case prompt is included.
- [ ] Result metadata is included.
- [ ] Final images are added or intentionally left as placeholders.
- [ ] Main README links to the Real Use Case.
- [ ] User explicitly agrees to merge.

---

## 19. Current state at handoff

At the time this document was created:

- The FreeCAD Agent repository is active.
- The watchdog architecture is operational.
- FreeCAD listener uses `127.0.0.1:8765`.
- Supervisor is used for long-running watchdog operation on the user's Debian machine.
- Python 3 is used for the watchdog environment.
- The virtual environment is intentionally excluded from Git.
- The first major Real Use Case is the 120×85×130 mm enclosure with a 3×2 pattern of Ø35 mm holes and an outer lid.
- The user has visually accepted the CAD result.
- The STL has been sent for printing.
- Real Use Case documentation is being prepared on `docs/real-use-cases` and should not be merged until the user approves.

This file itself belongs on `master` so a future session can load it immediately.

---

## 20. Golden rule

The assistant should always preserve the project's core loop:

```text
USER INTENT
    ↓
AI / PROMPT
    ↓
STRUCTURED CAD JOB
    ↓
GITHUB QUEUE
    ↓
WATCHDOG
    ↓
FREECAD LISTENER
    ↓
REAL FREECAD GEOMETRY
    ↓
INSPECTION / USER REVIEW
    ↓
STL / STEP
    ↓
3D PRINT
    ↓
REAL USE CASE
    ↓
COMMUNITY / FORKS / COLLABORATION
```

The objective is not merely to generate CAD code. The objective is to make **natural-language-driven, reproducible, inspectable, real-world FreeCAD workflows** that other people can fork and extend.