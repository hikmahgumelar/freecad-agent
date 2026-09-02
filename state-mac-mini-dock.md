# STATE — Mac Mini M4 Dock

**Branch:** `feature/mac-mini-m4-case` (NOT master — user requested this stays off master)
**State:** Dock v1 built and rendered; awaiting user review of refinements.

## Goal

A 3D-printable **docking base** for the Apple Mac mini M4 (2024) — a Satechi-style
"Stand & Hub" replacement. The Mac mini sits **on top** of the dock in a shallow
recess; the dock adds internal volume (M.2 NVMe SSD bay), front port slot, rear
cable pass-through, bottom power-button access, and vents.

Not a case that encloses the mini — a base it sits on.

## Device reference (Apple official, model A3238)

* Footprint **127 × 127 mm**, height **50 mm**, rounded aluminum cuboid.
* Power button is on the **bottom-rear** of the mini (needs an access hole).
* M4 intakes air from the **bottom perimeter** (vents matter).

## Implementation

Listener `freecad/freecad_agent_listener.py` — action `create_mac_mini_dock`
(function `_create_mac_mini_dock`). Two earlier related builders also exist:
`create_mac_mini_case` (an enclosing case — superseded by the dock concept).

Job: `cad/jobs/CAD-065.json`. Output FCStd:
`cad/output/mac-mini-m4-dock.FCStd`.

### Dock v1 parameters (CAD-065)

* footprint 131.8 × 131.8 mm (device + clearance 0.4 + recess wall 2.0 each side)
* dock_height 35 mm, top_thickness 3 mm, wall 2.4 mm, corner_radius 8 mm
* recess_depth 2 mm (locates the mini)
* SSD bay: M.2 2280, 80 × 22 mm guide rails
* front_port_slot 70 × 12 mm; rear_cable 90 × 16 mm
* power-button hole r=6 mm, inset 18 mm from rear
* deck + bottom vents (Ø5 mm, 5 mm gap); bottom plate 2.4 mm

### Build result (via live listener, verified)

* `MacMiniDockBody`: solids=2, faces=169, bbox x/y[0..131.8] z[0..35.0]
* `MacMiniDockPlate`: solids=1, faces=131, z[-2.4..0]
* Renders: `kesalahan/macdock_iso.png`, `macdock_top.png`, `macdock_front.png`

## Open items for next session

1. `MacMiniDockBody` reports **solids=2** — the internal SSD guide rails are
   fused but not merged into one solid. Tighten to a single solid for clean
   printability.
2. Vent holes currently also appear inside the top recess (where the mini sits).
   Decide: keep (helps bottom-intake airflow) or clear the recess band.
3. No screw bosses yet to fasten the bottom plate — add if a captive plate is
   wanted.
4. Rear cable pass-through not framed in the current renders — verify visually.
5. Record nothing to `master`; the dock lives only on this branch.

## Listener tooling note

The FreeCAD listener now supports `reload` and `render_view` over TCP, so code
changes can be applied and screenshots captured **without restarting FreeCAD**
(reload returned "code swapped in place" this session). If `reload` ever reports
the sentinel missing, fall back to a FreeCAD restart.

## Master status note

An earlier Mac mini *case* commit (`90a8aef`, action `create_mac_mini_case`)
was pushed to master BEFORE the user asked to keep this work on a branch. It is
still on master (untouched). Decision pending: leave it, or revert master to
keep the Mac mini work branch-only.
