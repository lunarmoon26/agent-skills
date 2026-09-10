# Lightweight Architecture Decision Records

Use this guide for one architecturally significant choice. The purpose of an ADR
is to preserve why a choice was made under a particular context, not to duplicate
the current architecture or implementation plan.

## Use the repository's convention first

Inspect existing decision records, status terms, numbering, indexes, and approval
rules. If none exist, use this small default:

```text
docs/decisions/NNNN-short-kebab-title.md
```

Use monotonically increasing numbers and never reuse an accepted number. Create
the directory and first file only when the first real decision exists; do not
bootstrap an empty decision catalogue.

## Significance test

An ADR is useful when at least one answer is yes:

- Will this alter system structure, ownership, or a critical boundary?
- Does it trade one important quality attribute against another?
- Does it establish an external, persisted, security, privacy, or deployment
  contract?
- Does it commit the project to a major dependency, vendor, framework, or
  operational model?
- Is reversal expensive, risky, migration-heavy, or likely to surprise a future
  contributor?
- Were multiple viable alternatives rejected for reasons that code will not show?

Otherwise keep the choice in code, a focused specification, the work item, or a
bounded experiment note.

## Record template

Keep the record readable in a few minutes. Optional metadata should follow the
repository's norms.

```markdown
# NNNN: [Decision in a short active title]

Status: Proposed
Date: YYYY-MM-DD
Decision owners: ... (optional)
Related: issue, specification, architecture section, or prior ADR

## Context
[State the problem, forces, constraints, and architecture-driving quality
scenarios. Keep this value-neutral and specific to the decision date.]

## Decision drivers
- ...

## Options considered
### [Option A]
- Helps because ...
- Hurts because ...

### [Option B]
- Helps because ...
- Hurts because ...

## Decision
Choose [option] because [reason tied to the drivers].

## Consequences
- Positive: ...
- Negative: ...
- Neutral or follow-up: ...

## Confirmation
- Test, review, metric, migration evidence, or fitness check that will demonstrate conformance: ...

## Links
- Supersedes / superseded by / refines / depends on: ...
```

For an obvious choice, collapse option details into a short list. Do not omit the
rejected alternatives when their tradeoffs are the main value of the record.

## Lifecycle

| Status | Meaning |
| --- | --- |
| Proposed | Open for review and material edits |
| Accepted | Current decision; preserve its original meaning |
| Rejected | Considered but not adopted; preserve the reason |
| Deprecated | Still historical but no longer recommended, without one direct replacement |
| Superseded | Replaced by a linked later ADR |

Accepted or rejected records are immutable in meaning, not necessarily in bytes.
Fixing a typo, broken link, or unambiguous metadata is acceptable. Changing the
context, choice, rationale, or consequences requires a new record. The new ADR
links to and supersedes the old one; the old ADR receives only the status and
replacement link needed to navigate history.

Do not delete a superseded decision merely because Git retains file history. The
record remains useful context for commits and releases made while it was active.

## Synchronize after a decision

An accepted ADR does not automatically update the system:

1. Update the current architecture summary or focused specification.
2. Implement and test the decision at the owning boundary.
3. Add a focused fitness check when an objective invariant can prevent drift.
4. Update indexes and links without copying the full rationale.
5. State any rollout, migration, or evidence still required.

If implementation reveals a different significant choice, create or propose a
new ADR. Do not create a highest-authority "override" document that leaves the
architecture and accepted decision contradictory.

## Review questions

- Is this exactly one decision?
- Is the context specific enough to explain why the decision was reasonable then?
- Are the important alternatives and decision drivers visible?
- Are positive, negative, and neutral consequences honest?
- Can the confirmation distinguish conformance from aspiration?
- Are current versus proposed behavior and follow-up work clear?
- Does the architecture summary link to the current decision?

## Foundations

This guide combines a small original template with concepts from:

- Michael Nygard's CC0 article and concise ADR structure:
  <https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions>
- MADR, available under MIT or CC0:
  <https://adr.github.io/madr/>
- The ADR reference collection:
  <https://github.com/architecture-decision-record/architecture-decision-record>
- AWS Prescriptive Guidance on ADR lifecycle:
  <https://docs.aws.amazon.com/prescriptive-guidance/latest/architectural-decision-records/adr-process.html>

Consult a project's governance and the original sources when formal approval,
regulatory evidence, or a specific ADR format is required.
