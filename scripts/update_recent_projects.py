#!/usr/bin/env python3
"""Refresh only the marked README section from GitHub's public repositories API."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import html
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import urllib.request

USER = "basit3000"
START = "<!-- RECENT-PROJECTS:START -->"
END = "<!-- RECENT-PROJECTS:END -->"
ROOT = Path(__file__).resolve().parents[1]


def fetch_repositories() -> list[dict]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "basit3000-profile",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token := os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {token}"
    repositories = []
    page = 1
    while True:
        # This endpoint lists public repos, even with an authenticated request.
        url = f"https://api.github.com/users/{USER}/repos?type=owner&sort=pushed&per_page=100&page={page}"
        request = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(request, timeout=30) as response:
            batch = json.load(response)
        if not isinstance(batch, list) or not all(isinstance(repo, dict) for repo in batch):
            raise ValueError("Unexpected repository response")
        repositories.extend(batch)
        if len(batch) < 100:
            return repositories
        page += 1


def markdown_text(value: str) -> str:
    """Keep API-provided labels as text, including Markdown/HTML punctuation."""
    value = html.escape(" ".join(value.split()), quote=True)
    return re.sub(r"([\\`*_{}\[\]()#+.!|~>-])", r"\\\1", value)


def render_projects(repositories: list[dict]) -> str:
    eligible = []
    for repo in repositories:
        if repo.get("private") is not False or repo.get("fork") or repo.get("archived"):
            continue
        name = repo.get("name", "")
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", name) or name.lower() == USER:
            continue
        if repo.get("owner", {}).get("login", "").lower() != USER:
            continue
        pushed = repo.get("pushed_at")
        if not pushed:
            continue
        # Invalid dates fail the update instead of publishing misleading data.
        date = datetime.fromisoformat(pushed.replace("Z", "+00:00"))
        if date.tzinfo is None:
            raise ValueError("Repository push date has no timezone")
        eligible.append((date.astimezone(timezone.utc), name, repo))
    eligible.sort(key=lambda item: (item[0], item[1]), reverse=True)
    if not eligible:
        return f"Browse [my public repositories](https://github.com/{USER}?tab=repositories)."
    lines = []
    for date, name, repo in eligible[:3]:
        language = f" · {markdown_text(repo['language'])}" if repo.get("language") else ""
        lines.append(
            f"- **[{markdown_text(name)}](https://github.com/{USER}/{name})**"
            f"{language} · Last pushed {date:%Y-%m-%d}"
        )
    return "\n".join(lines)


def replace_section(readme: str, content: str) -> str:
    if readme.count(START) != 1 or readme.count(END) != 1:
        raise ValueError("README must contain exactly one pair of recent-project markers")
    before, remainder = readme.split(START)
    if END not in remainder:
        raise ValueError("Recent-project markers are out of order")
    _, after = remainder.split(END)
    return f"{before}{START}\n{content}\n{END}{after}"


def update_readme(path: Path) -> bool:
    # Preserve existing line endings and all content outside the markers.
    original = path.read_bytes().decode("utf-8")
    replace_section(original, "")  # Validate before making a network request.
    content = render_projects(fetch_repositories())
    replacement = replace_section(original, content)
    if "\r\n" in original:
        replacement = replacement.replace("\r\n", "\n").replace("\n", "\r\n")
    if replacement == original:
        return False
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as output:
            temporary = Path(output.name)
            output.write(replacement.encode("utf-8"))
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--readme", type=Path, default=ROOT / "README.md")
    args = parser.parse_args()
    try:
        changed = update_readme(args.readme)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(f"Recent projects update failed; README unchanged: {exc}", file=sys.stderr)
        return 1
    print("Updated recent projects." if changed else "Recent projects unchanged.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
