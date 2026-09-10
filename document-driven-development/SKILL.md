---
name: document-driven-development
description: Use for repository-level documentation-first engineering when the user explicitly requests document-driven or spec-first work, a PRD or feature contract, canonical documentation ownership, docs-to-code drift repair, synchronized docs/code/tests, or requirement-to-evidence closure. Also use for consequential externally visible or persisted behavior changes that must update an existing contract. Do not use for ordinary coding with no contract impact, one-off prose or file-format editing, architecture briefs or ADRs, or comparative source research.
---

# Document-Driven Development

Design accepted behavior in the smallest sufficient document, implement it,
verify it, and reconcile what was learned in the same change. Documentation is
part of engineering, not a transcript written after implementation. It is also
not a reason to delay a small change with unnecessary process.

Two anchors: if a feature is not documented, it does not exist to its users; if
it is documented incorrectly, it is broken.

Project-local instructions, established ownership, templates, and safety gates
take precedence over this general workflow.

## Scale the documentation to the change

| Change | Documentation depth |
| --- | --- |
| Tiny, local, reversible, no contract change | Confirm intent and tests; create no new document |
| Bounded behavior or interface change | Update the focused owner with a short contract and acceptance criteria |
| Cross-cutting, persisted, externally visible, or costly to reverse | Add explicit design, risks, migration, and evidence; consider an ADR |
| New project with no conventions | Bootstrap only the documents that already have real content |

The goal is earlier clarity, not more Markdown.

## Identify authority by fact type

Do not treat every repository artifact as one chronological source of truth.
Identify which artifact owns each fact:

| Fact | Typical owner |
| --- | --- |
| Exact syntax or shape | Schema, manifest, interface definition, migration, build configuration, or other machine-readable artifact |
| Implemented product behavior | Focused specification, API reference, or domain contract |
| Durable cross-feature constraint | Principles or policy document |
| Architecture rationale | Accepted ADR or established decision log |
| User learning or task guidance | Tutorial, how-to, reference, or explanation selected by user need |
| Procedure and commands | Runbook or tool README |
| Unimplemented work | Issue, roadmap, or bounded temporary plan |
| Experiment or measurement | Dated evidence tied to version, environment, and limitations |
| Agent routing or reusable workflow | Repository instructions or project skill that links back to canonical owners |

Use existing filenames and owners. Read
[references/working-model.md](references/working-model.md) when placing a new
fact, bootstrapping a repository, or drafting a feature contract.

## Write as if shipped

Describe behavior in present tense - "returns", "rejects", "defaults to" - never
future tense. Carry lifecycle in status labels (`Proposed`, `Accepted`,
`Implemented`, `Deprecated`) rather than in verb tense, so a document can be
reviewed and accepted before the code exists.

## Change loop

1. **Inspect** - Read repository instructions, existing docs, machine contracts,
   implementation, tests, current work item, and relevant diffs. Find the focused
   owner before proposing another file.
2. **Separate status** - Distinguish current implemented behavior, the accepted
   change, future follow-up, historical evidence, and unresolved assumptions.
   None should silently masquerade as another.
3. **Document the delta** - Before broad implementation, write or confirm the
   problem, current baseline, desired outcome, goals, non-goals, observable
   behavior, constraints, acceptance criteria, and evidence needs. Put this in
   the existing canonical owner when possible, written as if shipped. For
   consequential externally visible behavior, get user agreement on this delta
   before implementing it.
4. **Resolve significant choices** - Use `research-driven-development` when the
   solution depends on unfamiliar codebases or comparative evidence. Use
   `lightweight-architecture` when the change alters system structure, critical
   qualities, external dependencies, deployment, or another costly-to-reverse
   decision.
5. **Implement minimally** - Inspect current code and make the smallest coherent
   change that satisfies the documented contract. Keep exact shapes in their
   machine-readable owners.
6. **Verify the contract** - Map automated and manual evidence to observable
   acceptance criteria, and walk the documented workflows end to end the way a
   user would. Run every command or example the changed documentation shows;
   output must match what the text promises. Tests should verify behavior and
   durable invariants, not prose wording, source layout, or the existence of a
   document.
7. **Reconcile discoveries** - Update the focused owner when implementation
   reveals a real constraint or edge case. Move remaining future work to its
   roadmap or issue, procedures to runbooks, bounded observations to evidence,
   and significant rationale to an ADR.
8. **Close the loop** - Review every changed layer, remove superseded snapshots or
   temporary plans whose facts have moved, validate links and project tooling,
   ship documentation in the same change or release as the behavior it describes,
   and report requirements against implementation and evidence.

Documentation of a command or side effect is not authorization to perform it.
Honor the project's worktree, deployment, publication, paid-service, hardware,
privacy, and destructive-action gates independently.

## Handle disagreement as drift

When docs, code, tests, and machine artifacts disagree:

1. Name the conflicting claims and their fact types.
2. Inspect the focused owner, exact machine contract, implementation, tests, and
   relevant decision history.
3. Determine intended behavior from evidence and current authorization; do not
   automatically prefer the newest prose or the current code.
4. Reconcile the owning artifacts in one scoped change.
5. Delete or supersede stale derived text instead of appending another override.

When verification fails against the documented contract, triage before editing:
intent still holds - fix the code; the document was wrong - pause, correct the
document first, then realign code and tests; both are doubtful - resolve intent
with the user. Never quietly adjust whichever artifact happens to match current
behavior.

Structural validation can prove syntax, links, schemas, or file conventions. It
cannot prove that prose is semantically true. Include both structural results and
the semantic owner review in the closure receipt.

## Keep agent context progressive

- Root instructions should route universal constraints and common commands.
- Nested instructions should cover clear path boundaries only.
- Skills should classify tasks, load canonical sources, guide transformations,
  select verification, and report evidence.
- Canonical docs and machine artifacts should load only for the affected domain.
- Skills and instructions should not copy changing inventories, limits, versions,
  or complete API references from their owners.

## Default closure receipt

```markdown
## Document-Driven Closure: [change]

### Contract and authority
- Accepted behavior: ...
- Canonical owner: ...
- Exact machine owner: ... or none

### Requirement to evidence
| Requirement | Implementation | Automated evidence | Manual or residual evidence |
| --- | --- | --- | --- |

### Synchronization
- Current behavior updated in: ...
- Future work moved to: ... or none
- Superseded material removed: ... or none
- Structural checks: ...

### Remaining uncertainty or gates
- ...
```

## Avoid

- Creating `PLAN.md`, `ARCHITECTURE.md`, `TODO.md`, `DECISIONS.md`, or any other
  standard set before inspecting the repository.
- Duplicating a fact so every document appears self-contained.
- Keeping shipped behavior in a roadmap or future behavior in a current spec.
- Making an issue, handoff, chat transcript, skill, or research note override a
  focused current contract.
- Treating Markdown as executable source unless the project explicitly adopts and
  validates that generation model.
- Blocking a tiny reversible fix on a large design document.
- Future-tense documentation ("will support"); label status instead.
- Declaring a feature done while any documented example remains unrun.
