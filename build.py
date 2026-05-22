#!/usr/bin/env python3
"""Personal blog static site generator.

Reads Markdown files from content/, renders them with Jinja2 templates,
generates a static site (HTML + RSS + search index) in output/.
"""

import os
import re
import json
import shutil
import datetime
from pathlib import Path

import yaml
import markdown
from jinja2 import Environment, FileSystemLoader

# ── Paths ────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent
CONTENT = ROOT / "content"
TEMPLATES = ROOT / "templates"
STATIC = ROOT / "static"
OUTPUT = ROOT / "output"

# ── Config ───────────────────────────────────────────────────────────
with open(ROOT / "config.yaml", encoding="utf-8") as fh:
    CFG = yaml.safe_load(fh)

SITE = CFG["site"]

# ── Jinja2 ───────────────────────────────────────────────────────────
env = Environment(loader=FileSystemLoader(str(TEMPLATES)), autoescape=True)
env.globals["site"] = SITE


def md_to_html(text):
    """Convert Markdown text to HTML with standard extensions."""
    return markdown.markdown(
        text,
        extensions=[
            "extra",
            "fenced_code",
            "codehilite",
            "toc",
            "tables",
            "sane_lists",
            "footnotes",
            "admonition",
        ],
        extension_configs={
            "codehilite": {
                "css_class": "highlight",
                "guess_lang": False,
            },
            "toc": {
                "toc_class": "toc",
                "permalink": True,
            },
        },
    )


# ── Frontmatter parsing ─────────────────────────────────────────────
RE_FM = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def parse_md(filepath):
    """Read a Markdown file, return (frontmatter_dict, html_body)."""
    raw = filepath.read_text(encoding="utf-8")
    m = RE_FM.match(raw)
    if m:
        fm = yaml.safe_load(m.group(1)) or {}
        body = raw[m.end():]
    else:
        fm = {}
        body = raw

    html = md_to_html(body)
    return fm, html


# ── Content loading ──────────────────────────────────────────────────
def load_all_posts():
    """Walk content/posts/, parse each .md file, return list of post dicts."""
    posts = []
    posts_dir = CONTENT / "posts"
    if not posts_dir.exists():
        return posts

    for fpath in sorted(posts_dir.iterdir()):
        if fpath.suffix.lower() not in (".md", ".markdown"):
            continue
        fm, html = parse_md(fpath)
        slug = fm.get("slug", fpath.stem)

        published = fm.get("date", datetime.date.today())
        if isinstance(published, datetime.datetime):
            published = published.date()
        elif isinstance(published, str):
            try:
                published = datetime.date.fromisoformat(published)
            except ValueError:
                published = datetime.date.today()

        post = {
            "title": fm.get("title", fpath.stem),
            "slug": slug,
            "date": published,
            "tags": fm.get("tags", []),
            "description": fm.get("description", ""),
            "draft": fm.get("draft", False),
            "content": html,
            "url": f"/posts/{slug}/",
        }
        posts.append(post)

    posts.sort(key=lambda p: p["date"], reverse=True)
    return posts


def load_page(slug):
    """Load a top-level page (about.md, etc.)."""
    fpath = CONTENT / f"{slug}.md"
    if not fpath.exists():
        return None
    fm, html = parse_md(fpath)
    return {
        "title": fm.get("title", slug),
        "content": html,
        "url": f"/{slug}/",
        "description": fm.get("description", ""),
    }


def collect_tags(posts):
    """Build {tag: [post, ...]} from a list of posts."""
    tags = {}
    for p in posts:
        for t in p.get("tags", []):
            tags.setdefault(t, []).append(p)
    return dict(sorted(tags.items()))


# ── RSS ──────────────────────────────────────────────────────────────
def build_rss(posts):
    """Generate an RSS 2.0 feed."""
    now = datetime.datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0000")
    items = []
    for p in posts[:20]:
        items.append(f"""\
    <item>
      <title>{p['title']}</title>
      <link>{SITE['url']}/posts/{p['slug']}/</link>
      <guid>{SITE['url']}/posts/{p['slug']}/</guid>
      <pubDate>{p['date'].strftime('%a, %d %b %Y %H:%M:%S +0000')}</pubDate>
      <description><![CDATA[{p.get('description', p['content'][:300])}]]></description>
    </item>""")

    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>{SITE['title']}</title>
    <link>{SITE['url']}</link>
    <description>{SITE.get('description', '')}</description>
    <language>{SITE.get('lang', 'zh-cn')}</language>
    <atom:link href="{SITE['url']}/rss.xml" rel="self" type="application/rss+xml"/>
    <lastBuildDate>{now}</lastBuildDate>
{chr(10).join(items)}
  </channel>
</rss>"""
    return rss


# ── Search index ─────────────────────────────────────────────────────
def build_search_index(posts):
    """Generate a JSON search index."""
    idx = []
    for p in posts:
        idx.append({
            "title": p["title"],
            "url": p["url"],
            "tags": p["tags"],
            "date": str(p["date"]),
            "description": p.get("description", ""),
            "content": re.sub(r"<[^>]+>", "", p["content"])[:500],
        })
    return idx


# ── Sitemap ──────────────────────────────────────────────────────────
def build_sitemap(posts, pages):
    urls = [f"""\
  <url>
    <loc>{SITE['url']}/</loc>
    <priority>1.0</priority>
  </url>"""]

    for p in posts:
        urls.append(f"""\
  <url>
    <loc>{SITE['url']}/posts/{p['slug']}/</loc>
    <lastmod>{p['date']}</lastmod>
    <priority>0.8</priority>
  </url>""")

    for name, _ in pages:
        urls.append(f"""\
  <url>
    <loc>{SITE['url']}/{name}/</loc>
    <priority>0.6</priority>
  </url>""")

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{chr(10).join(urls)}
</urlset>"""


# ── Render & write ───────────────────────────────────────────────────
def render(template_name, **kwargs):
    return env.get_template(template_name).render(**kwargs)


def write_html(path, html):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")


def copy_static():
    """Copy static/ into output/."""
    dst = OUTPUT / "static"
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(STATIC, dst)
    for item in STATIC.iterdir():
        dest = OUTPUT / item.name
        if item.is_dir():
            shutil.copytree(item, dest, dirs_exist_ok=True)
        else:
            shutil.copy2(item, dest)


def copy_cname():
    """Copy CNAME file if it exists (for custom domain support)."""
    cname = ROOT / "CNAME"
    if cname.exists():
        shutil.copy2(cname, OUTPUT / "CNAME")


# ── Main ─────────────────────────────────────────────────────────────
def main():
    print("Building blog ...")

    # Clean and create output directory
    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    OUTPUT.mkdir(parents=True)

    # Load content
    posts = load_all_posts()
    print("  [1/9] Posts loaded:", len(posts))

    # Filter drafts
    published = [p for p in posts if not p["draft"]]
    drafts = [p for p in posts if p["draft"]]
    if drafts:
        print("  [ ] Drafts skipped:", len(drafts))

    tags = collect_tags(published)
    search_index = build_search_index(published)

    # Pages
    about = load_page("about")
    pages = []
    if about:
        pages.append(("about", about))

    # Homepage
    idx_html = render("index.html", posts=published, tags=tags)
    write_html(OUTPUT / "index.html", idx_html)
    print("  [2/9] index.html")

    # Pagination
    per_page = SITE.get("posts_per_page", 10)
    total_pages = max(1, (len(published) + per_page - 1) // per_page)
    for pg in range(total_pages):
        start = pg * per_page
        end = start + per_page
        page_posts = published[start:end]
        p_html = render("index.html", posts=page_posts, tags=tags, page=pg + 1, total_pages=total_pages)
        if pg == 0:
            pass
        else:
            dir_p = OUTPUT / f"page/{pg + 1}"
            dir_p.mkdir(parents=True, exist_ok=True)
            (dir_p / "index.html").write_text(p_html, encoding="utf-8")

    # Post pages
    for p in published:
        post_html = render("post.html", post=p, tags=tags)
        out = OUTPUT / "posts" / p["slug"] / "index.html"
        write_html(out, post_html)
    print("  [3/9] Post pages:", len(published))

    # Tags index page
    tags_html = render("tags.html", tags=tags)
    write_html(OUTPUT / "tags" / "index.html", tags_html)
    print("  [4/9] tags/index.html")

    # Individual tag pages
    for tag_name, tag_posts in tags.items():
        t_html = render("tag.html", tag=tag_name, posts=tag_posts, tags=tags)
        write_html(OUTPUT / "tags" / tag_name / "index.html", t_html)

    # About page
    if about:
        ab_html = render("about.html", page=about, tags=tags)
        write_html(OUTPUT / "about" / "index.html", ab_html)
        print("  [5/9] about/index.html")

    # RSS
    rss = build_rss(published)
    (OUTPUT / "rss.xml").write_text(rss, encoding="utf-8")
    print("  [6/9] rss.xml")

    # Search index
    (OUTPUT / "search-index.json").write_text(
        json.dumps(search_index, ensure_ascii=False), encoding="utf-8"
    )
    print("  [7/9] search-index.json")

    # Sitemap
    sitemap = build_sitemap(published, pages)
    (OUTPUT / "sitemap.xml").write_text(sitemap, encoding="utf-8")
    print("  [8/9] sitemap.xml")

    # Static files & CNAME
    copy_static()
    copy_cname()
    print("  [9/9] Static files copied")

    print("Build complete! Output in output/")


if __name__ == "__main__":
    main()
