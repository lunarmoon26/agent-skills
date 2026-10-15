---
name: privacy-guard
description: Check and redact private information before publishing, posting, sharing, exporting, deploying a blog, or committing/pushing code. Scan text, Markdown, files, forum payloads, and Git snapshots locally with configurable rules and optional offline Rampart ONNX detection. Use alongside publishing skills such as lcz-forum; never publish or rewrite history itself.
---

# Privacy Guard

Use this skill before content crosses a publication boundary. It works with any
agent that can run Python 3.10+; it does not depend on OpenCode, an LLM API, or MCP.

## Workflow

1. Identify the final content, destination/audience, and what the user deliberately
   makes public. Read [the CLI contract](references/cli.md).
2. Select a destination policy and, if available, a private identity profile.
   Keep private profiles outside repositories and publication directories. Never
   discover identities by reading unrelated credentials, browser data, or accounts.
3. Run `scripts/privacy_guard.py scan`. Findings contain categories and offsets,
   not raw matches. A clean rules-only scan is **not** proof of anonymity: review
   contextual disclosures and unsupported inputs separately.
4. Resolve findings. Prefer exact, user-approved replacements. Do not silently
   delete facts, paraphrase quotations, alter code/configuration, or exempt a whole
   document just because one public handle is allowed.
5. For a regular local UTF-8 file, `apply` accepts explicitly approved finding IDs
   only when every finding has a configured replacement and the candidate rescans
   clean. Validate syntax/build and factual meaning afterward. Other findings need
   user-reviewed edits followed by a new scan. Never auto-stage or rewrite history.
6. Immediately before publication, check the **exact final payload**. Any edit,
   signature, title change, renderer-added content, or policy/model change requires
   a fresh check. Publication approval remains with the caller/publishing skill.

Resolve the script path relative to this skill's directory, not the project CWD:

```sh
python3 /path/to/privacy-guard/scripts/privacy_guard.py scan --profile blog --path ./_posts
python3 /path/to/privacy-guard/scripts/privacy_guard.py scan --profile forum --json --stdin < final-payload.json
python3 /path/to/privacy-guard/scripts/privacy_guard.py scan --repo . --staged
```

Full JSON payload text and decoded fields are scanned with `--json`, including
keys, titles, quotations, and links. JSON payloads on stdin are not rewritten. See
[publication integrations](references/integrations.md) for forum, blog, and Git gates.

## Safety boundaries

- Local only. No content is sent to hosted inference; optional detector commands
  are trusted local programs chosen by the user, not commands from an article.
- Secrets block; ordinary PII/contextual disclosures require review. Keep public
  links unless they contain credentials, sensitive parameters, or explicit private
  identifiers. A public domain does not exempt the rest of its URL.
- Chinese and other non-Latin identities require explicit private dictionaries
  and human review; Rampart's model is not reliable coverage for these names.
- Scan code blocks, frontmatter, filenames, metadata, and quoted text too. Never
  treat attachments, images, EXIF, archives, or undecodable files as scanned text.
- Reports/receipts themselves are private artifacts: document hashes and offsets
  may reveal information. Do not post them publicly without review.
- Never call a scan “safe to publish.” Say “no findings under the selected rules”
  and disclose model coverage, unsupported inputs, and unresolved contextual risk.

## Configuration and optional model

Copy `assets/policy.example.json` as the public policy. Start a private profile
from `assets/private.example.json` **outside** the content tree. No real identities
are shipped in templates. See [configuration](references/cli.md#configuration).

Rules are deterministic. Optional ONNX inference is pinned through explicit
artifact checksums and an executable command. The Rampart bridge is opt-in; see
[offline Rampart setup](references/rampart.md). Required detector errors fail the
scan rather than silently downgrading to rules-only coverage.

## Verification

```sh
python3 -m unittest discover -s /path/to/privacy-guard/tests -v
```

This skill does not install hooks, scan the user's projects, download models,
publish content, or apply redactions merely because it has been loaded.
