#!/usr/bin/env python3
"""
ToolAdvisor — Article Fixer
----------------------------
Fixes titles and categories in existing articles WITHOUT regenerating them.
Zero API calls. Zero cost. Runs in seconds.

Usage:
  python scripts/fix_articles.py              # Fix all articles
  python scripts/fix_articles.py --titles     # Fix titles only
  python scripts/fix_articles.py --categories # Fix categories only
  python scripts/fix_articles.py --preview    # Preview changes without saving
"""

import re
import argparse
from pathlib import Path
from datetime import datetime

ARTICLES_DIR = Path(__file__).parent.parent / "articles"
INDEX_PATH = ARTICLES_DIR / "reviews.html"
KEYWORDS_PATH = Path(__file__).parent / "keywords.txt"

# ── Title logic (same as generate.py) ─────────────────────────────────────────

BRANDS = [
    'ActiveCampaign', 'ClickUp', 'Apollo.io', 'AdCreative.ai', 'Reclaim.ai',
    'HubSpot', 'Manychat', 'PandaDoc', 'ElevenLabs', 'Murf AI', 'Brevo',
    'AWeber', 'Reply.io', 'Instantly', 'Leadpages', 'Zapier', 'Tidio',
    'Intercom', 'FreshBooks', 'QuickBooks', 'Grammarly', 'Notion', 'Loom',
    'Descript', 'Synthesia', 'Castmagic', 'Brand24', 'Folk', 'Close',
    'Writesonic', 'Copy.ai', 'ChatGPT', 'OpenAI', 'Canva', 'Midjourney',
    'ClickFunnels', 'DocuSign',
]

def fix_title(keyword: str) -> str:
    title = keyword.strip()
    kw_lower = title.lower()

    comparison_words = ['vs', 'versus', 'compared', 'comparison', 'or ']
    review_words = ['review', 'is it worth', 'worth it', 'pricing', 'alternative']
    how_words = ['how to', 'how do', 'what is', 'what are', 'why ', 'when to']
    already_titled = any(kw_lower.startswith(w) for w in ['best', 'top', 'the ', 'why ', 'how ', 'what ', 'is '])

    is_comparison = any(w in kw_lower for w in comparison_words)
    is_review = any(w in kw_lower for w in review_words)
    is_how = any(w in kw_lower for w in how_words)

    if not already_titled and not is_comparison and not is_review and not is_how:
        title = f"Best {title}"

    titled = title.title()
    for brand in BRANDS:
        titled = re.sub(re.escape(brand), brand, titled, flags=re.IGNORECASE)
    for word in [' Vs ', ' And ', ' For ', ' The ', ' Of ', ' In ', ' To ', ' A ', ' An ', ' Or ']:
        titled = titled.replace(word, word.lower())
    titled = titled[0].upper() + titled[1:] if titled else titled

    year = datetime.now().year
    if str(year) not in titled:
        titled = f"{titled} ({year})"

    return titled


def get_category(keyword: str) -> str:
    kw = keyword.lower()
    if any(w in kw for w in ['email', 'activecampaign', 'brevo', 'aweber', 'mailchimp',
                               'newsletter', 'cold email', 'instantly', 'reply.io',
                               'outreach', 'follow-up', 'follow up']):
        return 'Email'
    if any(w in kw for w in ['invoice', 'account', 'bookkeep', 'financ', 'payment',
                               'expense', 'freshbooks', 'quickbooks', 'tax']):
        return 'Finance'
    if any(w in kw for w in ['automat', 'zapier', 'make', 'workflow', 'schedul',
                               'project', 'clickup', 'notion', 'reclaim', 'task',
                               'meeting', 'calendar']):
        return 'Automation'
    if any(w in kw for w in ['chat', 'support', 'tidio', 'intercom', 'live chat',
                               'helpdesk', 'customer service']):
        return 'Customer Support'
    if any(w in kw for w in ['crm', 'sales', 'lead', 'apollo', 'hubspot', 'folk',
                               'close', 'pandadoc', 'prospect', 'pipeline']):
        return 'Sales'
    if any(w in kw for w in ['video', 'audio', 'voice', 'podcast', 'loom', 'descript',
                               'murf', 'eleven', 'castmagic', 'voiceover', 'transcript']):
        return 'Video'
    if any(w in kw for w in ['design', 'image', 'graphic', 'canva', 'adcreative',
                               'ad creative', 'social media', 'visual', 'midjourney',
                               'logo', 'banner', 'landing page', 'leadpages', 'manychat']):
        return 'Design'
    if any(w in kw for w in ['analyt', 'data', 'report', 'dashboard', 'insight',
                               'brand24', 'monitor']):
        return 'Analytics'
    if any(w in kw for w in ['writ', 'copy', 'blog', 'content', 'seo', 'article',
                               'grammarly', 'writesonic', 'rytr']):
        return 'Writing'
    return 'AI Tools'


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    return text[:80]


def load_keywords() -> list[str]:
    keywords = []
    for line in KEYWORDS_PATH.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith('#'):
            keywords.append(line)
    return keywords


def fix_article(path: Path, keyword: str, fix_title_flag: bool, fix_cat_flag: bool, preview: bool) -> dict:
    content = path.read_text(encoding='utf-8')
    original = content
    changes = []

    new_title = fix_title(keyword)
    new_category = get_category(keyword)

    if fix_title_flag:
        # Fix <title> tag
        content = re.sub(
            r'<title>.*?— ToolAdvisor</title>',
            f'<title>{new_title} — ToolAdvisor</title>',
            content
        )
        # Fix <h1> tag
        content = re.sub(
            r'<h1>(.*?)</h1>',
            f'<h1>{new_title}</h1>',
            content,
            count=1
        )
        if content != original:
            changes.append(f"  Title → {new_title}")

    if fix_cat_flag:
        # Fix article-pill in the article itself
        content = re.sub(
            r'<div class="article-pill">[^<]*</div>',
            f'<div class="article-pill">{new_category}</div>',
            content,
            count=1
        )
        if content != original:
            changes.append(f"  Category → {new_category}")

    if not preview and content != original:
        path.write_text(content, encoding='utf-8')

    return {
        'keyword': keyword,
        'slug': path.stem,
        'title': new_title,
        'category': new_category,
        'changed': content != original,
        'changes': changes,
    }


def rebuild_reviews_index(articles: list[dict], preview: bool):
    """Rebuild the cards in reviews.html with correct titles and categories."""
    if not INDEX_PATH.exists():
        print("  Warning: articles/reviews.html not found")
        return

    index_html = INDEX_PATH.read_text(encoding='utf-8')

    cards_html = ""
    for a in articles:
        read_time = "7"
        date = datetime.now().strftime("%b %Y")

        # Try to extract read time and date from existing article file
        article_path = ARTICLES_DIR / f"{a['slug']}.html"
        if article_path.exists():
            art = article_path.read_text(encoding='utf-8')
            rt = re.search(r'<span>(\d+) min read</span>', art)
            dt = re.search(r'<span>(\w+ \d{4})</span>', art)
            if rt: read_time = rt.group(1)
            if dt: date = dt.group(1)

            # Get meta description
            meta = re.search(r'<meta name="description" content="([^"]+)"', art)
            meta_desc = meta.group(1) if meta else f"Review of {a['keyword']} for small businesses."
        else:
            meta_desc = f"Review of {a['keyword']} for small businesses."

        cards_html += f"""
    <a href="/articles/{a['slug']}.html" class="article-card" data-category="{a['category']}">
      <div class="article-pill">{a['category']}</div>
      <h2>{a['title']}</h2>
      <p>{meta_desc[:140]}</p>
      <div class="article-footer">
        <div class="article-meta">
          <span>{read_time} min read</span>
          <span>{date}</span>
        </div>
        <div class="article-arrow">→</div>
      </div>
    </a>"""

    new_index = re.sub(
        r'<!-- Generated articles will be listed here automatically by generate\.py -->.*?(?=\s*</div>\s*</div>)',
        f'<!-- Generated articles will be listed here automatically by generate.py -->{cards_html}',
        index_html,
        flags=re.DOTALL
    )

    if not preview:
        INDEX_PATH.write_text(new_index, encoding='utf-8')
        print(f"  Rebuilt reviews index with {len(articles)} articles")
    else:
        print(f"  [preview] Would rebuild reviews index with {len(articles)} articles")


def main():
    parser = argparse.ArgumentParser(description="Fix articles without regenerating")
    parser.add_argument('--titles', action='store_true', help='Fix titles only')
    parser.add_argument('--categories', action='store_true', help='Fix categories only')
    parser.add_argument('--preview', action='store_true', help='Preview changes without saving')
    args = parser.parse_args()

    fix_title_flag = args.titles or (not args.titles and not args.categories)
    fix_cat_flag = args.categories or (not args.titles and not args.categories)

    if args.preview:
        print("PREVIEW MODE — no files will be changed\n")

    keywords = load_keywords()
    print(f"Loaded {len(keywords)} keywords\n")

    results = []
    changed = 0
    not_found = 0

    for keyword in keywords:
        title = fix_title(keyword)
        slug = slugify(title)
        article_path = ARTICLES_DIR / f"{slug}.html"

        if not article_path.exists():
            # Try matching by keyword fragments
            kw_slug = slugify(keyword)
            candidates = list(ARTICLES_DIR.glob("*.html"))
            match = None
            for c in candidates:
                if c.stem == kw_slug or kw_slug[:30] in c.stem:
                    match = c
                    break
            if match:
                article_path = match
            else:
                print(f"  NOT FOUND: {keyword} (expected {slug}.html)")
                not_found += 1
                continue

        result = fix_article(article_path, keyword, fix_title_flag, fix_cat_flag, args.preview)
        results.append(result)

        if result['changed']:
            changed += 1
            action = "[preview]" if args.preview else "Fixed"
            print(f"{action}: {article_path.name}")
            for c in result['changes']:
                print(c)

    print(f"\nDone. {changed} articles updated, {not_found} not found.")

    if results:
        rebuild_reviews_index(results, args.preview)

    if not args.preview:
        print("\nNext: git add . && git commit -m 'Fix article titles and categories' && git push")


if __name__ == "__main__":
    main()
