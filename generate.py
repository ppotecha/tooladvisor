#!/usr/bin/env python3
"""
ToolAdvisor Article Generator
------------------------------
Generates SEO-optimized affiliate review articles using Claude API.
Drops finished HTML files into /articles/ and updates the articles index.

Usage:
  python scripts/generate.py "best AI invoicing tools for freelancers"
  python scripts/generate.py --batch scripts/keywords.txt
"""

import anthropic
import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────

API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
MODEL = "claude-sonnet-4-20250514"
ARTICLES_DIR = Path(__file__).parent.parent / "articles"
TEMPLATE_PATH = Path(__file__).parent.parent / "article-template.html"
INDEX_PATH = ARTICLES_DIR / "reviews.html"
SITEMAP_PATH = Path(__file__).parent.parent / "sitemap.xml"
SITE_URL = "https://tooladvisor.tech"

# ── Affiliate link map ─────────────────────────────────────────────────────────
# Add your real affiliate links here after signing up to each program.
# Sign up at: jasper.com/affiliates, copy.ai (ShareASale), zapier.com/partners,
#             notion.so/affiliates, clickup.com/affiliates, etc.

AFFILIATE_LINKS = {
    "Jasper": "https://jasper.ai?fpr=YOURCODE",
    "Copy.ai": "https://copy.ai?via=YOURCODE",
    "Notion AI": "https://notion.so?r=YOURCODE",
    "ClickUp": "https://clickup.com?fp_ref=YOURCODE",
    "Zapier": "https://zapier.com/referral/YOURCODE",
    "Make": "https://make.com?pc=YOURCODE",
    "Writesonic": "https://writesonic.com?fpr=YOURCODE",
    "Rytr": "https://rytr.me/?via=YOURCODE",
    "Descript": "https://descript.com?lmref=YOURCODE",
    "Synthesia": "https://synthesia.io?via=YOURCODE",
    "FreshBooks": "https://freshbooks.com?ref=YOURCODE",
    "QuickBooks": "https://quickbooks.intuit.com",
    "HubSpot": "https://hubspot.com?ref=YOURCODE",
    "Tidio": "https://tidio.com?r=YOURCODE",
    "Intercom": "https://intercom.com",
    "Loom": "https://loom.com/referral/YOURCODE",
    "Grammarly": "https://grammarly.com/referral/YOURCODE",
}

# ── Prompts ────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an expert content writer for ToolAdvisor, a site that reviews AI tools for small businesses.

Your articles are:
- Highly specific and practical (real tool names, real pricing, real use cases)
- SEO-optimized with natural keyword usage (never stuffed)
- Structured for skimmability (clear H2s, H3s, bullet points)
- Honest — include genuine pros and cons, not just hype
- Conversion-focused — guide readers toward a clear recommendation

Write in HTML using these components:

<div class="tldr"><strong>TL;DR</strong> [2-3 sentence summary with top pick]</div>

<div class="tool-card">
  <div class="tool-card-header">
    <span class="tool-name">Tool Name</span>
    <span class="tool-rating">⭐ 4.5/5</span>
  </div>
  <p class="tool-desc">One-line description</p>
  <div class="tool-pros-cons">
    <ul class="pros"><h4>Pros</h4><li>Point</li></ul>
    <ul class="cons"><h4>Cons</h4><li>Point</li></ul>
  </div>
  <a href="AFFILIATE_LINK" class="tool-cta" rel="sponsored noopener" target="_blank">Try [Tool Name] free →</a>
</div>

<table class="comparison-table">...</table>

Rules:
- Include a TL;DR box near the top
- Include 3-5 tool cards with real affiliate links where available
- Include one comparison table
- End with a clear "Bottom line" section with a top recommendation
- Write 1200-1800 words of body content
- Return ONLY the HTML body content (no <html>, <head>, <body> tags)
- Use H2 for major sections, H3 for subsections
"""

def make_article_prompt(keyword: str) -> str:
    return f"""Write a comprehensive, SEO-optimized review article for this keyword:

"{keyword}"

Use real tool names, real pricing (as of 2025), and real affiliate links from this map where relevant:
{json.dumps(AFFILIATE_LINKS, indent=2)}

Structure the article well. Include a TL;DR, 3-5 tool cards, a comparison table, and a strong conclusion with a recommendation."""

# ── Helpers ───────────────────────────────────────────────────────────────────

def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    return text[:80]

def estimate_read_time(html: str) -> int:
    words = len(re.sub(r'<[^>]+>', '', html).split())
    return max(3, round(words / 200))

def extract_title(keyword: str) -> str:
    """Turn a keyword into a proper title."""
    title = keyword.strip()
    if not any(title.lower().startswith(w) for w in ['best', 'top', 'how', 'what', 'why', 'is']):
        title = f"Best {title.title()}"
    year = datetime.now().year
    if str(year) not in title:
        title = f"{title} ({year})"
    return title

def generate_article(keyword: str, client: anthropic.Anthropic) -> dict:
    """Call Claude API and return article data."""
    print(f"  Generating: {keyword}")

    message = client.messages.create(
        model=MODEL,
        max_tokens=4000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": make_article_prompt(keyword)}]
    )

    body_html = message.content[0].text
    title = extract_title(keyword)

    # Extract a clean meta description from the first paragraph
    first_para = re.search(r'<p[^>]*>(.*?)</p>', body_html, re.DOTALL)
    meta_desc = ""
    if first_para:
        meta_desc = re.sub(r'<[^>]+>', '', first_para.group(1))[:155].strip()
    if not meta_desc:
        meta_desc = f"Honest comparison of {keyword}. Find the best tool for your small business."

    # Guess category from keyword
    category_map = {
        'writ': 'Content', 'copy': 'Content', 'blog': 'Content',
        'invoic': 'Finance', 'account': 'Finance', 'payment': 'Finance',
        'email': 'Email & Outreach', 'outreach': 'Email & Outreach',
        'design': 'Design', 'image': 'Design', 'video': 'Design',
        'schedul': 'Operations', 'automat': 'Operations', 'workflow': 'Operations',
        'support': 'Customer Support', 'chat': 'Customer Support',
        'data': 'Analytics', 'analyt': 'Analytics',
    }
    category = 'AI Tools'
    kw_lower = keyword.lower()
    for key, cat in category_map.items():
        if key in kw_lower:
            category = cat
            break

    return {
        "keyword": keyword,
        "title": title,
        "slug": slugify(title),
        "meta_description": meta_desc,
        "category": category,
        "body_html": body_html,
        "read_time": estimate_read_time(body_html),
        "date": datetime.now().strftime("%b %Y"),
    }

def render_article(article: dict, template: str) -> str:
    """Fill the HTML template with article data."""
    html = template
    html = html.replace("{{TITLE}}", article["title"])
    html = html.replace("{{META_DESCRIPTION}}", article["meta_description"])
    html = html.replace("{{CATEGORY}}", article["category"])
    html = html.replace("{{READ_TIME}}", str(article["read_time"]))
    html = html.replace("{{DATE}}", article["date"])
    html = html.replace("{{ARTICLE_BODY}}", article["body_html"])
    return html

def save_article(article: dict, template: str) -> Path:
    """Write article HTML to disk."""
    html = render_article(article, template)
    filename = f"{article['slug']}.html"
    path = ARTICLES_DIR / filename
    path.write_text(html, encoding="utf-8")
    print(f"  Saved: articles/{filename}")
    return path

def update_articles_index(articles: list[dict]):
    """Rebuild the articles/index.html with all articles listed."""
    if not INDEX_PATH.exists():
        print("  Warning: articles/reviews.html not found, skipping index update")
        return

    index_html = INDEX_PATH.read_text(encoding="utf-8")

    cards_html = ""
    for a in articles:
        cards_html += f"""
    <a href="/articles/{a['slug']}.html" class="article-card">
      <div class="article-card-body">
        <div class="article-tag">{a['category']}</div>
        <h2>{a['title']}</h2>
        <p>{a['meta_description']}</p>
        <div class="article-meta">
          <span>{a['read_time']} min read</span>
          <span>{a['date']}</span>
        </div>
        <span class="read-link">Read review →</span>
      </div>
    </a>"""

    index_html = re.sub(
        r'<!-- Generated articles will be listed here automatically by generate\.py -->.*?(?=\s*</div>\s*</div>)',
        f'<!-- Generated articles will be listed here automatically by generate.py -->{cards_html}',
        index_html,
        flags=re.DOTALL
    )
    INDEX_PATH.write_text(index_html, encoding="utf-8")
    print(f"  Updated articles index ({len(articles)} articles)")

def update_sitemap(slugs: list[str]):
    """Generate sitemap.xml for all articles."""
    now = datetime.now().strftime("%Y-%m-%d")
    urls = [f"""  <url>
    <loc>{SITE_URL}/</loc>
    <changefreq>weekly</changefreq>
    <priority>1.0</priority>
  </url>""",
    f"""  <url>
    <loc>{SITE_URL}/articles/reviews.html</loc>
    <changefreq>weekly</changefreq>
    <priority>0.9</priority>
  </url>"""]

    for slug in slugs:
        urls.append(f"""  <url>
    <loc>{SITE_URL}/articles/{slug}.html</loc>
    <lastmod>{now}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>""")

    sitemap = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{chr(10).join(urls)}
</urlset>"""
    SITEMAP_PATH.write_text(sitemap, encoding="utf-8")
    print(f"  Sitemap updated ({len(slugs)} article URLs)")

def load_existing_articles() -> list[dict]:
    """Scan articles/ dir for existing article metadata."""
    articles = []
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    for f in sorted(ARTICLES_DIR.glob("*.html")):
        if f.name == "index.html":
            continue
        content = f.read_text(encoding="utf-8")
        title_match = re.search(r'<title>(.*?) — ToolAdvisor</title>', content)
        desc_match = re.search(r'<meta name="description" content="([^"]+)"', content)
        tag_match = re.search(r'<span class="article-tag">([^<]+)</span>', content)
        time_match = re.search(r'<span>(\d+) min read</span>', content)
        date_match = re.search(r'<span>(\w+ \d{4})</span>', content)
        articles.append({
            "title": title_match.group(1) if title_match else f.stem,
            "slug": f.stem,
            "meta_description": desc_match.group(1) if desc_match else "",
            "category": tag_match.group(1) if tag_match else "AI Tools",
            "read_time": time_match.group(1) if time_match else "5",
            "date": date_match.group(1) if date_match else datetime.now().strftime("%b %Y"),
        })
    return articles

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Generate affiliate articles for ToolAdvisor")
    parser.add_argument("keyword", nargs="?", help="Keyword to write an article for")
    parser.add_argument("--batch", metavar="FILE", help="Path to a text file with one keyword per line")
    args = parser.parse_args()

    if not API_KEY:
        print("Error: ANTHROPIC_API_KEY environment variable not set.")
        print("Run: export ANTHROPIC_API_KEY=your_key_here")
        sys.exit(1)

    if not TEMPLATE_PATH.exists():
        print(f"Error: Template not found at {TEMPLATE_PATH}")
        sys.exit(1)

    ARTICLES_DIR.mkdir(exist_ok=True)
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    client = anthropic.Anthropic(api_key=API_KEY)

    # Gather keywords
    keywords = []
    if args.keyword:
        keywords.append(args.keyword)
    elif args.batch:
        batch_path = Path(args.batch)
        if not batch_path.exists():
            print(f"Error: Batch file not found: {args.batch}")
            sys.exit(1)
        keywords = [l.strip() for l in batch_path.read_text().splitlines() if l.strip() and not l.startswith('#')]
    else:
        print("Usage: python scripts/generate.py \"your keyword here\"")
        print("       python scripts/generate.py --batch scripts/keywords.txt")
        sys.exit(0)

    print(f"\nGenerating {len(keywords)} article(s)...\n")
    new_articles = []

    for keyword in keywords:
        try:
            article = generate_article(keyword, client)
            save_article(article, template)
            new_articles.append(article)
        except Exception as e:
            print(f"  Error generating '{keyword}': {e}")

    # Rebuild index and sitemap with all articles (existing + new)
    all_articles = load_existing_articles()
    update_articles_index(all_articles)
    update_sitemap([a["slug"] for a in all_articles])

    print(f"\nDone. Generated {len(new_articles)} article(s).")
    print("Next: git add . && git commit -m 'Add articles' && git push")

if __name__ == "__main__":
    main()
