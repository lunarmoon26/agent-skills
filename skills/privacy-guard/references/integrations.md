# Publication integrations

## Forum skills (including lcz-forum)

The publishing skill retains its account/API and confirmation rules. Privacy Guard
does not read tokens or call forum APIs. Feed the exact final serialized title/body
payload to `scan --profile forum --json --stdin`; include quotes, signatures, edits, and
links. Resolve findings, rescan, and require exit 0 immediately before publishing
those same bytes. Check the actual body if the client transforms the serialization.

Do not upload drafts to a remote service merely to scan them. If contextual edits
are suggested by an agent, use masked content where possible and require review.
Attachments require their own inspection and may prevent publication approval.

## Personal blogs

Scan Markdown sources including YAML frontmatter, embedded HTML and code blocks:

```sh
python3 /path/to/privacy-guard/scripts/privacy_guard.py scan --profile blog --path ./_posts --policy public-policy.json --private /outside/site/private-profile.json
```

The scanner includes filenames but does not rename them. Scan publication-bound
generated text as a separate gate if layouts, plugins, feeds, or signatures add
content. It does not execute site plugins or parse all rendered formats. Validate
frontmatter/site builds and meaning after changes. Public author handles and contact
addresses need explicit narrow allow entries; internal domains and signed URL tokens
remain findings. Use a private profile outside the site's deploy root.

## Git

`scan --staged` inspects the index, not the working-tree version. Run it before
commit. `scan --outgoing --ref <ref>` defaults to full reachable history, not a
tip-only diff. Check every ref named in a push. A pre-push hook may invoke the CLI
for each local object ID from Git's stdin (skip all-zero deletion IDs); it must fail
on exit 1 **and** 2. Installation of hooks is an explicit user action and must
preserve existing hooks. No hooks are installed by this skill.

For first publication, omit `--base`. For incremental publication, only supply a
verified already-published base. Do not infer it from stale remote-tracking refs.
Protected CI helps catch errors but runs after upload. Local hooks are bypassable.
History redaction and credential rotation are separate approved workflows.

## Other agents and applications

Any agent can load SKILL.md and run the script by its absolute installed path.
Applications consume JSON reports and nonzero exits without an agent. No MCP or
OpenCode plugin is required. An application should control policy/configuration
and detector commands; untrusted draft content must never supply them.
