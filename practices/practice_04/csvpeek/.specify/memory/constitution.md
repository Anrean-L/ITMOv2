<!--
Sync Impact Report
Version change: unversioned template → 1.0.0
Modified principles: template placeholders replaced by initial principles
Added sections: Core Principles, Project Constraints, Development Workflow, Governance
Removed sections: none
Follow-up TODOs: none
Remove this report before committing the constitution.
-->
# csvpeek Constitution

## Core Principles

### I. Preserve Existing Behaviour

Changes MUST preserve the existing CSV CLI and its observable behaviour unless a change is
explicitly requested. Existing input handling, output, and error behaviour form the baseline
for review and regression tests.

### II. Minimal Dependencies and Simple Design

Implementations MUST use the Python standard library when it can meet the requirement.
Any external dependency MUST be justified by a concrete need and its alternatives considered.
Solutions MUST avoid unnecessary abstractions and choose the simplest design that meets the
requirements.

### III. Independent Business Logic and Agreed Contracts

Business logic MUST remain independent of the user interface and testable without it.
Before implementing a UI and backend interaction or changing its contract, the contract MUST
be defined and agreed: inputs, outputs, and error behaviour must be documented.

### IV. Test Success and Failure

Behaviour changes MUST include tests for relevant successful and erroneous scenarios.
Regression tests MUST cover existing behaviour affected by a change. Required project checks
MUST pass before a change is considered complete.

### V. Deterministic Results and Explicit Errors

For the same input and conditions, observable CLI results MUST be deterministic. Malformed
input and other failures MUST be reported explicitly and MUST NOT be silently ignored.

### VI. Preserve Agent Configuration

Existing agent configuration, including AGENTS.md, custom skills, MCP configuration, and hooks,
MUST be preserved. Changes to that configuration require an explicit request or authorization.

## Project Constraints

- Use Python 3.12 or later; application code belongs under `src/csvpeek/` and tests under `tests/`.
- Treat the existing nonempty project and its documented CLI behaviour as the starting point.
- Preserve the project's existing CSV analysis workflow, inspection requirements, and automatic
  verification hooks as documented in AGENTS.md.

## Development Workflow

- Define and agree UI/backend contracts before implementing the relevant interaction.
- Review changes against existing behaviour, the agreed contract, and these principles.
- Run `./scripts/check.sh` before completing a task; investigate and fix reported failures.
- Follow AGENTS.md for task-specific development and verification instructions.

## Governance

This constitution governs project development alongside AGENTS.md. Amendments MUST document the
proposed change and its rationale, receive project maintainer approval, and update the version
and amendment date. Incompatible changes MUST include a migration plan.

Constitution versions follow semantic versioning: MAJOR for incompatible principle removal or
redefinition, MINOR for new principles or materially expanded guidance, and PATCH for
clarifications without semantic change. Reviews MUST check compliance with these principles and
document any justified complexity or dependency. Conflicts or exceptions require explicit
maintainer approval and documentation.

**Version**: 1.0.0 | **Ratified**: 2026-10-27 | **Last Amended**: 2026-10-27
