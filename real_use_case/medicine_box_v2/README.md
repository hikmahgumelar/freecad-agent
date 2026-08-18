# Medicine Box v2 — Real Use Case

This real case documents the current medicine-box result produced through the FreeCAD Agent pipeline.

The design is intentionally split into three independent FreeCAD documents so each printable component can be inspected, sliced, and printed independently:

- `medicine-box-cover-v2.FCStd` — cover, 122.5 × 87.5 × 61 mm. The closed face is oriented down toward the print bed and the opening faces up. The body inserts into the cover by 60 mm with 0.25 mm clearance per side.
- `medicine-box-plate-6holes-v2.FCStd` — plate, 117.6 × 82.6 × 1 mm, with six Ø35 mm holes in a 3 × 2 pattern. The plate is intended to print flat.
- `medicine-box-body-v2.FCStd` — body, 120 × 85 × 130 mm, with 1 mm wall and bottom plus an internal 3 mm wide × 1 mm thick ledge at Z=70 mm for the plate. The body is intended to print upright.

The three documents are independent: a cover file contains only the cover, a plate file contains only the plate, and a body file contains only the body.

## Assembly concept

The plate sits on the internal ledge inside the body. The body then inserts into the cover from the open side. The cover is a sleeve-style component rather than the plate support.

## Print readiness

The current geometry is designed for FDM printing with the intended orientations above. No support is required by design. Final slicer validation remains printer/material dependent and should verify wall count, first-layer adhesion, dimensional tolerance, and actual fit after printing.

## Evidence

Add FreeCAD screenshots and/or photographs of the generated parts under `result/` for the real-case record.
