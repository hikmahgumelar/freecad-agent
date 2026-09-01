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

## 0. Mandatory new-session bootstrap

When a new ChatGPT session is started for this project and the session has access to the `freecad-agent` GitHub repository, the **first project action must be to load/read `GPT-FreeCad-Agent.md` from the repository**.

Do not ask the user to paste the repository code or repeat the project history before doing this.

Use the repository handoff document as the primary session bootstrap source. After loading it:

1. Read the current session checkpoint.
2. Inspect the current GitHub job state relevant to that checkpoint.
3. Inspect the current implementation files before assuming an action is supported.
4. Continue from the documented state instead of restarting the project explanation.
5. Only ask the user for additional code/access if the repository cannot actually be accessed or the required file/state is unavailable.

The expected first user instruction in a new session may simply be:

> **“Lanjut FreeCAD Agent.”**

The assistant should then proactively load `GPT-FreeCad-Agent.md` and resume from its checkpoint.

If repository access is available, a response such as “please send the latest code or give me repository access” is incorrect because the repository is already the source of truth for the session handoff.

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

## 13. Current Session Checkpoint — 2026-09-01

This is the newest handoff checkpoint. **Read this before the older 2026-08-20
checkpoint below.** The active work is now **CAD-059 Golden Reference Snap-In**
(ESP32-C3 Super Mini), not the Medicine Box.

### CAD-059 status

Snap/button/cover tasks are **code-complete and locked** in
`freecad/freecad_agent_listener.py` (committed to `master`: `808a1ab`,
`71de339`) via the reusable `agent/features/flexure_button.py` module:

* S-02 U-cut = **0.50 mm** — listener guards `button_slot_width != 0.5`.
* S-03 rear bridge = **1.00 mm** — listener guards `button_rear_bridge != 1.0`.
* S-04 actuator pad at **inner base of U** via `FlexureButton.pad_origin`;
  size locked `2.0 x 2.0 x 0.75`.
* S-05 island preserved **2 x 7 mm**, no capsule / no raised head.
* B-01 USB-C centered: `center_x = outer_w / 2.0`; BOOT/RESET mirrored about
  the same center via `FlexureButton.mirrored(center_x)`.
* C-01 cover overlaps body with `skirt_h`, preserving `cover_clear = 0.20 mm`.

Pure-logic tests on `flexure_button.py` pass (slot/bridge/island values, pad
centering at base of U, symmetric mirroring, invalid-input guards). Real
`.FCStd` geometry is **not yet verified** — that is V-01.

The full task/geometry contract lives in `state-cad-059.md`. Read it before
touching CAD-059 geometry.

### Only V-01 remains

Run validation job **CAD-061** (`cad/jobs/CAD-061.json`, status `pending`,
`create_snapfit_case`) against a live FreeCAD listener, then inspect the real
`.FCStd` (recompute pass, 2 parts BottomCase+TopCover, U-cut 0.5, pad at base,
USB centered, BOOT/RESET symmetric, cover seated) and record PASS/FAIL.

### V-01 PASSED (2026-09-01) + geometry fixes

Live-inspected the generated `ESP32C3SnapFitCaseV4`: cover fully seats
(TopCover z[0.80..6.40] over 5.20 mm body), USB-C symmetric (left_gap =
right_gap = 5.45 mm), BOOT/RESET inside the case and symmetric about the
centerline. Three reported defects were fixed:

* Cover half-seated → `skirt_h = body_h - cover_lip` (default lip 0.8 mm),
  guarded so the skirt always captures the snap bosses.
* Buttons at the case edge → `button_pair_center_to_center` corrected 20.0 →
  8.8, plus a listener guard that rejects any spacing pushing the flexure
  U-slots into the walls.
* Off-center USB was old geometry; current code centers USB on `outer_w/2`.

Follow-up: **CAD-062** is a fresh visual-review job with the corrected params
(spacing 8.8, cover_lip 0.8) so the result can be opened and inspected in
FreeCAD. Open minor item: `TopCover` had `solids=3` (pads attached but not
fully fused) — cosmetic/printability only, geometry is correct.

### Live blocker: listener not bound

`.gitignore` in this checkout is `*` (repo sits inside a venv), so tracked
files must be committed with `git add -f`. Push to `master` triggers the
Supervisor watchdog to `pull --ff-only` + `execv()` restart and then pick up
pending jobs — this is the normal delivery path for CAD-059 work.

FreeCAD may be running while the listener is still **not** bound on
`127.0.0.1:8765`. This is usually `from agent.features import FlexureButton`
failing in the FreeCAD interpreter (`No module named 'agent'`). Before starting
the listener, run in the FreeCAD Python console:

```python
import sys
sys.path.insert(0, "/Users/gugum/projectx/freecad-agent")
```

then bootstrap the listener and confirm `listening on 127.0.0.1:8765`. A
`Connection refused` job result is an environment failure, not a geometry
failure — never record V-01 PASS from it.

---

## 13-legacy. Session Checkpoint — 2026-08-20

This section is the primary handoff checkpoint for the next ChatGPT session. **Read this section before continuing any CAD work.**

### Medicine Box V3 — agreed design contract

Medicine Box is a 3-part printable design:

1. **Body**
2. **Plate**
3. **Cover**

Current agreed requirements:

- Original nominal footprint: **120 mm length × 85 mm width**.
- Full Medicine Box body height: **130 mm** unless a future variant explicitly changes height.
- Body, plate, and cover structural thickness: **3 mm**.
- The 3 mm wall/thickness is added **outward**, so the functional/internal space is not reduced just because wall thickness changes from 1 mm to 3 mm.
- Plate: **6 holes, Ø35 mm, 3 columns × 2 rows**, horizontal and facing TOP.
- Plate is a separate printable part.
- Body has a continuous internal supporting ledge on all four sides for the plate.
- Plate must enter the Body from the top and descend until it rests on the internal Body ledge.
- Body must enter the Cover; **Body goes inside Cover, never the reverse**.
- For the full Medicine Box, the Cover insertion/depth requirement is **60 mm**.
- Mating interfaces must be snug/functional: **not too tight and not too loose**.
- Initial FDM fit-test clearance target is approximately **0.3 mm per side**. This is a starting design parameter, not a guarantee for every printer.
- Printability must be checked before calling the design ready: orientation, overhangs, floating geometry, support, part separation, clearance, assembly, and actual print validation.

### Smoke-Test Box — current reference design

The Smoke-Test Box is a smaller-height reference used to validate the mating geometry before generating the full Medicine Box V3.

The agreed Smoke-Test dimensions/intent are:

- Body height: **50 mm**.
- Cover height: **40 mm**.
- Body wall: **3 mm**, added outward.
- Cover wall: **3 mm**, added outward.
- Plate thickness: **3 mm**.
- Cover top thickness: **3 mm**.
- Plate remains the same functional reference plate: **117.6 × 82.6 mm, 6 × Ø35 mm, 3×2**.
- Initial plate/body clearance target: **0.3 mm per side**.
- Initial body/cover clearance target: **0.3 mm per side**.
- Plate must fit into Body and rest on the internal ledge.
- Body must fit into Cover.
- The Smoke-Test Box is the reference for future Medicine Box variants; future variants should keep the same footprint/fit logic and primarily change height unless explicitly specified otherwise.
- Cover height is 40 mm total. With a 3 mm cover top, the effective cavity/insertion depth is **37 mm** if the 40 mm value is interpreted as total cover height. Do not silently reinterpret this; if the user changes the cover-depth requirement, update the spec explicitly.

### Current CAD job state

**CAD-050** was created for `create_smoke_test_box` with the Smoke-Test requirements above, but the execution **failed** because the currently running watchdog/listener reported:

```text
Unsupported action: create_smoke_test_box
```

Therefore **Smoke-Test Box has NOT been successfully generated yet**. Do not tell the user it passed or that an `.FCStd` result exists.

The immediate next engineering task is:

1. Inspect the actual deployed watchdog/listener source and make sure `create_smoke_test_box` is supported end-to-end.
2. Ensure the FreeCAD-side implementation creates the three separate printable parts: Body, Plate, Cover.
3. Validate the two mating interfaces geometrically:
   - Plate → Body → rests on ledge.
   - Body → Cover.
4. Validate print orientation and support requirements.
5. Create a new/revised CAD job rather than pretending CAD-050 succeeded.
6. After the job completes, inspect the actual `.FCStd` result and report PASS/FAIL with evidence.

Do not reuse CAD-050 as a successful result; it is a failed historical execution.

### Important recent implementation lesson

A previous attempt tried to submit a Smoke-Test Body with outer dimensions 120 × 85 mm and 3 mm walls while keeping the old internal plate size. That was correctly recognized as invalid because increasing the wall inward would shrink the internal space and prevent the plate from fitting.

The correct design principle is:

**Keep the functional/internal dimensions, and add the 3 mm material outward.**

This principle must be preserved in Medicine Box V3 and its Smoke-Test reference.

### Session resume instruction

When a new ChatGPT session starts, do not reconstruct the Medicine Box requirements from memory. Read this checkpoint first, inspect the current GitHub job status/source, and continue from the **CAD-050 failed / action-support-fix** state.

Do not jump directly to Medicine Box V3. The Smoke-Test must pass first.

---

## 14. Final assistant behavior

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
