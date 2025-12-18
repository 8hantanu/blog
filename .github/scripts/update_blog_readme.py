from __future__ import annotations
from collections import defaultdict

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Optional


WIKI_DIR = Path("wiki")
BLOG_REPO_README = Path("README.md")

BASE_URL = "https://8hantanu.net/wiki"


@dataclass(frozen=True)
class Post:
    title: str
    d: date
    relpath: str  # posix relative path within wiki repo, e.g. "self/travel.md"


TITLE_RE = re.compile(r"^\s*#\s+(.+?)\s*$")
DATE_RE = re.compile(r"^\s*\*\*(\d{4}-\d{2}-\d{2})\*\*\s*$")


def parse_post(md_path: Path) -> Optional[Post]:
    """
    A file is a blog post if it starts with:
      # Title
      **YYYY-MM-DD**
    (allowing leading blank lines)
    """
    try:
        text = md_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        # Ignore non-utf8 files
        return None

    lines = text.splitlines()

    # skip initial blank lines
    i = 0
    while i < len(lines) and lines[i].strip() == "":
        i += 1
    if i >= len(lines):
        return None

    m_title = TITLE_RE.match(lines[i])
    if not m_title:
        return None
    title = m_title.group(1).strip()

    i += 1
    # allow blank lines between title and date? spec says "followed by date"
    # but to be forgiving, skip blanks
    while i < len(lines) and lines[i].strip() == "":
        i += 1
    if i >= len(lines):
        return None

    m_date = DATE_RE.match(lines[i])
    if not m_date:
        return None

    yyyy_mm_dd = m_date.group(1)
    try:
        d = date.fromisoformat(yyyy_mm_dd)
    except ValueError:
        return None

    relpath = md_path.relative_to(WIKI_DIR).as_posix()
    return Post(title=title, d=d, relpath=relpath)


def to_blog_link(relpath: str) -> str:
    """
    If path is e.g. self/places/README.md -> https://8hantanu.net/wiki/self/places
    If path is e.g. self/travel.md        -> https://8hantanu.net/wiki/self/travel
    If path is README.md at root          -> https://8hantanu.net/wiki
    """
    p = Path(relpath)

    if p.name.lower() == "readme.md":
        if p.parent.as_posix() == ".":
            return BASE_URL
        return f"{BASE_URL}/{p.parent.as_posix()}"

    if p.suffix.lower() == ".md":
        no_ext = p.with_suffix("")
        return f"{BASE_URL}/{no_ext.as_posix()}"

    # fallback (shouldn't happen)
    return f"{BASE_URL}/{p.as_posix()}"


def collect_posts() -> list[Post]:
    posts: list[Post] = []
    for md in WIKI_DIR.rglob("*.md"):
        # ignore hidden-ish directories if you want; keeping it simple:
        post = parse_post(md)
        if post:
            posts.append(post)

    # latest -> oldest by date, tie-break by path for stability
    posts.sort(key=lambda p: (p.d, p.relpath), reverse=True)
    return posts


def render_blog_section(posts: list[Post]) -> str:
    lines: list[str] = ["# Shantanu's blog ✒️", "", "**Collection of the latest and greatest pages from the wiki 📖**", ""]

    posts_by_year: dict[int, list[Post]] = defaultdict(list)
    for p in posts:
        posts_by_year[p.d.year].append(p)

    # years already implicitly sorted desc because posts were sorted
    for year in sorted(posts_by_year.keys(), reverse=True):
        lines.append(f"## {year}")
        for p in posts_by_year[year]:
            link = to_blog_link(p.relpath)
            lines.append(f"- [{p.title}]({link})")
        lines.append("")  # blank line after each year

    return "\n".join(lines)


def replace_blog_section(readme_text: str, new_section: str) -> str:
    """
    Replace the README section that starts with a line exactly '# Blog'
    and continues until the next H1 ('# ') or end-of-file.
    If '# Blog' doesn't exist, append the section at the end (with spacing).
    """
    lines = readme_text.splitlines()

    # find '# Blog' line
    start = None
    for idx, line in enumerate(lines):
        if line.strip() == "# Blog":
            start = idx
            break

    if start is None:
        # append
        out = readme_text.rstrip() + "\n\n" + new_section.strip() + "\n"
        return out

    # find end: next H1 after start
    end = len(lines)
    for idx in range(start + 1, len(lines)):
        if lines[idx].startswith("# "):  # next H1
            end = idx
            break

    before = "\n".join(lines[:start]).rstrip()
    after = "\n".join(lines[end:]).lstrip()

    combined = ""
    if before:
        combined += before + "\n\n"
    combined += new_section.strip() + "\n"
    if after:
        combined += "\n" + after.rstrip() + "\n"
    return combined


def main() -> None:
    if not WIKI_DIR.exists():
        raise SystemExit(f"Expected wiki repo checked out at: {WIKI_DIR.resolve()}")

    posts = collect_posts()
    new_blog = render_blog_section(posts)

    existing = ""
    if BLOG_REPO_README.exists():
        existing = BLOG_REPO_README.read_text(encoding="utf-8")

    updated = replace_blog_section(existing, new_blog)
    BLOG_REPO_README.write_text(updated, encoding="utf-8")
    print(f"Found {len(posts)} blog posts. Updated {BLOG_REPO_README}.")


if __name__ == "__main__":
    main()
