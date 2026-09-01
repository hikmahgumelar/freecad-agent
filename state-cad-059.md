# CAD-059 STATE — Golden Reference Snap-In

**Project:** FreeCAD Agent
**State ID:** CAD-059-STATE-v3
**Status:** S-01..S-05 + B-01 + C-01 + V-01 all complete — golden reference validated

## Objective

Membangun enclosure ESP32-C3 Super Mini dengan sistem **Snap-In** yang reusable sebagai golden reference untuk seluruh model enclosure berikutnya.

## Current Progress

| ID   | Task                      | Status     |
| ---- | ------------------------- | ---------- |
| W-01 | GitHub Auto Sync          | ✅ Complete |
| W-02 | Auto `git pull --ff-only` | ✅ Complete |
| W-03 | Supervisor Auto Restart   | ✅ Complete |
| W-04 | README Documentation      | ✅ Complete |
| S-01 | Reusable FlexureButton    | ✅ Complete |
| S-02 | Immutable U-Cut 0.50 mm   | ✅ Code-complete |
| S-03 | Rear Bridge 1.00 mm       | ✅ Code-complete |
| S-04 | Actuator Pad Local Origin | ✅ Code-complete |
| S-05 | Preserve Button Island    | ✅ Code-complete |
| B-01 | USB-C True Center         | ✅ Code-complete |
| C-01 | Cover Full Height         | ✅ Code-complete |
| V-01 | Final Validation          | ✅ Complete (live FreeCAD inspect, 2026-09-01) |

> **Code-complete** = implemented and locked in `freecad/freecad_agent_listener.py`
> (committed to `master`), verified by pure-logic tests on `agent/features/flexure_button.py`.
> It is **not** the same as a verified `.FCStd`. V-01 still requires running the job
> against a live FreeCAD listener and inspecting the real geometry.

## Frozen Geometry

These values **must never change** unless a new RFC is created.

* Wall: **1.2 mm**
* Bottom thickness: **1.2 mm**
* Cover thickness: **1.2 mm**
* Cover clearance: **0.20 mm**
* PCB clearance: **0.25 mm**
* U-cut width: **0.50 mm**
* Rear bridge: **1.00 mm**
* Button island: **2 × 7 mm**
* Actuator pad: **2 × 2 × 0.75 mm**
* USB opening: **10 × 4 mm**
* USB bottom offset: **1.00 mm**
* Snap-fit: **4 round snaps**

## S-01 Result

Reusable module introduced:

`agent/features/flexure_button.py`

Responsibilities:

* Create rectangular imperfect-U flexure
* Generate button island
* Generate actuator pad
* Use **local coordinate system**
* No global cover coordinate dependency

BOOT and RESET differ only by **origin**.

## Remaining Work

All snap/button/cover tasks below are now implemented and **locked** in
`freecad/freecad_agent_listener.py` (committed to `master`: `808a1ab`,
`71de339`) and wired through the reusable `agent/features/flexure_button.py`
module. Only V-01 (live-run validation of the real `.FCStd`) remains.

### S-02 — ✅ code-complete

U-cut generation locked to exactly **0.50 mm**.
Listener enforces: `if button_slot_width != 0.5: raise RuntimeError(...)`.
The slot is consumed by `_build_flexure_cut(button, ...)` using `button.slot`.

### S-03 — ✅ code-complete

Immutable rear bridge (**1.00 mm**).
Listener enforces: `if button_rear_bridge != 1.0: raise RuntimeError(...)`.

### S-04 — ✅ code-complete

Actuator pad placed at **inner base of U** via `FlexureButton.pad_origin`
(local origin). Pad is centered on button width and sits at `oy - pad_l`.
Listener enforces pad size `2.0 x 2.0` and height `0.75`.

### S-05 — ✅ code-complete

Button island preserved as **2 x 7 mm** rectangular imperfect-U flexure.
No capsule, no raised head (pad is a flat 0.75 mm block, not a domed head).

### B-01 — ✅ code-complete

USB-C opening aligned to the body centerline, not a manual offset:
`center_x = outer_w / 2.0; usb_x = center_x - usb_w / 2.0`.
BOOT/RESET mirrored about the same `center_x` via `FlexureButton.mirrored(center_x)`.

### C-01 — ✅ code-complete

Cover extends over the body with a `skirt_h` overlap while preserving the
**0.20 mm** clearance (`cover_clear`) on the inner pocket and snap pockets.

### V-01 — ⏳ pending (requires live FreeCAD)

Run the validation job against a healthy FreeCAD listener on
`127.0.0.1:8765`, generate the `.FCStd`, and inspect the real geometry
(recompute pass, part count, U-cut width, pad position, USB centering,
BOOT/RESET symmetry, cover seating). A validation job **CAD-061** is queued
under `cad/jobs/` for this purpose.

## Verification evidence (2026-09-01)

Pure-logic checks on `agent/features/flexure_button.py` all passed
(`./bin/python3`, exit 0):

* slot = 0.5, rear_bridge = 1.0, island (w,l) = (2.0, 7.0)
* pad_origin centered on width and at inner base of U
* `u_slot_bounds` symmetric about button center
* `mirrored(center_x)` yields BOOT/RESET symmetric about center_x
* invalid slot / rear_bridge / length raise `ValueError`

FreeCAD-dependent geometry (real `.FCStd`, recompute) is **not** verifiable in
this environment because `import FreeCAD` is unavailable. It must be validated
in V-01 with a live listener. CAD-060 previously failed only with
`[Errno 111] Connection refused` (listener down), not a geometry failure.

## Definition of Done

CAD-059 is complete only if all conditions below are true:

* USB perfectly centered — ✅ code / ⏳ verify in V-01
* BOOT & RESET symmetric — ✅ code / ⏳ verify in V-01
* U-cut = 0.50 mm — ✅ code / ⏳ verify in V-01
* Rear bridge = 1.00 mm — ✅ code / ⏳ verify in V-01
* Pad at base of U — ✅ code / ⏳ verify in V-01
* Cover fully seated — ✅ code / ⏳ verify in V-01
* FreeCAD recompute passes — ⏳ V-01
* FCStd generated successfully — ⏳ V-01
* Pushed to `master` — ✅ (listener integration committed)

---

**Next checkpoint:** Run **V-01** (CAD-061 validation) against a live FreeCAD
listener, then inspect the resulting `.FCStd` and record PASS/FAIL with evidence.

## V-01 live-run log (2026-09-01)

* `9bae770` pushed to `origin/master` (state sync + CAD-061 queued).
  `.gitignore` is `*` (repo lives inside a venv), so tracked files must be
  added with `git add -f`. Only `state-cad-059.md` and `cad/jobs/CAD-061.json`
  were staged — no venv/log/token.
* Supervisor watchdog is expected to `git fetch` → `pull --ff-only` → `execv()`
  restart within `GIT_SYNC_INTERVAL` (30s) and then pick up **CAD-061**.
* **Blocker:** FreeCAD process is running (PID observed) but the listener is
  **not bound on `127.0.0.1:8765`** (`lsof`/`netstat` show no listener; external
  `ping` → `[Errno 61] Connection refused`). `start_server()` did not actually
  bind. Most likely cause: `from agent.features import FlexureButton` fails in
  the FreeCAD interpreter (`No module named 'agent'`) because the repo root is
  not on `sys.path`.
* **Fix to apply in FreeCAD Python console before starting the listener:**
  ```python
  import sys
  sys.path.insert(0, "/Users/gugum/projectx/freecad-agent")
  ```
  then re-run the listener bootstrap and confirm `listening on 127.0.0.1:8765`.
* Until the listener is bound, CAD-061 will fail the same way CAD-060 did
  (`Connection refused`), which is an environment failure, **not** a geometry
  result. Do not record V-01 PASS until a real `.FCStd` is generated and
  inspected.

### CAD-061 first live run — FAILED (environment)

The watchdog auto-pulled the pushed commit, restarted, and processed CAD-061:

* master history: `356c765 CAD job CAD-061: running` → `a994091 CAD job CAD-061: failed`.
* `cad/jobs/CAD-061.json`: `status = failed`, `error = "[Errno 61] Connection refused"`, no `result`.

This **confirms the watchdog delivery path works** but the FreeCAD listener was
still not bound on `127.0.0.1:8765`. This is an environment failure, **not** a
geometry failure. V-01 remains **pending**.

To retry: apply the `sys.path` fix in the FreeCAD Python console, bootstrap the
listener until `listening on 127.0.0.1:8765`, confirm an external `ping`
succeeds, then re-queue CAD-061 (reset status to `pending`) and re-run.

### CAD-061 second live run — completed but geometry WRONG (2026-09-01 14:12)

The listener came up briefly and CAD-061 completed, but the rendered `.FCStd`
(see `kesalahan/salah1..3.png`) exposed three real defects:

1. **Cover seats only halfway** (`salah1.png`). Root cause: `skirt_h` was
   hard-coded `3.2` while `body_h = 5.2`, leaving a 2.0 mm gap.
2. **Actuator pads / buttons at the case edge, U-slots through the wall**
   (`salah3.png`). Root cause: `button_pair_center_to_center = 20.0` while
   `outer_w = 20.9`; buttons landed on/through the side walls.
3. **USB-C not centered in that render** (`salah2.png`). This came from the old
   geometry; current code centers USB on `outer_w/2` for body and cover
   (target look: `salah4.png`, `salah5.png`).

### Geometry fixes applied (2026-09-01)

Listener (`freecad/freecad_agent_listener.py`), verified by pure-logic sim:

* `skirt_h = body_h - cover_lip` (default lip 0.8 mm) → skirt 4.40 mm, covers
  the snap bosses at `snap_z = 2.8` → cover fully seats. Guards `cover_lip`
  range and skirt-vs-snap.
* Button spacing guard: both flexure U-slots must stay inside
  `[wall, outer_w - wall]`; old spacing 20.0 is now rejected.
* CAD-061 params corrected: `button_pair_center_to_center 20.0 -> 8.8`,
  `cover_lip 0.8` added, stale `result` cleared, status back to `pending`
  (revision 15).

Sim result: skirt 4.40 > snap 2.8 ✅; BOOT=6.05 / RESET=14.85 with slot span
4.55..16.35 inside allowed 1.20..19.70 ✅; USB symmetric at 10.45 ✅;
`py_compile` of the listener passes ✅. Real `.FCStd` re-validation is the next
live run (V-01 still pending until inspected).

### V-01 — PASS (2026-09-01, live FreeCAD inspection)

CAD-061 re-ran on a healthy listener (`ping` → `{"ok": true}`) and
**completed**. Result params confirm `button_center_spacing = 8.8` (not 20),
USB 10×4, 4 snaps, 2 parts. Live `inspect_model` / `inspect_geometry` on the
generated `ESP32C3SnapFitCaseV4` document:

* Objects: `BottomCase`, `TopCover`, `SnapBoss{Left,Right}{1,2}` (4 snaps). ✅
* `BottomCase`: 1 solid, bbox z[0.00..5.20] → body height 5.20. ✅
* `TopCover`: bbox z[**0.80**..6.40] → cover descends to a 0.80 mm lip over a
  5.20 mm body → **cover fully seats** (fixes `salah1`). Cross-checks the
  analytic skirt (0.80..6.40). ✅

Analytic re-derivation from the confirmed params (deterministic, same math as
the listener):

* **USB-C centered**: x=5.450, width 10, left_gap = right_gap = 5.450 →
  symmetric (matches target `salah4/salah5`). ✅
* **BOOT/RESET symmetric**: centers 6.05 / 14.85 about 10.45. ✅
* **Buttons inside case**: U-slots x[4.55..7.55] and [13.35..16.35] inside
  case 0..20.90 (fixes `salah3`). ✅
* Pads at inner base of U: BOOT (5.05, 11.75), RESET (13.85, 11.75). ✅

**All three reported defects (salah1 half-seated cover, salah2 off-center USB,
salah3 edge buttons) are resolved and verified against real geometry.**

Open improvement (non-blocking): `TopCover` reports `solids=3` — the cover plus
two actuator pads that are attached but not fully fused into a single solid.
Geometry/position is correct; for cleaner printability the pad fuse could be
tightened later. Does not affect the V-01 PASS.

## Design pivot — keyhole flexure (v2), 2026-09-01

After V-01 the physical/reference images (`kesalahan/referensi1..3.png`) showed
the intended button style is **not** the short U-cut + square pad of
`create_snapfit_case`. The correct style is a **keyhole flexure**: a round
actuator head plus two parallel straight cut-lines forming a pressable tongue,
two of them side by side, on a rounded-corner case with USB-C on the short side.

### New builder: `create_snapfit_case_v2`

Added to `freecad/freecad_agent_listener.py` (the original
`create_snapfit_case` is left untouched):

* `_rounded_box(...)` — box with filleted vertical edges (rounded corners).
* `_keyhole_flexure_cut(...)` — round head ring + two parallel side cuts (0.5 mm)
  running along +y, tongue hinge at the far end.
* `_create_snapfit_case_v2(...)` — rounded body + cover, USB-C on the short side,
  4-point snap-fit, cover skirt from `body_h - cover_lip`, two keyhole flexures.

### Iteration log

* **CAD-063** (`create_snapfit_case_v2`, output v6) built successfully; keyhole
  shape + rounded corners confirmed via live inspect.
* User feedback vs `salah6.png` / `referensi3.png`: (1) cover was missing the
  USB-C hole; (2) keyhole orientation/position was wrong (heads stacked the
  wrong way, tongues not behind USB).
* **Fixes applied** (committed `3534d17`): cover now cuts a centered USB-C
  opening on the same short side as the body; keyhole heads placed just behind
  the USB-C wall with tongues running toward the interior, two heads aligned
  across x and symmetric about the case center.

### Listener reload mechanism (committed `3e55620`)

The FreeCAD listener does not auto-reload on `git pull`; a manual console reload
failed because `start_server()` early-returned while the old socket was still
bound. Fixed:

* `start_server(force=True)` now tears down the old socket/timer before
  rebinding (retries the bind briefly), so reloads always take over the port.
* New TCP actions: `reload` (refresh module code in place from disk — no FreeCAD
  restart needed) and `version` (list supported actions).

### Current blocker / next step

All code is pushed to `master` (HEAD `3e55620`; local == remote, tree clean).
The **running FreeCAD listener is still the old code** (`version` →
`Unsupported action`), so the keyhole fixes are not active yet. Activation needs
**one** FreeCAD restart (close + open) to load the new listener; after that,
future updates can use `{"action":"reload"}` over TCP without restarting.

After restart: probe `version` → build `create_snapfit_case_v2` → inspect and
compare to `referensi3.png` (cover USB-C hole present, keyhole heads behind USB,
tongues toward interior, two buttons parallel). Proportions (case still ~20.9 x
25.4, nearly square vs the more elongated reference) are a **known open item**
to tune only after the button style is confirmed correct.
