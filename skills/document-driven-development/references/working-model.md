# Lightweight Document-Driven Working Model

Use this guide when deciding where a fact belongs, drafting a bounded feature
contract, bootstrapping documentation, or closing documentation drift. Adapt it
to the repository rather than copying every section.

## Place one fact in one owner

| Question | Place the answer in |
| --- | --- |
| What exact fields, values, routes, or build settings are valid? | Machine-readable contract plus focused explanatory reference |
| What does the implemented feature do? | Focused product, domain, or API specification |
| What must remain true across features? | Principles or policy |
| Why did we choose this costly-to-reverse approach? | ADR or existing decision log |
| How does a user complete a task? | How-to guide |
| What is every supported parameter or endpoint? | Reference documentation |
| Why does this concept work this way? | Explanation or design rationale |
| How does a new contributor learn it? | Tutorial, only when repeated onboarding demand exists |
| How do operators execute and verify a procedure? | Runbook or tool README |
| What should be built later? | Issue or roadmap |
| What happened in one experiment or release candidate? | Dated, identity-bound evidence |

When another artifact needs the fact, link to the owner and retain only the
minimum context needed for routing.

## Draft a bounded feature contract

Use this shape inside an existing owner or work item. Omit sections that add no
decision value. Write the body in present tense as if implemented; the Status
field alone carries lifecycle, so the contract can be reviewed and accepted
before code exists.

```markdown
## [Feature or change]

Status: Proposed / Accepted / Implemented
Canonical owner: [existing document or intended destination]

### Current baseline and problem
- Current observable behavior: ...
- User or integration problem: ...

### Outcome
- Target user or caller: ...
- Desired observable result: ...

### Goals
- ...

### Non-goals
- ...

### Contract
- Entry points and preconditions: ...
- States, data, or interface behavior: ...
- Validation and failure behavior: ...
- Compatibility or migration: ...

### Constraints and assumptions
- Constraint: ...
- Assumption needing evidence: ...

### Acceptance criteria
- Given ..., when ..., then ...

### Evidence plan
- Automated: ...
- Manual, integration, hardware, or release: ...

### Follow-up and synchronization
- Future work owner: ... or none
- Temporary-plan deletion condition: ... or none
```

Acceptance criteria should describe observable outcomes. Avoid assertions about
private symbols, file layout, exact prose, or one preferred implementation unless
that structure is itself a public or safety-critical contract.

## Map requirements to evidence

Use a table only when several requirements or evidence classes are involved:

| Requirement | Owning contract | Implementation | Evidence | Not proved or remaining gate |
| --- | --- | --- | --- | --- |

An automated test, build, schema validator, static analysis, simulator, physical
device, visual review, signed package, and production observation prove different
facts. State those boundaries rather than collapsing them into "tests passed."

## Bootstrap an undocumented project

Do not pre-create empty documentation taxonomies. Start with the smallest useful
set:

1. Use `README.md` for purpose, audience, quick start, and links to deeper owners.
2. Add one focused behavior or product document when the README can no longer own
   the contract clearly.
3. Add an architecture overview only when system context, structure, flows,
   qualities, or risks need durable communication.
4. Create a decisions location when the first significant decision occurs, using
   the repository's convention or the lightweight architecture default.
5. Track unimplemented work in the team's existing issue system or a small
   roadmap, not in canonical current-state prose.

Grow documentation in response to repeated reader needs and durable ownership,
not to fill a template.

## Compact and reconcile

- Normalize one term per domain concept before adding detail.
- Prefer bounded lists, tables, state diagrams, schemas, formulas, and links over
  repeated narrative.
- Keep changing inventories, versions, and numeric limits in one owner.
- Label proposed, current, deprecated, experimental, and historical material.
- Remove a temporary plan after implemented facts and remaining future work move
  to their durable owners.
- Update derived agent routing only when its trigger, source routing, workflow,
  safety gate, or output contract changes.

## Foundations and limits

This working model is informed by:

- Canonical's documentation-driven development experience:
  <https://ubuntu.com/blog/a-year-of-documentation-driven-development>
- The concise documentation-first loop in the original DDD gist:
  <https://gist.github.com/zsup/9434452>
- Diataxis user-needs taxonomy: <https://diataxis.fr/>
- Write the Docs' docs-as-code workflow:
  <https://www.writethedocs.org/guide/docs-as-code/>

The Markdown-as-source compilation workflow described at
<https://github.blog/ai-and-ml/generative-ai/spec-driven-development-using-markdown-as-a-programming-language-when-building-with-ai/>
is an opt-in experimental pattern. Use it only when a project explicitly treats
generated code as disposable, defines regeneration and review rules, and retains
independent tests. It is not a default requirement of document-driven
development.
