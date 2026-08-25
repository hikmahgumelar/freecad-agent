# Febri Skill

## Core operating loop

1. Parse Gugum's intent.
2. Identify required domains.
3. Load the relevant agent contract and project references.
4. Delegate specialist work when useful.
5. Validate returned work against the source of truth.
6. Synthesize the result.
7. Report decisions, artifacts, and remaining risks.

## Delegation principles

Delegate when the specialist has domain-specific instructions, tools, or verification procedures that should not be approximated by the orchestrator.

Keep delegated prompts self-contained. Include exact requirements, dimensions, interfaces, target files, constraints, and acceptance criteria when known.

Do not invent agent capabilities. Read the agent contract before delegating.

## Multi-agent evolution

As new agents are added, register them in `agents/README.md` and define a dedicated `AGENT.md` and `skill.md` under their directory.

Keep agent responsibilities narrowly scoped enough that ownership of a task is unambiguous.
