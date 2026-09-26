#!/usr/bin/env python3
"""
Dynamic tag extractor for Principal Tech Editor.
Scans markdown frontmatter in $WIKI_PATH/raw/articles and blog posts directory.
Based on extract-tags.mjs, implemented in pure Python (no external dependencies required).
"""

import os
import sys
import re
import json
import argparse
import subprocess
from pathlib import Path

# Baseline fallback tags from canonical taxonomy in case wiki directory is unavailable
FALLBACK_TAGS = [
    "agents", "agi", "ai", "ai-infrastructure", "ai-policy", "ai-safety",
    "andrej-karpathy", "andrew-ng", "anthropic", "ar-glasses", "boris-cherny",
    "build-log", "career", "cisco", "computational-irreducibility", "cyberhud",
    "dario-amodei", "deepseek", "demis-hassabis", "enterprise-software",
    "entrepreneurship", "fei-fei-li", "foundation-models", "harrison-chase",
    "ilya-sutskever", "information-theory", "ios-development", "jagged-intelligence",
    "jensen-huang", "john-schulman", "langchain", "linux", "llm-scaling",
    "local-llm", "machine-learning", "matt-shumer", "mcp", "memory-system",
    "meta", "miri", "neuroscience", "nvidia", "ollama", "open-source", "openai",
    "openclaw", "physics", "pydantic", "rag", "reinforcement-learning",
    "research", "richard-sutton", "robotics", "sam-altman", "self-hosted",
    "software-engineering", "stephen-wolfram", "system-architecture", "vllm",
    "world-models", "yann-lecun", "yuval-noah-harari"
]

def parse_frontmatter_tags(content: str) -> list[str]:
    """Extract tags list from YAML frontmatter without external yaml dependencies."""
    match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return []
    
    fm = match.group(1)
    tags = []
    
    # Check block list format:
    # tags:
    #   - tag1
    #   - tag2
    block_match = re.search(r"^tags:\s*\n((?:\s*-\s*[^\n]+\n)+)", fm, re.MULTILINE)
    if block_match:
        for line in block_match.group(1).splitlines():
            clean = re.sub(r"^\s*-\s*", "", line).strip("\"' \t")
            if clean:
                tags.append(clean)
        return tags

    # Check inline list format:
    # tags: [tag1, tag2]
    inline_match = re.search(r"^tags:\s*\[(.*?)\]", fm, re.MULTILINE)
    if inline_match:
        for t in inline_match.group(1).split(","):
            clean = t.strip("\"' \t")
            if clean:
                tags.append(clean)
        return tags

    return tags

def get_existing_tags(dirs: list[str] | None = None, include_fallback: bool = True) -> list[str]:
    """Scan markdown files across provided directories and return sorted list of unique tags."""
    if dirs is None:
        wiki_env = os.environ.get("WIKI_PATH")
        wiki_root = Path(wiki_env).expanduser() if wiki_env else Path.home() / "Workspace/lunarmoon26.github.io/_wiki"
        if not wiki_root.exists():
            wiki_root = Path.home() / "wiki"

        dirs = [
            str(wiki_root / "raw/articles"),
            str(Path.home() / "Workspace/lunarmoon26.github.io/_posts")
        ]

    found_tags = set()
    scanned_files = 0

    for d in dirs:
        dir_path = Path(d).expanduser().resolve()
        if not dir_path.is_dir():
            continue

        for fpath in dir_path.glob("*.md"):
            try:
                text = fpath.read_text(encoding="utf-8", errors="ignore")
                tags = parse_frontmatter_tags(text)
                for t in tags:
                    found_tags.add(t)
                scanned_files += 1
            except Exception:
                continue

    if not found_tags and include_fallback:
        return sorted(list(set(FALLBACK_TAGS)))

    combined = set(found_tags)
    if include_fallback:
        combined.update(FALLBACK_TAGS)

    return sorted(list(combined))

def main():
    parser = argparse.ArgumentParser(description="Extract existing tags from wiki and blog markdown files.")
    parser.add_argument("--wiki-path", help="Path to wiki root directory")
    parser.add_argument("--dirs", nargs="*", help="Specific directories to scan for .md files")
    parser.add_argument("--no-fallback", action="store_true", help="Exclude baseline fallback tags")
    parser.add_argument("--copy", action="store_true", help="Copy JSON result to system clipboard (pbcopy/xclip)")
    parser.add_argument("--plain", action="store_true", help="Output as plain newline-separated text")

    args = parser.parse_args()

    target_dirs = args.dirs
    if not target_dirs:
        wiki_root = Path(args.wiki_path).expanduser() if args.wiki_path else (
            Path(os.environ["WIKI_PATH"]).expanduser() if "WIKI_PATH" in os.environ else (
                Path.home() / "Workspace/lunarmoon26.github.io/_wiki"
            )
        )
        target_dirs = [
            str(wiki_root / "raw/articles"),
            str(Path.home() / "Workspace/lunarmoon26.github.io/_posts")
        ]

    tags = get_existing_tags(target_dirs, include_fallback=not args.no_fallback)

    if args.plain:
        out = "\n".join(tags)
    else:
        out = json.dumps(tags, indent=2)

    print(out)

    if args.copy:
        try:
            if sys.platform == "darwin":
                subprocess.run(["pbcopy"], input=json.dumps(tags).encode("utf-8"), check=True)
                print("\nCopied to clipboard (pbcopy).", file=sys.stderr)
            elif sys.platform.startswith("linux"):
                subprocess.run(["xclip", "-selection", "clipboard"], input=json.dumps(tags).encode("utf-8"), check=True)
                print("\nCopied to clipboard (xclip).", file=sys.stderr)
        except Exception as e:
            print(f"\nCould not copy to clipboard: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
