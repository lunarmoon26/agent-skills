# Focused Codebase Deep Dive

Read this guide when a research question requires understanding how a local or
external codebase actually implements a relevant behavior. It is a rubric, not a
required report template.

## Start from the project question

Write one sentence for each item:

- **Question:** What implementation decision are we trying to make?
- **Criteria:** Which local constraints or quality attributes discriminate good
  options?
- **Target mechanism:** What exact behavior must be traced?
- **Confidence need:** Is static evidence enough, or is reproduction required?

## Establish source identity

Record enough identity to make the finding reproducible:

```text
Repository: owner/name or canonical URL
Inspected identity: tag, release, branch, or full commit
Inspection date: YYYY-MM-DD when currency matters
Relevant language/runtime: ...
```

Prefer the release compatible with the local project over an unrelated latest
branch. If documentation describes another version, call out the difference.

## Trace the mechanism

Follow the shortest end-to-end path that can answer the question:

1. Public entry point, command, handler, or API.
2. Dispatch, routing, lifecycle, or orchestration layer.
3. Core abstraction and its concrete implementation.
4. State ownership, data model, and persistence boundary.
5. External calls, I/O, concurrency, and other side effects.
6. Validation, errors, cancellation, retry, and cleanup.
7. Extension or replacement seam.
8. Unit, integration, conformance, and failure-path tests.

Do not inventory the whole repository. Expand the trace only when a dependency or
cross-cutting mechanism changes the conclusion.

## Evidence anchors

For each consequential claim, capture a compact anchor:

```text
owner/repository@identity: path/to/file.ext:line-line - observed mechanism
```

Use symbols plus file and line ranges when possible. Link tests that establish the
behavior, not only the implementation definition. If the evidence comes from a
runtime experiment, record the exact command, environment assumptions, and result.

## Evaluate strengths and weaknesses

Judge the mechanism against the local criteria, not against an abstract ideal.

| Concern | Questions |
| --- | --- |
| Correctness | Which invariants are encoded? Which edge cases are tested? |
| Composability | Can the mechanism be extended or replaced without bypassing policy? |
| Operability | How are failures, retries, cancellation, observability, and recovery handled? |
| Maintainability | Is ownership clear? Are abstractions earned or incidental? |
| Security and privacy | Where are trust boundaries, validation, credentials, and sensitive data? |
| Performance | What work is duplicated, blocking, unbounded, or allocation-heavy? |
| Maturity | Do tests, releases, issue history, and maintenance activity support the claimed behavior? |

Always include at least one meaningful weakness or state that focused inspection
found none within scope. Avoid manufacturing symmetry when a source is clearly
strong or weak.

## Assess transfer risk

Separate borrowing a concept from adopting a dependency:

- **Adopt:** Use the source or its supported API directly.
- **Adapt:** Reimplement a bounded pattern under local constraints.
- **Experiment:** Prototype because runtime, scale, policy, or integration evidence
  is missing.
- **Reject:** The mechanism conflicts with requirements or costs more than it
  solves.

Check domain mismatch, language/runtime differences, licensing, dependency and
upgrade cost, operational assumptions, data migration, team familiarity, and how
much surrounding architecture the pattern requires.

## Compare sources

Use one row per source and criteria that matter to the decision:

| Source | Mechanism | Requirement fit | Evidence quality | Weakness | Transfer cost | Verdict |
| --- | --- | --- | --- | --- | --- | --- |

Scores are optional. If used, define them for this decision instead of imposing a
universal scale. A short explanation is more useful than false numerical precision.

## Stop conditions

Stop researching when:

- one option meets the criteria and remaining sources cannot plausibly change the
  decision;
- the important mechanism and its failure boundaries are directly evidenced;
- differences reduce to preferences the user or project already settled;
- the next uncertainty requires a local experiment rather than more reading; or
- additional sources repeat an already understood pattern.

End by naming the confidence level and the smallest action that could falsify the
recommendation.
