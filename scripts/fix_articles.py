#!/usr/bin/env python3
"""
ToolAdvisor — Article Fixer
----------------------------
Fixes titles, capitalisation, and categories in existing articles.
No full regeneration needed.

Modes:
  python scripts/fix_articles.py                # Fix capitalisation + categories (free, instant)
  python scripts/fix_articles.py --rewrite      # Also rewrite titles using Claude API (cheap, ~$0.002/article)
  python scripts/fix_articles.py --categories   # Fix categories only
  python scripts/fix_articles.py --preview      # Preview without saving

The --rewrite flag uses Claude to produce natural, well-written titles.
Without it, capitalisation fixes are applied locally at zero cost.
"""

import re
import os
import argparse
import anthropic
from pathlib import Path
from datetime import datetime

ARTICLES_DIR = Path(__file__).parent.parent / "articles"
INDEX_PATH   = ARTICLES_DIR / "reviews.html"
KEYWORDS_PATH = Path(__file__).parent / "keywords.txt"
API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# ── Capitalisation fixes ──────────────────────────────────────────────────────
# These are applied locally, zero cost.
# Format: (pattern, replacement) — case-insensitive search, exact replacement

CAP_FIXES = [
    # Acronyms that Python's .title() mangles
    (r'\bAi\b', 'AI'),
    (r'\bCrm\b', 'CRM'),
    (r'\bSeo\b', 'SEO'),
    (r'\bSms\b', 'SMS'),
    (r'\bApi\b', 'API'),
    (r'\bSaas\b', 'SaaS'),
    (r'\bUi\b', 'UI'),
    (r'\bUx\b', 'UX'),
    (r'\bKpi\b', 'KPI'),
    (r'\bRoi\b', 'ROI'),
    (r'\bB2b\b', 'B2B'),
    (r'\bB2c\b', 'B2C'),
    (r'\bCta\b', 'CTA'),
    (r'\bErp\b', 'ERP'),
    (r'\bHr\b', 'HR'),
    (r'\bIt\b', 'IT'),
    # Brand names
    (r'\bActivecampaign\b', 'ActiveCampaign'),
    (r'\bClickup\b', 'ClickUp'),
    (r'\bApollo\.Io\b', 'Apollo.io'),
    (r'\bAdcreative\.Ai\b', 'AdCreative.ai'),
    (r'\bReclaim\.Ai\b', 'Reclaim.ai'),
    (r'\bHubspot\b', 'HubSpot'),
    (r'\bManychat\b', 'ManyChat'),
    (r'\bPandadoc\b', 'PandaDoc'),
    (r'\bElevenlabs\b', 'ElevenLabs'),
    (r'\bMurf Ai\b', 'Murf AI'),
    (r'\bAweber\b', 'AWeber'),
    (r'\bReply\.Io\b', 'Reply.io'),
    (r'\bLeadpages\b', 'Leadpages'),
    (r'\bFreshbooks\b', 'FreshBooks'),
    (r'\bQuickbooks\b', 'QuickBooks'),
    (r'\bClickfunnels\b', 'ClickFunnels'),
    (r'\bDocusign\b', 'DocuSign'),
    (r'\bWritesonic\b', 'Writesonic'),
    (r'\bCopy\.Ai\b', 'Copy.ai'),
    (r'\bChatgpt\b', 'ChatGPT'),
    (r'\bOpenai\b', 'OpenAI'),
    (r'\bMidjourney\b', 'Midjourney'),
    (r'\bCastmagic\b', 'Castmagic'),
    (r'\bBrand24\b', 'Brand24'),
    # Common words that shouldn't be title-cased mid-sentence
    (r'\bVs\b', 'vs'),
    (r' And ', ' and '),
    (r' For ', ' for '),
    (r' The ', ' the '),
    (r' Of ', ' of '),
    (r' In ', ' in '),
    (r' To ', ' to '),
    (r' A ', ' a '),
    (r' An ', ' an '),
    (r' Or ', ' or '),
    (r' With ', ' with '),
    (r' On ', ' on '),
    (r' At ', ' at '),
    (r' By ', ' by '),
    (r' From ', ' from '),
    (r' Into ', ' into '),
]

def apply_cap_fixes(title: str) -> str:
    """Apply all capitalisation fixes to a title string."""
    result = title
    for pattern, replacement in CAP_FIXES:
        result = re.sub(pattern, replacement, result)
    # Always capitalise first character
    if result:
        result = result[0].upper() + result[1:]
    return result

# ── Category detection ────────────────────────────────────────────────────────

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

# ── Claude title rewriter ─────────────────────────────────────────────────────

def rewrite_titles_with_claude(keyword_title_pairs: list[tuple]) -> dict:
    """
    Send all titles to Claude in one batch call.
    Returns a dict mapping keyword -> new title.
    Cost: ~$0.002 total for 50 titles.
    """
    if not API_KEY:
        print("Error: ANTHROPIC_API_KEY not set. Run: export ANTHROPIC_API_KEY=your_key")
        return {}

    client = anthropic.Anthropic(api_key=API_KEY)

    # Build the prompt with all titles at once — one API call for all
    pairs_text = "\n".join(
        f'{i+1}. Keyword: "{kw}" | Current title: "{title}"'
        for i, (kw, title) in enumerate(keyword_title_pairs)
    )

    prompt = f"""You are writing titles for ToolAdvisor, an AI tool review site for small businesses.

Rewrite each article title to be clear, natural, and compelling. Rules:
- Keep it concise (under 70 characters including year)
- For comparison articles (X vs Y): "X vs Y: Which Is Better for Small Businesses? (2026)"
- For review articles: "[Tool] Review: Is It Worth It for Small Businesses? (2026)"  
- For best-of lists: "The Best [Category] Tools for Small Businesses (2026)"
- Always fix capitalisation: AI not Ai, CRM not Crm, SaaS not Saas
- Keep brand names exactly correct: ActiveCampaign, ClickUp, HubSpot, etc.
- No clickbait, no ALL CAPS, no exclamation marks
- Sound like a real editor wrote it, not a bot

Return ONLY a numbered list matching the input numbers, one title per line, nothing else.
Format exactly: 1. Title Here

{pairs_text}"""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )

    response = message.content[0].text
    results = {}

    for i, (kw, _) in enumerate(keyword_title_pairs):
        pattern = rf'^{i+1}\.\s+(.+)$'
        match = re.search(pattern, response, re.MULTILINE)
        if match:
            results[kw] = match.group(1).strip()
        else:
            results[kw] = None  # Fall back to cap fixes only

    return results

# ── Helpers ───────────────────────────────────────────────────────────────────

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

def find_article_path(keyword: str):
    """Find the article file for a given keyword."""
    # Try a few slug variants
    candidates = [
        slugify(keyword),
        slugify(f"best {keyword}"),
    ]
    for slug in candidates:
        p = ARTICLES_DIR / f"{slug}.html"
        if p.exists():
            return p

    # Fuzzy match — find file whose name contains key words from the keyword
    words = [w for w in keyword.lower().split() if len(w) > 3 and w not in
             ['best', 'tools', 'small', 'business', 'with', 'that', 'from', 'your', 'for']]
    for f in ARTICLES_DIR.glob("*.html"):
        if f.name == "reviews.html":
            continue
        if all(w in f.stem for w in words[:3]):
            return f

    return None

def get_current_title(path: Path) -> str:
    content = path.read_text(encoding='utf-8')
    match = re.search(r'<h1>(.*?)</h1>', content)
    return match.group(1).strip() if match else ""

def fix_markdown_in_body(content: str) -> str:
    """Convert any leftover markdown syntax to proper HTML."""

    # **bold text** → <strong>bold text</strong>
    content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', content)

    # *italic text* → <em>italic text</em> (single asterisk, not already inside a tag)
    content = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<em>\1</em>', content)

    # `code` → <code>code</code>
    content = re.sub(r'`([^`]+)`', r'<code>\1</code>', content)

    # ### Heading → <h3>
    content = re.sub(r'^### (.+)$', r'<h3>\1</h3>', content, flags=re.MULTILINE)

    # ## Heading → <h2>
    content = re.sub(r'^## (.+)$', r'<h2>\1</h2>', content, flags=re.MULTILINE)

    # # Heading → <h2> (treat h1 as h2 in body)
    content = re.sub(r'^# (.+)$', r'<h2>\1</h2>', content, flags=re.MULTILINE)

    # Bare lines starting with - or * that aren't inside a list → wrap in <ul><li>
    # Find blocks of consecutive bullet lines and wrap them
    def wrap_bullets(m):
        lines = m.group(0).strip().split('\n')
        items = ''.join(f'<li>{re.sub(r"^[-*]\s+", "", l.strip())}</li>' for l in lines if l.strip())
        return f'<ul>{items}</ul>'

    content = re.sub(r'((?:^[-*] .+\n?)+)', wrap_bullets, content, flags=re.MULTILINE)

    # Numbered lists: "1. item" → <ol><li>
    def wrap_numbered(m):
        lines = m.group(0).strip().split('\n')
        items = ''.join(f'<li>{re.sub(r"^\d+\.\s+", "", l.strip())}</li>' for l in lines if l.strip())
        return f'<ol>{items}</ol>'

    content = re.sub(r'((?:^\d+\. .+\n?)+)', wrap_numbered, content, flags=re.MULTILINE)

    # Standalone lines that look like plain text paragraphs but aren't wrapped in tags
    # (only outside of existing HTML tags)
    lines = content.split('\n')
    fixed_lines = []
    for line in lines:
        stripped = line.strip()
        # If it's a non-empty line with no HTML tags and not inside a tag context
        if (stripped
            and not stripped.startswith('<')
            and not stripped.endswith('>')
            and not re.match(r'^<', stripped)
            and len(stripped) > 40):  # Only wrap substantial text blocks
            fixed_lines.append(f'<p>{stripped}</p>')
        else:
            fixed_lines.append(line)
    content = '\n'.join(fixed_lines)

    # Clean up any double-wrapped paragraphs
    content = re.sub(r'<p><p>', '<p>', content)
    content = re.sub(r'</p></p>', '</p>', content)

    return content


def apply_fixes_to_file(path: Path, new_title: str, new_category: str, preview: bool) -> bool:
    content = path.read_text(encoding='utf-8')
    original = content

    # Fix <title> tag
    content = re.sub(
        r'<title>.*?— ToolAdvisor</title>',
        f'<title>{new_title} — ToolAdvisor</title>',
        content
    )
    # Fix <h1>
    content = re.sub(r'<h1>.*?</h1>', f'<h1>{new_title}</h1>', content, count=1)
    # Fix category pill
    content = re.sub(
        r'<div class="article-pill">[^<]*</div>',
        f'<div class="article-pill">{new_category}</div>',
        content, count=1
    )
    # Fix meta og:title
    content = re.sub(
        r'<meta property="og:title" content="[^"]*">',
        f'<meta property="og:title" content="{new_title}">',
        content
    )

    # Fix markdown in article body only (between article-body tags)
    def fix_body(m):
        return m.group(0)[:m.start('body') - m.start(0)] + \
               fix_markdown_in_body(m.group('body')) + \
               m.group(0)[m.end('body') - m.start(0):]

    body_match = re.search(r'<div class="article-body">(?P<body>.*?)</div>\s*<div class="disclosure"', content, re.DOTALL)
    if body_match:
        fixed_body = fix_markdown_in_body(body_match.group('body'))
        content = content[:body_match.start('body')] + fixed_body + content[body_match.end('body'):]

    if not preview and content != original:
        path.write_text(content, encoding='utf-8')

    return content != original

def rebuild_reviews_index(articles: list[dict], preview: bool):
    if not INDEX_PATH.exists():
        print("  Warning: articles/reviews.html not found")
        return

    index_html = INDEX_PATH.read_text(encoding='utf-8')
    cards_html = ""

    for a in articles:
        read_time = "7"
        date = datetime.now().strftime("%b %Y")
        meta_desc = f"In-depth review of {a['keyword']} for small businesses."

        article_path = ARTICLES_DIR / f"{a['slug']}.html"
        if article_path.exists():
            art = article_path.read_text(encoding='utf-8')
            rt = re.search(r'<span>(\d+) min read</span>', art)
            dt = re.search(r'<span>(\w+ \d{{4}})</span>', art)
            meta = re.search(r'<meta name="description" content="([^"]+)"', art)
            if rt: read_time = rt.group(1)
            if dt: date = dt.group(1)
            if meta: meta_desc = meta.group(1)[:140]

        cards_html += f"""
    <a href="/articles/{a['slug']}.html" class="article-card" data-category="{a['category']}">
      <div class="article-pill">{a['category']}</div>
      <h2>{a['title']}</h2>
      <p>{meta_desc}</p>
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
        print(f"  Rebuilt reviews index ({len(articles)} articles)")
    else:
        print(f"  [preview] Would rebuild reviews index ({len(articles)} articles)")

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Fix article titles and categories without regenerating")
    parser.add_argument('--rewrite', action='store_true',
                        help='Use Claude API to rewrite titles naturally (~$0.002 total)')
    parser.add_argument('--categories', action='store_true',
                        help='Fix categories only, skip titles')
    parser.add_argument('--preview', action='store_true',
                        help='Show what would change without saving')
    args = parser.parse_args()

    if args.preview:
        print("PREVIEW MODE — no files will be changed\n")

    keywords = load_keywords()
    print(f"Loaded {len(keywords)} keywords")

    # Find all articles and their current titles
    found = []
    not_found = []
    for kw in keywords:
        path = find_article_path(kw)
        if path:
            current_title = get_current_title(path)
            found.append({'keyword': kw, 'path': path, 'current_title': current_title})
        else:
            not_found.append(kw)

    print(f"Found {len(found)} articles, {len(not_found)} not found\n")
    if not_found:
        print("Not found:")
        for kw in not_found:
            print(f"  - {kw}")
        print()

    # Step 1: Get new titles
    new_titles = {}

    if args.rewrite and not args.categories:
        print("Rewriting titles with Claude API (one batch call)...")
        pairs = [(a['keyword'], a['current_title']) for a in found]
        new_titles = rewrite_titles_with_claude(pairs)
        # Apply cap fixes to any Claude returned titles too
        for kw in new_titles:
            if new_titles[kw]:
                new_titles[kw] = apply_cap_fixes(new_titles[kw])
        print(f"Got {sum(1 for v in new_titles.values() if v)} rewritten titles\n")
    elif not args.categories:
        # Just apply cap fixes locally — free
        for a in found:
            new_titles[a['keyword']] = apply_cap_fixes(a['current_title'])

    # Step 2: Apply fixes to each article
    results = []
    changed = 0

    for a in found:
        kw = a['keyword']
        path = a['path']

        if args.categories:
            new_title = a['current_title']  # Don't touch titles
        else:
            new_title = new_titles.get(kw) or apply_cap_fixes(a['current_title'])

        new_category = get_category(kw)

        if args.preview:
            print(f"  {path.name}")
            if not args.categories:
                print(f"    Title:    {a['current_title']}")
                print(f"    → Becomes: {new_title}")
            print(f"    Category: {new_category}")
        else:
            was_changed = apply_fixes_to_file(path, new_title, new_category, preview=False)
            if was_changed:
                changed += 1
                print(f"  Fixed: {path.name}")
                if not args.categories:
                    print(f"    → {new_title}")
                print(f"    → [{new_category}]")

        results.append({
            'keyword': kw,
            'slug': path.stem,
            'title': new_title,
            'category': new_category,
        })

    if not args.preview:
        print(f"\n{changed} articles updated")
        rebuild_reviews_index(results, preview=False)
        print("\nNext: git add . && git commit -m 'Fix titles and categories' && git push")
    else:
        rebuild_reviews_index(results, preview=True)

if __name__ == "__main__":
    main()
