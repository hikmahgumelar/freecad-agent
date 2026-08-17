# Real Use Case: Large Enclosure with Internal Hole Plate

This example shows a practical FreeCAD generation workflow: describe the enclosure in natural language, send the specification to FreeCAD Agent, and obtain a FreeCAD CAD result.

## Prompt

Create an enclosure with:

- Body: 120 mm length × 85 mm width × 130 mm height
- Wall thickness: 1 mm
- Bottom thickness: 1 mm
- Internal horizontal plate at 70 mm from the bottom
- Plate thickness: 1 mm
- Plate attached to all four enclosure sides
- Six holes, diameter 35 mm
- Hole pattern: 3 columns × 2 rows
- Holes face upward (TOP)
- Holes must be complete, circular, and must not overlap
- Lid is an outer cap
- Body must enter inside the lid
- Lid insertion depth: 60 mm
- Lid clearance: 0.2 mm per side
- Lid wall thickness: 1 mm

## Result

The generated model contains three CAD objects:

- `LargeBoxBase` — enclosure body
- `InternalTopPlate` — horizontal internal plate with six Ø35 mm holes
- `LargeBoxLid` — removable outer cap

The generation job was completed successfully as `CAD-035`.

The verified result was visually inspected in FreeCAD: the lid covers the body externally, while the perforated plate is horizontal inside the enclosure and attached to all four sides.

## Files / Images


**Place the final FreeCAD screenshot here.**

### Cover (Large Box Lid)
<img width="1920" height="1049" alt="image" src="https://github.com/user-attachments/assets/22092fd7-65bd-4a9c-a211-723721d944bb" />


### Cover (Large Box Base and Internal Top Plate with six Ø35 Holes )
<img width="1920" height="1049" alt="image" src="https://github.com/user-attachments/assets/671a4888-4b09-42fc-ace3-c035cbad64e5" />


## Why this example matters

The important part of this use case is that the design starts from a natural-language specification instead of manually rebuilding the enclosure from scratch in CAD. The hole placement logic also validates the available plate dimensions against the requested hole diameter so the 3×2 Ø35 mm pattern does not produce overlapping circles.

See the main project documentation for setup and execution instructions.
