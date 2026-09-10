# Agent Skills

Personal skills for AI coding agents, following the [Agent Skills](https://agentskills.io/) format.

## Install locally

```sh
bunx skills add /path/to/agent-skills
```

## Install from GitHub

```sh
bunx skills add lunarmoon26/agent-skills
```

## Executable tools

The repository is also an [Agent Plugins 1.0](https://agent-plugins.org/) package. Its `photo_process` MCP tool uses [`@lunarmoon26/agent-skill-runtime`](https://github.com/lunarmoon26/agent-skill-runtime) to run the pinned Python bridge in `skills/photo-processing/skill-runtime.json`.

Prepare the exact PEP 723 dependency once before enabling the MCP server:

```sh
npx @lunarmoon26/agent-skill-runtime@0.1.0 prepare \
  --root . \
  --manifest skills/photo-processing/skill-runtime.json
```

Normal tool calls run `uv` offline. Agent Plugins clients read `mcp.json`; clients without Agent Plugins support can launch the same stdio server directly with the command declared there.

## Included skills

- `document-driven-development`
- `lightweight-architecture`
- `photo-processing`
- `research-driven-development`
- `tech-breakdown-in-chinese`

Each skill lives in `skills/<skill-name>/`, with scripts, references, tests, or eval fixtures where needed.
