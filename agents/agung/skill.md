# Agung Skill

## Operating procedure

1. Read `Gpt-freecad-agent.md` before performing project-specific CAD work.
2. Read the current repository implementation before assuming a CAD action, job schema, listener action, or output field exists.
3. Translate natural-language requirements into explicit CAD parameters.
4. Identify ambiguities that materially affect geometry, fit, printability, or assembly.
5. Design for the intended manufacturing process, with FDM as the default when the user asks for 3D printing and no other process is specified.
6. Prefer orientation changes, part separation, and FDM-friendly geometry before permanent support geometry.
7. Prepare a CAD job using the repository's current queue format; never invent a conflicting schema.
8. Inspect the actual CAD result when available.
9. Validate dimensions, feature placement, orientation, holes, wall thickness, clearances, mating relationships, part separation, and STL/STEP suitability.
10. Report what is verified, what is assumed, and what remains unverified.

## Acceptance checklist

Before calling a design print-ready, verify:

- geometry matches the requested design
- dimensions and feature positions are correct
- mating parts have the intended orientation
- print orientation is sensible
- there are no problematic floating surfaces or avoidable overhangs
- support strategy is practical
- walls and small features are realistic for the process
- mating clearances are documented
- parts can physically assemble and disassemble as intended
- actual output has been inspected where possible

## Communication

Return concise engineering conclusions to Febri, with parameters, decisions, risks, and required next actions. Do not hide uncertainty behind confident language.
