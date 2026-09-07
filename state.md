# Cyberdeck Project State

## Project

Cyberdeck case project using the `freecad-agent` workflow.

The current hardware foundation is:

- Raspberry Pi Zero
- Pimoroni HyperPixel 4.0 Touch, 800×480, DPI interface
- Physical keyboard, intended to use a slide-out mechanism

The FreeCAD Agent handoff document remains the primary operating manual for the repository and its CAD workflow.

## Current Hardware State

The blue Raspberry Pi Zero protective case has been removed/dismantled.

The HyperPixel 4.0 is intended to mount directly to the Pi Zero GPIO header. Do not force the boards together if the GPIO alignment is not correct.

Power for the initial HyperPixel test should be supplied through the Pi Zero `PWR IN` micro-USB port; the HyperPixel receives power through the GPIO connection.

## Immediate Next Actions

1. Measure the case/hardware dimensions needed for the cyberdeck enclosure.
2. Measure and document the keyboard dimensions and mechanical requirements for the slide mechanism.

## Design Contract Constraint

Before CAD design, create and approve the cyberdeck design contract.

The contract must define the maximum allowed overall case thickness. The enclosure design must not exceed that maximum thickness. Thickness is a hard constraint and must not be increased simply to accommodate the hardware; layout and mechanical design must be adapted to remain within the contract.

The contract is the source of truth for the cyberdeck mechanical design.

## Design Direction

The cyberdeck should use a compact enclosure around the HyperPixel 4.0 + Pi Zero assembly, with the keyboard mounted as a slide-out component.

Do not finalize CAD dimensions from guesses. Use measured hardware dimensions as the reference geometry.

Before generating the final case, define:

- HyperPixel/LCD outer dimensions and mounting-hole locations
- Pi Zero envelope and GPIO stack height
- Keyboard outer dimensions and thickness
- Keyboard slide travel
- Rail/guide geometry
- USB/power/other port cutouts
- Ventilation
- Wall thickness
- FDM clearances
- Assembly and removal direction
- Maximum overall thickness from the approved contract

## Current Status

**Phase:** Hardware preparation / measurement

**CAD:** Not started for the final cyberdeck enclosure

**Current checkpoint:** Blue Pi Zero case removed. Next: establish/approve the contract, then collect precise hardware and keyboard measurements before CAD geometry is finalized.

## Session Note

Do not restart the cyberdeck design from scratch in the next session. Read this `state.md` and `GPT-FreeCad-Agent.md` first, then continue from the current measurement/contract checkpoint.
