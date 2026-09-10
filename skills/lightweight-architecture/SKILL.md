---
name: lightweight-architecture
description: "Use for repository architecture documentation and significant design decisions: architecture briefs, arc42-style context or views, system boundaries, decomposition, critical runtime or deployment flows, quality scenarios, risks, architecture reviews, ADRs, decision records, option tradeoffs, and superseding an accepted decision. Use when the user asks to document or review architecture without a heavyweight research program. Do not use for routine feature documentation or exhaustive comparative codebase research."
---

# Lightweight Architecture

Document the architecture that helps current stakeholders make, implement, and
review consequential decisions. Prefer a small current model over a complete but
stale template.

Project-local instructions, established architecture documents, diagram
conventions, and decision processes take precedence over this skill.

## Select a mode

| Mode | Use when | Output |
| --- | --- | --- |
| Architecture brief | A system or meaningful subsystem needs shared context | Existing architecture owner or one compact brief |
| Decision record | One significant choice needs durable rationale | ADR or established decision-log entry |
| Architecture review | Code, docs, qualities, or decisions may have drifted | Findings, missing evidence, and focused updates |

A task may use both a brief and an ADR, but do not make an ADR restate the entire
architecture.

## Inspect before authoring

1. Read repository instructions and locate existing architecture, product,
   operations, security, data, deployment, and decision owners.
2. Inspect the implementation, tests, manifests, schemas, and infrastructure that
   support the architectural claims. Record exact artifact paths and the relevant
   release, commit, environment, or deployment identity for consequential current-
   state claims.
3. Identify the audience, decision at hand, top constraints, and quality outcomes.
4. Update established owners rather than imposing a new filename or diagram
   notation.
5. Use `research-driven-development` first when the direction depends on evidence
   from unfamiliar local or external codebases.

## Architecture brief workflow

Read [references/architecture-brief.md](references/architecture-brief.md), then:

1. State purpose, scope, non-goals, and stakeholders.
2. Capture only the highest-priority quality scenarios and hard constraints.
3. Delimit the system from users, neighboring systems, and external interfaces.
4. Explain the solution strategy and level-one building blocks with clear
   responsibilities and dependencies.
5. Add only architecturally relevant runtime, data, and deployment views.
6. Record cross-cutting rules, risks, technical debt, and links to significant
   decisions.
7. Compare the brief with current code and evidence; cite exact supporting
   artifacts and label proposed architecture separately from implemented
   architecture.

Use diagrams when they answer a stakeholder question better than text. Every
diagram needs a named scope, audience or concern, and explanatory labels. A
diagram is not useful merely because architecture documentation usually has one.

## Decide whether an ADR is warranted

Create or update a decision record when a choice materially affects one or more
of these concerns and future contributors will need the rationale:

- system boundaries, decomposition, or ownership;
- measurable quality attributes such as security, reliability, performance,
  operability, or evolvability;
- external or persisted interfaces and data models;
- major dependencies, vendors, frameworks, or construction techniques;
- deployment, runtime topology, migration, or trust boundaries;
- an approach that is expensive, risky, or difficult to reverse.

Skip an ADR when the choice is local, low-risk, readily reversible, temporary,
already mandated by an accepted owner, or has no meaningful alternative. Record
experiments as evidence and ordinary implementation details in code or the work
item.

For a significant decision, read
[references/adr-guide.md](references/adr-guide.md). Keep one decision per record,
make the forces and alternatives explicit, include positive and negative
consequences, and define how conformance will be checked.

## Review and synchronization

- The architecture brief owns the current shared model; an ADR owns why a
  significant choice was made. Neither should duplicate focused product or API
  specifications.
- Exact shapes remain in machine-readable contracts. Architecture prose explains
  boundaries, responsibilities, qualities, and rationale.
- A proposed ADR may evolve during review. Preserve the meaning of an accepted or
  rejected ADR. Materially changed decisions require a new ADR that supersedes
  the old one.
- When accepting or superseding an ADR, update the current architecture summary,
  focused contracts, tests or fitness checks, and links that depend on it.
- Keep unimplemented options visibly proposed. Do not present a target diagram as
  the current system.
- Treat implementation, deployment, test, and architecture-document disagreement
  as drift to investigate, not as permission to add an override file.

## Default architecture review

```markdown
## Architecture Review: [scope]

### Audience and decision
- ...

### Current architecture evidence
- Context and boundaries (artifact and identity): ...
- Building blocks and ownership (file paths): ...
- Critical runtime/deployment flow (source, tests, and environment): ...
- Quality scenarios (acceptance evidence): ...

### Findings
| Severity | Finding | Evidence | Owner or decision affected | Recommended action |
| --- | --- | --- | --- | --- |

### ADR actions
- Create / accept / supersede / none: ...

### Unknowns and validation
- ...
```

## Avoid

- Filling all twelve arc42 sections regardless of relevance.
- Describing every source directory, class, runtime path, or deployment resource.
- Treating a framework diagram as proof of actual integration.
- Recording every implementation choice as an ADR.
- Editing an accepted ADR until it appears to predict a later decision.
- Making an ADR or architecture document a higher-authority override over exact
  machine contracts or focused current behavior.
- Starting an exhaustive research program when repository evidence already
  supports the architectural decision.
