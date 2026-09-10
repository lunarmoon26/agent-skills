# Compact Architecture Brief

This is an arc42-informed question set, not a shortened copy of the arc42
template. Use only the sections needed to explain the current decision, system,
or subsystem.

## Relevance filter

| Topic | Include when |
| --- | --- |
| Purpose, scope, and stakeholders | Always, but keep it short |
| Quality scenarios | A quality attribute shapes architecture or acceptance |
| Constraints | A technical, organizational, legal, operational, or budget limit narrows choices |
| Context and external interfaces | Almost always for a system; for a subsystem when its boundary is unclear |
| Solution strategy | Several design choices form one coherent direction |
| Level-one building blocks | More than one meaningful responsibility or deployable component exists |
| Runtime view | A critical, surprising, failure-prone, or distributed interaction needs explanation |
| Data view | Ownership, lifecycle, consistency, migration, or sensitive-data flow matters |
| Deployment view | Infrastructure, environments, topology, hardware, or operations influence design |
| Cross-cutting concepts | A rule applies across several components and would otherwise be duplicated |
| Decisions | A significant choice needs rationale and lifecycle; link ADRs rather than copying them |
| Risks and technical debt | Known uncertainty or compromise can affect delivery or operation |
| Glossary | Domain terms are ambiguous or overloaded |

Leave irrelevant topics absent instead of writing "not applicable" sections.

## Brief template

Adapt this inside the repository's current architecture owner. A small project
may need only a page; a mature project may split these concerns across focused
documents.

```markdown
# [System or subsystem] Architecture

Status: Implemented / Proposed / Mixed (label proposed sections)
Audience: ...
Last verified against: [commit, release, environment, or date when useful]

## Purpose and scope
- User or business outcome: ...
- In scope: ...
- Non-goals: ...
- Key stakeholders and concerns: ...

## Quality scenarios and constraints
| Priority | Context and stimulus | Observable response or change | Measure |
| --- | --- | --- | --- |

Hard constraints:
- ...

## Context and interfaces
| Actor or neighboring system | Inputs | Outputs | Protocol or trust boundary | Owner |
| --- | --- | --- | --- | --- |

## Solution strategy
- Fundamental approach: ...
- How it supports the top quality scenarios: ...
- Significant decisions: [ADR links]

## Level-one building blocks
| Building block | Responsibility | Owned data or state | Interfaces | Dependencies |
| --- | --- | --- | --- | --- |

## Critical flows
### [Flow, failure, startup, migration, or recovery scenario]
1. ...

## Deployment and operations
- Environments and topology: ...
- Software-to-infrastructure mapping: ...
- Scaling, observability, recovery, and operational ownership: ...

## Cross-cutting concepts
- Security and privacy: ...
- Data consistency and migration: ...
- Error, retry, cancellation, and idempotency: ...
- Other system-wide rule: ...

## Risks and technical debt
| Risk or debt | Impact | Evidence or trigger | Mitigation or decision needed |
| --- | --- | --- | --- |

## Glossary
| Term | Meaning |
| --- | --- |
```

## Quality scenarios

Avoid labels such as "fast," "secure," or "scalable" without an observable
condition. A compact scenario states:

1. **Context:** Relevant system state or environment.
2. **Stimulus:** Event, request, failure, or proposed change.
3. **Response:** Expected behavior or modification.
4. **Measure:** Threshold, bound, evidence, or acceptance result.

Keep only the top three to five architecture-driving scenarios in the summary.
Detailed acceptance criteria can live in focused specifications.

## Views and depth

- Start with the system context and level-one responsibilities.
- Add a runtime scenario for representative success, important failure, recovery,
  migration, or an interaction that crosses trust or process boundaries.
- Add deployment detail only to the depth needed to explain runtime qualities and
  operational ownership.
- Decompose a building block further only when it is complex, risky, volatile,
  surprising, or independently owned.
- Prefer a table or numbered flow when it communicates more precisely than a
  diagram.

## Current versus target state

For mixed documents, label each proposed section or use separate current and
target views. Bind factual claims to code, machine artifacts, tests, deployed
evidence, or an accepted decision. Do not let a target architecture silently
become documentation of current behavior.

## Source inspiration

The questions and relevance filtering are informed by the arc42 template and its
"travel light" guidance:

- <https://github.com/arc42/arc42-template>
- <https://docs.arc42.org/>

arc42's template and documentation are licensed CC BY-SA 4.0. This guide uses an
original compact structure and does not reproduce the template text. Consult the
official material, attribution requirements, and complete sections when a project
needs full arc42 compatibility.
