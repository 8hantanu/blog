from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Optional
import re


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
        return None

    lines = text.splitlines()

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
    while i < len(lines) and lines[i].strip() == "":
        i += 1
    if i >= len(lines):
        return None

    m_date = DATE_RE.match(lines[i])
    if not m_date:
        return None

    try:
        d = date.fromisoformat(m_date.group(1))
    except ValueError:
        return None

    relpath = md_path.relative_to(WIKI_DIR).as_posix()
    return Post(title=title, d=d, relpath=relpath)


def to_blog_link(relpath: str) -> str:
    """
    Convert a wiki markdown path into a public URL.
    """
    p = Path(relpath)

    if p.name.lower() == "readme.md":
        if p.parent.as_posix() == ".":
            return BASE_URL
        return f"{BASE_URL}/{p.parent.as_posix()}"

    if p.suffix.lower() == ".md":
        return f"{BASE_URL}/{p.with_suffix('').as_posix()}"

    return f"{BASE_URL}/{p.as_posix()}"


def collect_posts() -> list[Post]:
    posts: list[Post] = []

    for md in WIKI_DIR.rglob("*.md"):
        post = parse_post(md)
        if post:
            posts.append(post)

    posts.sort(key=lambda p: (p.d, p.relpath), reverse=True)
    return posts


def render_blog_section(posts: list[Post]) -> str:
    lines: list[str] = [
        "# Shantanu's blog",
        "",
        "**Collection of the latest and greatest pages from the wiki**",
        "",
    ]

    posts_by_year: dict[int, list[Post]] = defaultdict(list)
    for p in posts:
        posts_by_year[p.d.year].append(p)

    for year in sorted(posts_by_year.keys(), reverse=True):
        lines.append(f"## {year}")
        for p in posts_by_year[year]:
            link = to_blog_link(p.relpath)
            lines.append(f"- [{p.title}]({link})")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    if not WIKI_DIR.exists():
        raise SystemExit(
            f"Expected wiki repo checked out at: {WIKI_DIR.resolve()}"
        )

    posts = collect_posts()
    content = render_blog_section(posts)

    # Explicitly remove README.md (optional, but matches your requirement)
    if BLOG_REPO_README.exists():
        BLOG_REPO_README.unlink()

    # Recreate README.md from scratch
    BLOG_REPO_README.write_text(content, encoding="utf-8")

    print(f"Found {len(posts)} blog posts. Recreated {BLOG_REPO_README}.")


if __name__ == "__main__":
    main()
