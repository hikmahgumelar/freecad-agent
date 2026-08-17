# GPT FreeCAD Agent Skill

## Purpose

This document defines the workflow GPT should follow when using FreeCAD Agent to turn natural-language CAD requirements into real, printable CAD artifacts.

The goal is not only to generate correct geometry. Every design must also be evaluated from a real 3D-printing and assembly perspective before it is considered successful.

## Core Principle

When the user asks to create, modify, or print a CAD design, do not stop at visualization or a sketch.

The expected workflow is:

```text
Natural-language prompt
        ↓
Requirement interpretation
        ↓
CAD geometry
        ↓
Printability review
        ↓
Manufacturing / assembly review
        ↓
STL / STEP / FCStd
        ↓
3D print
        ↓
Physical assembly verification
```

A generated sketch or conceptual image is not considered the final result when the user is asking for a real CAD artifact.

## Mandatory Printability Check

Before declaring a CAD job ready for printing, evaluate the design from the printer's point of view.

Check at minimum:

1. Print orientation
2. Overhangs
3. Floating geometry
4. Bridges
5. Support requirements
6. Support removal difficulty
7. Wall thickness
8. Small features and holes
9. Clearance between mating parts
10. Assembly direction
11. Whether parts should be separated for printing
12. Whether the geometry can realistically be manufactured with the intended FDM process

If a design has a likely print failure, identify it before the job is considered successful.

## Support Strategy

Do not automatically add permanent support geometry to the CAD model.

First determine whether the geometry can be changed to reduce or eliminate support requirements.

Preferred order:

1. Change print orientation if practical.
2. Split the design into printable parts if appropriate.
3. Modify geometry using chamfers, gradual transitions, ledges, ribs, or other FDM-friendly features.
4. If support is still necessary, let the slicer generate temporary support whenever possible.
5. If support is unavoidable, prefer geometry and interfaces that make the support easy to remove.

Support should be treated as a manufacturing concern, not automatically as part of the permanent CAD geometry.

## Multi-Part Design Rule

If a design contains a large ceiling, internal platform, suspended plate, or other geometry that would require difficult support when printed as one piece, consider splitting it into separate printable parts.

For example:

```text
Body
  + removable internal plate
  + removable lid
```

The parts must then be designed with appropriate clearance and mechanical seating features.

## FDM Clearance Rule

Do not assume that two mating dimensions can be identical and still assemble correctly after FDM printing.

For sliding or removable parts, explicitly introduce clearance and document the assumed starting clearance.

Example:

```text
Body internal space: 118 × 83 mm
Plate nominal size: 117.4 × 82.4 mm
Starting clearance: 0.3 mm per side
```

The exact clearance is printer, material, nozzle, and slicer dependent. Treat it as a starting engineering parameter, not a universal guarantee.

## Internal Plate / Ledge Pattern

When an internal plate must be removable, a reliable pattern is:

```text
Body wall
┌─────────────────────┐
│ ┌─────────────────┐ │
│ │ removable plate│ │
│ └─────────────────┘ │
│  └── 1 mm ledge ──┘ │
└─────────────────────┘
```

The plate should:

- be a separate printable part;
- enter from the intended assembly direction;
- rest on a ledge or support surface;
- have clearance from the surrounding wall;
- remain removable unless the user explicitly requests permanent attachment.

A ledge around all relevant sides is preferred over isolated support points when stability is important.

## Lid / Top Rule

For enclosures, explicitly determine whether the lid is:

- an inner plug;
- an outer cap; or
- a separate top plate.

Do not infer the direction of fit from the word "lid" alone.

If the user says the body must enter the lid, the lid is an outer cap and its internal dimensions must be larger than the body dimensions, with appropriate clearance.

If the top would create a large unsupported ceiling during FDM printing, consider making the top a separate printable part.

## Example: Printable Enclosure Workflow

For an enclosure with an internal perforated plate:

```text
                removable TOP
                      ↓
          ┌────────────────────┐
          │                    │
          └────────────────────┘

          ┌────────────────────┐
          │ ○  ○  ○            │
          │ ○  ○  ○            │ ← removable plate
          └────────────────────┘
             ↑            ↑
          ledge         ledge

          │                  │
          │       BODY       │
          │                  │
          └──────────────────┘
```

The plate is printed separately and inserted into the body. The top is also printed separately if doing so avoids a large unsupported ceiling.

## Requirement Clarification

Before generating CAD, resolve ambiguity in requirements such as:

- inside vs outside dimensions;
- lid insertion direction;
- whether a plate is horizontal or vertical;
- whether holes face TOP or a side;
- whether a part must be removable;
- whether dimensions include wall thickness;
- whether the user wants a one-piece or multi-part print.

If the requirement is clear, proceed without unnecessary questions.

## CAD Result vs Visualization

When the user asks for a CAD job, the final deliverable should be the actual CAD artifact or job result.

Do not substitute:

- an AI sketch;
- a conceptual rendering;
- a visual mockup;
- a dimension illustration;

for the requested CAD result.

Visualizations can be used to confirm interpretation, but they are not the final engineering artifact.

## Real Use Case Documentation

When a CAD design is successfully created and verified, it can be documented as a Real Use Case.

The preferred structure is:

```text
docs/real_use_cases/
└── <case-name>/
    ├── PROMPT.md
    ├── README.md
    └── result/
        ├── images
        ├── STL
        └── STEP / FCStd when appropriate
```

Document the actual prompt, relevant iterations, final result, and physical print result when available.

Failures and design iterations are useful engineering evidence. If a first design fails because of printability, document the issue and the corrected design rather than hiding the iteration.

## Definition of Done

A CAD job should only be considered complete when:

- requirements are satisfied;
- geometry is internally consistent;
- mating parts have appropriate clearance;
- print orientation has been considered;
- overhangs and floating geometry have been reviewed;
- support requirements have been considered;
- assembly is physically plausible;
- the requested CAD artifact has been generated;
- and, when physically printed, the real result has been verified.

The target is:

**Prompt → CAD → Printability → Print → Assembly → Real Result.**
