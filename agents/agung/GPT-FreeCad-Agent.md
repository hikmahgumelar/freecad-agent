# GPT-FreeCad-Agent

This file is a project-specific copy of the repository's `GPT-FreeCad-Agent.md` operating manual for the Agung agent.

Agung MUST read this file before performing FreeCAD Agent work.

The authoritative project document is the repository-root `GPT-FreeCad-Agent.md`. This copy is intentionally kept with Agung's agent package so the agent's required reference is explicit and self-contained.

When this copy is updated, it must remain synchronized with the repository-root document.

---

## Required behavior

1. Read this file before FreeCAD Agent work.
2. Treat its workflow, architecture, job lifecycle, printability rules, and validation rules as mandatory.
3. Inspect the current repository implementation before assuming a CAD action or job schema exists.
4. Never declare CAD work print-ready merely because FreeCAD accepted the geometry.
5. Validate dimensions, geometry, print orientation, overhangs, supports, wall thickness, clearances, assembly, and STL/STEP suitability.
6. Follow the repository's Git workflow and job-queue rules.
7. When the full technical detail is needed, consult the repository-root `GPT-FreeCad-Agent.md` and current implementation files.

## Source document

`/GPT-FreeCad-Agent.md`
