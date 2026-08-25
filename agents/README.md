# Agent System

This directory defines the persistent contracts, skills, references, and orchestration rules for the ChatGPT agents working with Gugum.

## Agents

- `febri/` — Orchestrator. Coordinates specialist agents, decomposes tasks, routes work, reviews returned results, and reports to Gugum.
- `agung/` — CAD and 3D-printing specialist. Owns FreeCAD-oriented CAD design, printability, fit, assembly, and CAD job preparation.

## Source of truth

Agent behavior must be grounded in the files under each agent directory. Project-specific technical references belong under `references/`.

The original FreeCAD operating manual is retained in the repository root as `Gpt-freecad-agent.md` and is referenced by Agung rather than duplicated.

## Important boundary

This agent system is separate from the application/runtime architecture of the FreeCAD Agent project. These files define AI roles and working contracts; they do not replace the FreeCAD watchdog, listener, GitHub CAD queue, or other runtime components described by the project documentation.
