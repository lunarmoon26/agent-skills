# CLI contract

Status: Implemented. Python 3.10+, standard library only for rules and Git scanning.
Commands return JSON to stdout; diagnostic errors are generic and never include
input content or external detector stderr. Exit codes: `0` no findings and complete
requested text coverage; `1` unresolved findings; `2` invalid configuration,
incomplete coverage, unsupported input, or detector/runtime error.

## Scan

```sh
python3 scripts/privacy_guard.py scan --profile document --path article.md
python3 scripts/privacy_guard.py scan --profile blog --path ./_posts --policy policy.json --private /outside/project/identity.json
python3 scripts/privacy_guard.py scan --profile forum --json --stdin < final-payload.json
python3 scripts/privacy_guard.py scan --repo . --staged
python3 scripts/privacy_guard.py scan --repo . --outgoing --ref HEAD
```

`--path` and `--ref` repeat. Exactly one input mode is required: paths, stdin,
staged Git, or outgoing Git. Directory inputs include hidden files and do not honor
`.gitignore`: ignored files can still be published. `.git` administrative entries
are skipped. Symlinks, special files, oversize inputs, non-UTF-8/NUL-containing
files, known binary extensions (including UTF-8 SVG), Git submodules, and LFS pointers
produce incomplete-coverage issues. The scanner does not follow symlinks.

`--json` adds parsing of each file/stdin input as JSON and checks decoded keys,
string values, and key/value projections (e.g. `balance: 123`). This catches values
hidden by JSON Unicode escapes. Invalid JSON is incomplete coverage. `json_field`
sources use structural indexes, never private key names. Their offsets refer to
the decoded string/projection, not serialized JSON bytes. This option is read-only
and not supported for Git input. Duplicate findings across raw payload/fields are
intentional defense in depth. HTML entities, URL-encoded content, escaped strings
inside source code, and other embedded encodings are not comprehensively decoded.

Outgoing mode scans every unique blob in **every reachable commit tree**, including
deleted historical files, commit message, author/committer identity, and filenames.
It defaults to full history of HEAD; specify every ref being pushed. `--base`
excludes commits reachable from one explicitly trusted, already-published base.
No remote is contacted and no remote-tracking tip is assumed current. Incorrect
bases/ref selection can omit outgoing content. Annotated tag messages, notes,
external LFS objects, submodule content, images and metadata are not fully covered.
Annotated tags produce a coverage issue. Git filenames are checked even when
their content is unsupported; symlinks themselves produce unsupported-coverage
issues. Staged scans resolve the repository root even when invoked in a subdirectory.

Reports identify sources with opaque IDs and `kind`; offsets are zero-based
Unicode-code-point offsets in the decoded **original** text. Line numbers are
one-based. Filesystem filename checks use publication-relative names, not the
host's absolute home-directory prefix. `--show-paths` opts into actual paths/locations;
those can contain PII.
No snippets, matches, replacements, or private rule IDs are emitted. Labels/rule
IDs in private configuration should themselves avoid sensitive values. Findings
are bound to content + effective configuration + source identity and cannot be
reused after edits. `profile` selects the workflow label (code/blog/forum/document),
not an implicit exemption or a different default detection policy.

## Configuration

JSON `version: 1`; unknown keys are rejected. `--policy` is public configuration;
`--private` adds local private rules/allow entries. Actions and rules are merged;
duplicate custom rule IDs are rejected. There is no configuration autodiscovery.

A configured replacement covering an entire non-secret built-in/model finding
resolves that finding. Partial overlaps and other custom findings remain; secret
findings can never be suppressed by a replacement rule.

- `max_bytes`: per-input limit, 1–64 MiB (default 2 MiB).
- `actions`: category to `review`, `block`, or `replace`; replacement requires a
  rule-level template. Built-in categories cannot be silently disabled.
- `rules`: `{id, category, literal|pattern, action?, replacement?, ignore_case?}`.
  Exactly one matcher; Python regular expressions are trusted configuration and
  should be bounded. Defaults to case-sensitive matching and `review`.
- `allow`: `{category, literal, reason, kind?}`. Exact matched-value equality, no
  substring exemptions. `kind` scopes to `file`, `filename`, `stdin`, `git_blob`,
  `git_metadata`, `git_filename`, or `json_field`. Secret/credential categories cannot be allowed.
- `ner`: optional `{command: [executable, ...arguments], artifacts: {absolute_path:
  sha256}, timeout_seconds?, categories?}`. Each file's checksum is verified before
  inference. The command takes one JSON request on stdin and returns a JSON array
  of `{start, end, label, score?}` on stdout. It must preserve code-point offsets.
  Defaults to review; category names are `ner_<lowercase-label>`, except `SECRET`,
  `CREDENTIAL_URL`, and `SENSITIVE_URL_PARAMETER`, which always block. Unknown or invalid
  spans fail closed. `categories` optionally selects labels; omitted means all.

Default rules detect common token/key forms, password/auth assignments,
credential-bearing URLs and sensitive URL parameters, emails, phone candidates,
IPv4, validated US SSNs/payment cards, personal home-directory paths, and
account/balance/subscription statements in English/Chinese. Phone/IP/numeric
matches may be examples or version strings; review is intentional. These are
heuristics, not comprehensive secret/PII coverage. Public URLs are not blanked.

Private configuration is rejected inside input directories or Git worktrees
(including parent repositories), and if it is itself selected as an input.
For standalone files not in Git, keep it outside the publication directory by
convention: the CLI cannot infer an entire site's deploy root from one file.

## Approved application

```sh
python3 scripts/privacy_guard.py apply --path article.md --private /outside/project/identity.json --expect-sha256 DIGEST_FROM_SCAN --approve FINDING_ID
```

Only one regular UTF-8 file, in place. Requires the expected byte digest and IDs
for **every** finding; each must have action `replace`. Secret categories are never
auto-replaced. Filename findings and overlapping replacements require manual
editing. Candidate text is rescanned with the same policy/model and must have no
findings. JSON files must parse before and after; other formats require external
syntax/build validation. Empty replacements are permitted when explicitly configured.

The file is checked again before atomic replacement; mode bits are retained.
Concurrent writers cannot be fully locked across arbitrary editors: use a quiescent
file. No backup containing raw PII, reverse map, or approved-plan file is created.
Git index/history is never modified. No stdout contains original or rewritten text.

## Receipt limitations

`content_sha256`, `policy_sha256`, and `engine_sha256` bind checks to bytes,
configuration, and scanner source; coverage
reports whether NER ran. Timestamps are omitted for reproducibility. These are
local check receipts, not signatures, access controls, anonymity certificates, or
authorization to publish. Configured detector code/environment changes must be
pinned operationally as well as model assets. There is no persistent content cache.
