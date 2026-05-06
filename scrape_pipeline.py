import os
import re
import time
from pathlib import Path
from dotenv import load_dotenv
import requests

load_dotenv()

api_key = os.getenv("API_KEY")

# --- Step 01: Search + scrape with Firecrawl ---

api_url = "https://api.firecrawl.dev/v2/search"

headers = {
    "Authorization": f"Bearer {api_key}"
}

payload = {
    "query": "Chipotle investor relations press releases",
    "limit": 5,
    "scrapeOptions": {"formats": ["markdown"]}
}

response = requests.post(api_url, headers=headers, json=payload)

data = response.json()
results = data["data"]["web"]
print(f"Firecrawl returned {len(results)} results")

for r in results:
    print(f"  - {r['title']}")
    print(f"    {r['url']}")
    print(f"    markdown length: {len(r.get('markdown') or '')} chars")

# --- Step 02: Save each result as a markdown file in knowledge/raw/ ---

raw_dir = Path("knowledge/raw")
raw_dir.mkdir(parents=True, exist_ok=True)


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-") or "untitled"


scraped_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
used_names: set[str] = set()

for r in results:
    title = r.get("title") or "untitled"
    url = r.get("url", "")
    description = (r.get("description") or "").replace('"', '\\"')
    body = r.get("markdown") or ""

    frontmatter = (
        "---\n"
        f'url: "{url}"\n'
        f'title: "{title.replace(chr(34), chr(92) + chr(34))}"\n'
        f'description: "{description}"\n'
        f'scraped_at: "{scraped_at}"\n'
        "---\n\n"
    )

    base = slugify(title)
    name = f"{base}.md"
    if name in used_names:
        name = f"{base}-{r.get('position', 'x')}.md"
    used_names.add(name)

    path = raw_dir / name
    path.write_text(frontmatter + body, encoding="utf-8")
    print(f"  wrote {path}")