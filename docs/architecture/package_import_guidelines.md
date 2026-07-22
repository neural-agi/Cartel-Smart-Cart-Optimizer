# Package Import Guidelines

Cartel's Cost Intelligence packages use explicit, acyclic imports.

Principles:

- `__init__.py` files expose only stable vocabulary or lightweight contracts.
- Concrete services are imported directly from their defining modules.
- Avoid package-level barrel exports that can create dependency cycles.
- Deterministic packages should prefer explicit imports over convenience exports.
- Dependency direction must remain acyclic across observation, context, evaluation, and orchestration layers.

Practical guidance:

- Import services from `*.service` modules where they are used.
- Import orchestrators from `*.orchestrator` modules where they are used.
- Keep package roots small and stable.
- If a package export introduces a cycle, remove the export rather than adding a shared abstraction.
- Add common helpers only after multiple concrete implementations prove the shared behavior is stable.
