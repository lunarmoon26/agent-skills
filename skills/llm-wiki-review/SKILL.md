---
name: llm-wiki-review
description: Add a human approval gate around the community-managed `llm-wiki` workflow. Use whenever the user wants to ingest, synthesize, add, or update source material in an LLM Wiki but wants proposed compiled Wiki content reviewed before it is created or changed; also use when the user asks to continue, approve, reject, revise, defer, or recover a pending `llm-wiki-review` proposal. Do not use for read-only Wiki queries, or when the user explicitly accepts `llm-wiki` direct writes without review.
---

# LLM Wiki Review

Use this skill as a lightweight human-in-the-loop layer over the separately
installed, community-managed `llm-wiki` skill. The underlying skill supplies
Wiki orientation, source capture, retrieval, synthesis, and maintenance. This
skill owns the decision to promote a proposed claim into compiled Wiki content.

This is a review convention, not a deterministic access-control boundary. Use a
dedicated tool with enforced transactions, hashes, and path controls when those
guarantees are required.

## Preconditions and authority

1. Resolve the Wiki root from the user's explicit path or the active
   `WIKI_PATH` configuration. If it is missing or ambiguous, ask for it; do not
   guess another Wiki location.
2. Confirm that the community `llm-wiki` skill is available to the active agent,
   then load it using that agent's normal skill-loading mechanism. Do not copy,
   modify, or replace the community skill.
3. Treat the resolved Wiki root as the only writable Wiki boundary. Keep the
   source and target paths explicit; do not search unrelated workspaces to find
   a substitute source or Wiki.
4. If another review/apply system already controls this change, such as a
   deterministic librarian tool or queue, stop rather than creating competing
   authorities.

The companion may create immutable Raw captures and `Review/` proposal files.
Until a valid, explicit approval, it must not create or alter compiled Wiki
pages, including entity, concept, comparison, query, index, log, or schema
files.

## Create a proposal

1. Follow `llm-wiki`'s normal orientation and discovery process: read the active
   schema, index, and recent log; preserve source provenance; search for
   relevant existing pages; and surface uncertainty or contradictions.
2. Capture Raw material only as the underlying skill prescribes. Preserve the
   exact source body, use its current hash convention, and immediately verify
   the stored body hash. Raw material remains immutable after capture.
3. Stop before every compiled write. For each target, create one proposal in:

   ```text
   Review/YYYY-MM-DD-<target-name>-proposal.md
   ```

   `Review/` is relative to the Wiki root. Keep the target and every source path
   relative to that root. Reject a target whose normalized path, parent, or
   resolved destination escapes the Wiki root.
4. Record the target's baseline state and the exact proposed content. These
   hashes let a resumed review detect a changed source, target, or proposal
   instead of applying stale approval. Use this frontmatter shape:

   ```yaml
   ---
   type: llm-wiki-review
   status: needs-review
   decision: pending
   revision: 1
   operation: create
   target: concepts/example.md
   target_sha256: absent
   source_hashes:
     raw/articles/example-source.md: <sha256-of-raw-body>
   proposed_content_sha256: <sha256-of-exact-proposed-content>
   sources:
     - raw/articles/example-source.md
   ---
   ```

   Set `operation` to `create`, `update`, or `conflict-resolution`. For an
   update, `target_sha256` is the SHA-256 of the current target bytes; for a
   create it is `absent`. Recompute `proposed_content_sha256` over the exact
   text under **Proposed content**, not the proposal's feedback or decision
   fields.
5. Use this proposal body:

   ```markdown
   # Proposed Wiki change

   ## What will change
   Explain the change and its expected scope in plain language.

   ## Proposed content
   Include the exact complete content that would be written to `target`.

   ## Evidence and uncertainty
   Identify supporting Raw sources, uncertainty, and conflicting claims.

   ## Human feedback
   Add a decision or feedback here if working from the file.
   ```

6. Validate the exact proposed content against the active `SCHEMA.md` before
   showing it to the user. At minimum, compiled pages need `title`, `created`,
   `updated`, `type`, `tags`, and `sources`, unless the active schema has a
   stricter rule. Use `tags: []` when the schema has no applicable taxonomy; do
   not omit the field. Do not request approval for invalid content.

For a Wiki bootstrap, propose each compiled foundational file separately. Do not
let `llm-wiki` initialize `SCHEMA.md`, `index.md`, or `log.md` directly while
this companion governs the run.

### Contradictions

Present competing claims before the detail and propose retaining both with an
appropriate contested marker. Replace the usual feedback prompt with these
primary choices, and repeat them in the response:

- **Keep both:** approve this proposal.
- **Not a contradiction:** revise it to preserve compatible or context-dependent
  claims without the contested marker, then request approval again.
- **Decide later:** defer without changing compiled content.

Treat source preference or a custom resolution as `revise`. Require a reason or
stronger evidence before removing a supported claim; never silently choose a
winner.

## Request and bind the decision

Report the proposal path, revision, target, operation, and main uncertainty.
For ordinary proposals, ask for `approve`, `reject`, `revise`, or `defer`.
Accept a decision either in the conversation or in the proposal frontmatter.
Use only these canonical `decision` values: `pending`, `approve`, `reject`,
`revise`, and `defer`.

Bind a decision to the named proposal and current revision. If more than one
pending proposal could match the request, list the candidates and ask the user
to name one. Silence, elapsed time, or a decision for an older revision is not
approval. Stop after requesting a decision.

## Resume, apply, or recover

Resume only after another explicit user request. Reread the named proposal and
its current revision, then verify all of the following before any compiled
write:

- the decision is `approve` for this revision;
- the target remains inside the Wiki root and its bytes still match
  `target_sha256` (or remain absent for `create`);
- every Raw source's current body hash matches `source_hashes`;
- the exact proposed content still matches `proposed_content_sha256`; and
- the content still satisfies the active schema.

If a source, target, schema, path, or proposed content has changed, do not
apply the approval. Create or update a new pending revision with fresh hashes,
describe why it is stale, and request review again.

- **Approve:** Write only the exact reviewed content to `target`. Set
  `decision: approve` and `status: applied`. Use `llm-wiki` for derived index
  and log maintenance after the target write. List those derived changes in the
  completion receipt. Do not let maintenance modify another compiled content
  page unless that page has its own approved proposal.
- **Reject:** Leave all compiled content unchanged. Set `decision: reject` and
  `status: rejected`; change no index or log.
- **Revise:** Incorporate the feedback into the proposal, increment `revision`,
  refresh all relevant hashes, reset `decision: pending` and
  `status: needs-review`, then stop for approval.
- **Defer:** Leave all compiled content unchanged. Set `decision: defer` and
  `status: deferred`; change no index or log.

Make retries idempotent. If an interruption left the approved target already
matching the proposal, finish only missing derived maintenance; do not rewrite
the target or duplicate log entries. If the state cannot establish that safely,
stop and request a new review.

## Completion receipt

Before reporting completion, confirm and state:

- proposal path, revision, decision, and target;
- Raw provenance and stored-body-hash verification;
- schema validation of the proposed and, when approved, applied content;
- that approved content exactly matches the reviewed proposal;
- every compiled file changed after approval, including derived index/log work;
- that reject and defer changed only proposal state; and
- any remaining uncertainty, contested claims, or required follow-up.
