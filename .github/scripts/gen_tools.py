#!/usr/bin/env python3
"""Regenerate the Public Tools and Forks tables in README.md from the live API.

Run by .github/workflows/update-tools.yml on a schedule (and on demand). It
rewrites only the regions between the <!-- TOOLS:START/END --> and
<!-- FORKS:START/END --> markers, so the hand-written header, About Me and
metrics footer are never touched.

Design notes
------------
* Public repos only: the /users/{user}/repos endpoint never returns private
  repos, so nothing private can leak onto the profile.
* Tools  = public, non-fork repos with a description (or a curated override).
  Forks  = public, fork repos with a description (or an override).
  The profile repo and archived repos are skipped, plus anything in SKIP.
* Star badges are shields.io *static* badges with the count baked in from the
  API each run. Static badges always render (the live github/stars endpoint can
  cache an "invalid" state), and we control the color so the white count stays
  legible: deep green for tools, dark grey for forks.
* To customise how a repo shows without editing its GitHub description, add an
  entry to OVERRIDES. To hide a public repo, add its name to SKIP (or drop its
  description / archive it).
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

OWNER = "0xbartita"
README = Path("README.md")

TOOLS_COLOR = "0a7d2c"   # deep green — readable white digits
FORKS_COLOR = "484f58"   # dark grey  — readable white digits

# Public repos never shown as tools/forks (the profile repo is always skipped).
SKIP = {OWNER.lower()}

# Curated display overrides, keyed by lowercased repo name.
# "desc" pins the table description; "name" pins the displayed link text.
OVERRIDES: dict[str, dict[str, str]] = {
    "h1-asset-fetcher": {
        "desc": "Fetch, download & decompile Android/iOS/Exe assets from HackerOne bug bounty programs",
    },
    "cookie-swapper": {
        "desc": "Burp Suite extension — auto-apply session tokens to all Repeater tabs. No more manual cookie replacement",
    },
    "h1-monitor": {
        "desc": "Self-hosted HackerOne monitor bot — watches public and private programs for scope changes and pushes them to your Telegram, 24/7",
    },
    "ioscpy-windows": {
        "desc": "Windows port — mirror & control a jailbroken iPhone over USB",
    },
    "netwraith": {
        "desc": "iOS traffic-interception framework — routes all device HTTP/HTTPS through Burp Suite via a system-wide VPN tunnel",
    },
    "trollvnc": {
        "desc": "VNC server for iOS — remote screen access & control",
    },
    "ipatool": {
        "desc": 'ipatool with a keyring auth fix — resolves the "item could not be found in the keyring" error',
    },
}


def fetch_repos() -> list[dict]:
    """All public repos owned by OWNER (forks included), via the gh CLI."""
    out = subprocess.check_output(
        ["gh", "api", f"users/{OWNER}/repos?per_page=100&type=owner", "--paginate"],
        text=True,
    )
    # gh --paginate concatenates array pages into one JSON array.
    return json.loads(out)


def cell(text: str) -> str:
    """Make a string safe for a Markdown table cell (single line, escaped pipes)."""
    return " ".join((text or "").split()).replace("|", "\\|")


def badge(repo: str, count: int, color: str) -> str:
    label = "%E2%98%85"  # ★
    url = f"https://img.shields.io/badge/{label}-{count}-{color}?style=flat-square"
    return f"[![Stars]({url})](https://github.com/{OWNER}/{repo}/stargazers)"


def row(repo: dict, color: str) -> str:
    name = repo["name"]
    ov = OVERRIDES.get(name.lower(), {})
    disp = ov.get("name", name)
    desc = ov.get("desc") or repo.get("description") or ""
    stars = repo.get("stargazers_count", 0)
    return (
        f"| [**{disp}**](https://github.com/{OWNER}/{name}) "
        f"| {cell(desc)} | {badge(name, stars, color)} |"
    )


def table(repos: list[dict], head: str, color: str) -> str:
    lines = [f"| {head} | Description | Stars |", "|------|-------------|:-----:|"]
    if repos:
        lines += [row(r, color) for r in repos]
    else:
        lines.append("| _nothing here yet_ | | |")
    return "\n".join(lines)


def splice(text: str, tag: str, body: str) -> str:
    start, end = f"<!-- {tag}:START -->", f"<!-- {tag}:END -->"
    if start not in text or end not in text:
        raise SystemExit(f"markers for {tag} not found in README.md")
    pat = re.compile(re.escape(start) + r".*?" + re.escape(end), re.S)
    return pat.sub(f"{start}\n{body}\n{end}", text, count=1)


def main() -> None:
    repos = [
        r for r in fetch_repos()
        if not r.get("private")
        and not r.get("archived")
        and r["name"].lower() not in SKIP
        and ((r.get("description") or "").strip() or r["name"].lower() in OVERRIDES)
    ]
    key = lambda r: (-r.get("stargazers_count", 0), r["name"].lower())
    tools = sorted([r for r in repos if not r.get("fork")], key=key)
    forks = sorted([r for r in repos if r.get("fork")], key=key)

    text = README.read_text()
    text = splice(text, "TOOLS", table(tools, "Tool", TOOLS_COLOR))
    text = splice(text, "FORKS", table(forks, "Project", FORKS_COLOR))
    README.write_text(text)

    print(f"Tools: {[r['name'] for r in tools]}")
    print(f"Forks: {[r['name'] for r in forks]}")


if __name__ == "__main__":
    main()
