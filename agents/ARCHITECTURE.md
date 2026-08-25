# Agent Architecture

## Purpose

This directory is the persistent home for AI-agent contracts and skills used with the FreeCAD Agent project.

## Layers

### Orchestrator

`febri/` defines the top-level coordinator.

Febri owns task decomposition, specialist selection, context handoff, result evaluation, and communication back to Gugum.

### Specialists

Each specialist owns one domain and must have:

- `AGENT.md` — identity, authority, responsibilities, boundaries
- `skill.md` — operating procedure and acceptance criteria
- `references/` — optional domain-specific documents

### Project runtime

The AI agent layer does not replace the FreeCAD runtime. The runtime remains governed by the project documentation, including the watchdog, FreeCAD listener, GitHub CAD queue, and job lifecycle.

## Current topology

```text
Gugum
  |
  v
Febri (Orchestrator)
  |
  +----> Agung (CAD / 3D Printing)
  |
  +----> future specialists
```

## Change policy

New agents should be added on a feature branch and reviewed before merging to `master`.

Do not silently change an agent's domain boundaries. Update its `AGENT.md`, `skill.md`, and this architecture document when the role changes materially.
