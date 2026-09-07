# Cyberdeck Project State

## Project

Cyberdeck case project using the `freecad-agent` workflow.

The current hardware foundation is:

- Raspberry Pi Zero
- Pimoroni HyperPixel 4.0 Touch, 800×480, DPI interface
- Physical keyboard, intended to use a separate keyboard case/module
- Rechargeable BL-5C-class Li-ion battery as the current battery direction

The FreeCAD Agent handoff document remains the primary operating manual for the repository and its CAD workflow.

## Current Hardware State

The blue Raspberry Pi Zero protective case has been removed/dismantled.

The HyperPixel 4.0 is intended to mount directly to the Pi Zero GPIO header. Do not force the boards together if the GPIO alignment is not correct.

Power for the initial HyperPixel test should be supplied through the Pi Zero `PWR IN` micro-USB port; the HyperPixel receives power through the GPIO connection.

## Design Contract

A draft contract has now been created at `CYBERDECK-DESIGN-CONTRACT.md` on this branch.

The primary mechanical objective is **compactness**.

The maximum overall case thickness will be explicitly defined and approved in the contract. Once approved, it is a hard constraint. The enclosure must not be made thicker merely to accommodate hardware; internal layout and mechanical packaging must be redesigned instead.

The current wall-thickness target is approximately **2.5 mm**, subject to printability and structural validation.

The supplied 4-inch case STL is only a physical footprint/proportion reference at approximately **99 × 66 × 26.4 mm overall**. Its 26.4 mm envelope is not the final thickness target.

## Design Direction

The current concept uses two main mechanical assemblies:

1. **Main chassis:** HyperPixel 4.0 Touch + Raspberry Pi Zero + rechargeable battery/power system in one enclosure.
2. **Keyboard module:** physical keyboard enclosed in its own thin protective case/module.

The keyboard sliding/rail mechanism is intentionally deferred until the basic two-assembly packaging is validated.

BL-5C battery placement must maintain safe mechanical clearance and must not compress or press the battery against exposed PCB components, GPIO/header pins, solder joints, or flex connections.

## Measurement Rule

Do not finalize CAD dimensions from guesses. Use measured hardware as the reference geometry.

Before CAD freeze, measure:

- HyperPixel outer dimensions and mounting-hole locations
- HyperPixel + GPIO + Pi Zero stack height
- Pi Zero component envelope
- BL-5C physical dimensions and thickness
- Keyboard case/module dimensions
- Required clearances and assembly access

## Immediate Next Actions

1. Approve/finalize the maximum overall thickness in the design contract.
2. Measure the HyperPixel/Pi Zero stack.
3. Measure the BL-5C battery.
4. Measure and document the keyboard and its intended separate case/module.
5. Only then begin final CAD packaging.

## Current Status

**Phase:** Contract + hardware preparation / measurement

**CAD:** Not started for the final cyberdeck enclosure

**Current checkpoint:** Blue Pi Zero case removed; compact two-assembly architecture selected; draft design contract created; precise hardware measurements are the next gate before CAD.

## Session Note

Do not restart the cyberdeck design from scratch in the next session. Read `state.md`, `CYBERDECK-DESIGN-CONTRACT.md`, and `GPT-FreeCad-Agent.md` first, then continue from the current contract/measurement checkpoint.
