#!/usr/bin/env python3
"""Refresh the static star-count badges in README.md from the live GitHub API.

The badges are shields.io *static* badges (`badge/stars-<N>-<color>`), so they
always render — unlike the live `github/stars` endpoint, which can get stuck on
a cached "invalid". This script keeps the baked-in count current.

Safe by construction: it only rewrites the digits inside a `badge/stars-<N>-`
segment, and only on a line that links to the matching repo.
"""
import re
import subprocess
from pathlib import Path

OWNER = "0xbartita"
REPOS = ["h1-asset-fetcher", "Cookie-Swapper"]


def stars(repo: str) -> int:
    out = subprocess.check_output(
        ["gh", "api", f"repos/{OWNER}/{repo}", "--jq", ".stargazers_count"],
        text=True,
    )
    return int(out.strip())


def main() -> None:
    readme = Path("README.md")
    lines = readme.read_text().splitlines(keepends=True)
    counts = {repo: stars(repo) for repo in REPOS}

    changed = False
    for i, line in enumerate(lines):
        for repo, n in counts.items():
            if f"github.com/{OWNER}/{repo}" in line:
                new = re.sub(r"(badge/stars-)\d+(-)", rf"\g<1>{n}\g<2>", line)
                if new != line:
                    lines[i] = new
                    changed = True

    if changed:
        readme.write_text("".join(lines))
        print("Updated star counts:", counts)
    else:
        print("Star counts already current:", counts)


if __name__ == "__main__":
    main()
