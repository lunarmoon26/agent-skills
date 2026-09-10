---
name: research-driven-development
description: Use for evidence-led engineering when a task requires drilling into local or external codebases, comparing implementations, frameworks, libraries, or standards, evaluating strengths and weaknesses, tracing how a system really works, or researching before a consequential implementation choice. Use when the user says investigate, compare approaches, survey repositories, learn from existing projects, find prior art, or validate a design against source. Do not use for routine code navigation, a simple documentation lookup, or architecture/spec writing that needs no source research.
---

# Research-Driven Development

Use research to reduce implementation uncertainty, not to manufacture a document
pipeline. Current agents can perform the synthesis; this skill establishes the
evidence standard that keeps that synthesis grounded.

Project-local instructions, established documents, and user constraints take
precedence over this general workflow.

## Choose the smallest useful depth

| Depth | Use when | Typical scope |
| --- | --- | --- |
| Quick | One unfamiliar mechanism or a narrow local question | One codebase, targeted trace |
| Standard | Choosing or adapting an approach | Local baseline plus two to four high-signal sources |
| Deep | High-risk, expensive, or explicitly broad research | More sources, reproduction, history, and a durable report |

Do not turn every investigation into a landscape survey. Stop when the evidence
can discriminate the viable options and identify the remaining validation.

## Research workflow

1. **Frame the decision** - State the engineering question, relevant constraints,
   and what evidence would change the implementation choice. Infer these from the
   task and repository when possible; ask only for a user-essential unresolved
   criterion.
2. **Inspect the local baseline** - Read repository instructions, current code,
   tests, contracts, dependencies, and existing decisions before looking for an
   external pattern. Research must solve this project's problem rather than a
   generic one.
3. **Discover candidates** - Use repository search, primary documentation, web
   search, or BX to find plausible sources. Prefer maintained primary repositories
   and the version relevant to the project. Search results discover candidates;
   they do not establish how a source works.
4. **Select for signal** - Choose the few sources most likely to answer the
   question. Consider direct requirement fit, implementation accessibility,
   recency, maturity, and domain similarity. Popularity alone is not evidence of
   fit.
5. **Pin source identity** - Record the repository and the inspected tag, release,
   branch, or commit when the conclusion depends on version. State when only the
   current default branch was available.
6. **Drill into implementation** - Trace the relevant entry point through core
   abstractions, state and data flow, side effects, failure and cancellation paths,
   extension seams, and tests. Read the focused guide in
   [references/deep-dive-guide.md](references/deep-dive-guide.md) when evaluating a
   source or comparing several sources.
7. **Evaluate in context** - Explain the source's mechanism, strengths,
   weaknesses, hidden assumptions, operational costs, and transfer risk relative
   to the local project. A source can be well engineered and still be a poor fit.
8. **Verify selectively** - Run a focused test, example, build, or reproduction
   when feasible and when it would materially increase confidence. Do not present
   static inspection as runtime proof.
9. **Synthesize a decision** - Recommend `adopt`, `adapt`, `experiment`, or
   `reject`. Name what should be borrowed, what should remain local, and the
   smallest experiment needed for unresolved risk.

Independent source deep dives can run in parallel. Give each investigator the
same question and evidence contract, then synthesize across their findings rather
than concatenating reports.

## Evidence discipline

- Label important claims as **direct evidence**, **inference**, or **unknown**.
- Cite exact repository files and line ranges for implementation claims. Add a
  commit or tag when lines may move or version differences matter.
- Treat public docs as the intended contract and source/tests as evidence of the
  inspected implementation. A mismatch is a finding, not a reason to silently
  choose whichever artifact supports the recommendation.
- Include negative evidence: missing tests, unhandled failures, hard coupling,
  stale dependencies, undocumented assumptions, or a mechanism that does not
  transfer.
- Do not infer production quality from stars, examples, a polished README, or one
  successful happy-path test.
- Keep confidential code and credentials within their authorized boundary. A
  research task does not authorize publishing, cloning private sources elsewhere,
  or accepting new service terms.

## Default output

Return a concise memo unless the user requests a file or the research will remain
useful beyond the current decision:

```markdown
## Research: [question]

### Decision criteria
- ...

### Local baseline
- Current mechanism and constraints: ...

### Sources inspected
| Source and identity | Mechanism | Strengths | Weaknesses | Transfer risk | Evidence |
| --- | --- | --- | --- | --- | --- |

### Recommendation
- Adopt / adapt / experiment / reject: ...
- Why: ...

### Confidence and remaining validation
- Direct evidence: ...
- Inference or unknown: ...
- Smallest next experiment: ...
```

Persist a research note only when requested, when several future tasks will reuse
it, or when it supports a durable specification or decision. Follow the
repository's existing documentation structure. Use `document-driven-development`
to place lasting findings and `lightweight-architecture` when the outcome changes
system structure or warrants an architecture decision record.

## Avoid

- Mandatory phases, fixed filenames, ID registries, or one report per source.
- Exhaustive candidate catalogues after the decision is already clear.
- Feature checklists that never inspect implementation.
- Recommendations without local constraints or concrete source anchors.
- Copying another project's architecture wholesale.
- Keeping a research document as a higher-authority override over current specs,
  decisions, machine contracts, or implementation evidence.
