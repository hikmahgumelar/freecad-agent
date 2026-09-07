# Cyberdeck Design Contract

## Status

**Draft — awaiting Product Owner approval**

## Core Mechanical Objective

The cyberdeck enclosure must prioritize a **compact overall form factor**.

Compactness is a first-class design requirement. The enclosure must not be made unnecessarily thick or oversized simply to accommodate components. Internal layout, stacking, mounting strategy, and mechanical packaging must be optimized instead.

## Hard Thickness Constraint

The final maximum overall case thickness is to be explicitly defined and approved in this contract before final CAD design.

Once approved, the maximum overall thickness is a **hard constraint**. The design must not exceed it. If the hardware does not fit, the internal arrangement must be redesigned rather than increasing the contracted maximum thickness.

## Current Physical Reference

The supplied 4-inch case STL is a reference for footprint/proportion only. Its measured overall envelope is approximately **99 × 66 × 26.4 mm**. This is **not** the final cyberdeck thickness requirement.

## Case Construction

The initial enclosure wall-thickness target is approximately **2.5 mm**, subject to printability and structural validation.

## Architecture Direction

The current concept consists of two main mechanical assemblies:

1. **Main chassis:** HyperPixel 4.0 Touch + Raspberry Pi Zero + rechargeable battery/power system in one enclosure.
2. **Keyboard module:** physical keyboard enclosed in its own thin protective case/module.

A sliding/rail mechanism for the keyboard is intentionally deferred until the basic two-assembly packaging is validated.

## Battery Packaging

The intended battery is a rechargeable BL-5C-class Li-ion battery. Battery placement must provide adequate mechanical clearance and must not allow the battery to be compressed, punctured, or pressed against exposed PCB components, GPIO/header pins, solder joints, or flex connections.

## Measurement Rule

Final CAD dimensions must be based on measured hardware, not visual estimates. The following must be measured before CAD freeze:

- HyperPixel outer dimensions and mounting locations
- HyperPixel + GPIO + Pi Zero stack height
- Pi Zero component envelope
- BL-5C physical dimensions and thickness
- Keyboard case/module dimensions
- Required clearances and assembly access

## Design Priority

When packaging conflicts occur, use this priority:

1. Safety and hardware protection
2. Contracted maximum thickness
3. Compact overall footprint
4. Serviceability and assembly
5. Structural integrity
6. Aesthetics

The contract is the source of truth for the mechanical CAD design.
