# ToolAdvisor

AI tool review site for small businesses. Generates affiliate content automatically via Claude API.

## Structure

```
tooladvisor/
├── index.html              # Homepage (tooladvisor.tech/)
├── article-template.html   # Template used for every generated article
├── articles/
│   ├── reviews.html        # All reviews listing page (tooladvisor.tech/articles/reviews.html)
│   └── *.html              # Generated articles
├── scripts/
│   ├── generate.py         # Article generator — the main script
│   └── keywords.txt        # Keywords to write articles for
└── sitemap.xml             # Auto-generated, submit to Google Search Console
```

## Setup

### 1. Install dependencies

```bash
pip install anthropic
```

### 2. Set your API key

```bash
export ANTHROPIC_API_KEY=your_key_here
```

On Mac/Linux add this to your `~/.zshrc` or `~/.bashrc` so you don't have to set it every time.

### 3. Add your affiliate links

Open `scripts/generate.py` and update the `AFFILIATE_LINKS` dict with your real referral URLs. Sign up for programs at:

- Jasper: jasper.ai/affiliates
- Copy.ai: copy.ai (via ShareASale)
- Notion: notion.so/affiliates
- ClickUp: clickup.com/affiliates
- Zapier: zapier.com/partners
- Make: make.com/en/affiliate-program
- Writesonic: writesonic.com/affiliates
- FreshBooks: freshbooks.com/affiliate
- HubSpot: hubspot.com/partners

### 4. Generate articles

Single article:
```bash
python scripts/generate.py "best AI invoicing tools for freelancers"
```

Batch (all keywords in keywords.txt):
```bash
python scripts/generate.py --batch scripts/keywords.txt
```

### 5. Push to GitHub

```bash
git add .
git commit -m "Add articles"
git push
```

Vercel auto-deploys on every push.

## Deploy to Vercel

1. Go to vercel.com → "Add New Project" → import your GitHub repo
2. No build settings needed (pure HTML)
3. Add your custom domain (tooladvisor.tech) in Project Settings → Domains

## Submit to Google

After deploying:
1. Go to [Google Search Console](https://search.google.com/search-console)
2. Add property → Domain → `tooladvisor.tech`
3. Submit `https://tooladvisor.tech/sitemap.xml`

## Affiliate programs to sign up for

Priority order (highest commissions first):

| Tool | Commission | Program |
|------|-----------|---------|
| Jasper | 30% recurring | jasper.ai/affiliates |
| Writesonic | 30% recurring | writesonic.com/affiliates |
| ClickUp | $50/referral | clickup.com/affiliates |
| Copy.ai | 45% recurring | ShareASale |
| Notion | Variable | notion.so/affiliates |
| FreshBooks | $5–$55/signup | freshbooks.com/affiliate |
| Zapier | 25% first year | zapier.com/partners |

## Tips

- Generate 20-30 articles before worrying about traffic
- Comparison articles ("X vs Y") convert best
- "Best X for [specific person]" keywords have less competition than generic "best X"
- Rerun the generator on the same keyword every 6 months to refresh content
