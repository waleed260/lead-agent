# PRD — AI Lead Generation Agent
> **Project Name:** `lead-agent`
> **Stack:** Python 3.12 · uv · Playwright · BeautifulSoup · Claude API · SerpAPI · Google Sheets API
> **Status:** Draft v1.0

---

## 1. Overview

`lead-agent` is a fully automated, four-stage AI agent pipeline that accepts a Google Maps search query (e.g. *"Restaurants in Lahore"*), scrapes business listings, enriches each record using Claude AI, fills in missing social profiles via Google Search, and writes everything into a structured Google Sheet — with zero manual work after the initial run.

---

## 2. Goals

| # | Goal |
|---|------|
| G1 | Scrape business data from Google Maps without a paid API |
| G2 | Use Claude to extract email, founder name, and social links from each business website |
| G3 | Fall back to SerpAPI Google Search for socials not found on the website |
| G4 | Auto-fill a Google Sheet with one clean row per business |
| G5 | Run the entire pipeline with a single command |

---

## 3. Non-Goals

- No CRM integration (out of scope for v1)
- No email sending or outreach automation
- No proxy rotation or CAPTCHA solving
- No real-time / scheduled runs (manual trigger only in v1)

---

## 4. Architecture

```
YOU (search query: "Restaurants in Lahore")
        │
        ▼
┌─────────────────────────────┐
│  STAGE 1 — Google Maps      │  Playwright (headless Chromium)
│  Scraper  (scraper.py)      │  → name, phone, website, address, category
└────────────────┬────────────┘
                 │
                 ▼
┌─────────────────────────────┐
│  STAGE 2 — AI Enrichment    │  Claude Haiku API
│  Agent    (enricher.py)     │  → visits website → extracts email,
│                             │    founder, instagram, facebook, linkedin
└────────────────┬────────────┘
                 │
                 ▼
┌─────────────────────────────┐
│  STAGE 3 — Social Search    │  SerpAPI (100 free/day)
│            (enricher.py)    │  → fills missing socials via
│                             │    site:instagram.com query
└────────────────┬────────────┘
                 │
                 ▼
┌─────────────────────────────┐
│  STAGE 4 — Google Sheets    │  gspread + Google Sheets API
│  Writer   (sheets.py)       │  → one row per business, styled header
└─────────────────────────────┘
```

---

## 5. Output Schema

| Column | Source | Notes |
|--------|--------|-------|
| Business Name | Stage 1 | From Google Maps listing |
| Category | Stage 1 | e.g. Restaurant, Café |
| Phone | Stage 1 | Cleaned from Maps panel |
| Email | Stage 2 | Claude extracts from website |
| Website | Stage 1 | Direct link from Maps |
| Address | Stage 1 | From Maps address button |
| Instagram | Stage 2 / 3 | Full URL |
| Facebook | Stage 2 / 3 | Full URL |
| LinkedIn | Stage 2 / 3 | Full URL |
| Twitter / X | Stage 2 | Full URL |
| Founder | Stage 2 | Claude extracts from About/Contact pages |

---

## 6. Tech Stack & Cost

| Purpose | Tool | Cost |
|---------|------|------|
| Google Maps scraping | Playwright (Python) | Free |
| Website content extraction | BeautifulSoup4 | Free |
| AI enrichment | Claude Haiku API | Free credits on signup |
| Social profile search | SerpAPI | 100 searches/day free |
| Google Sheets output | gspread + Google Sheets API | Free |
| Environment management | uv | Free |

---

## 7. Project Setup (Step-by-Step)

### 7.1 Prerequisites

- Python 3.12+
- [`uv`](https://docs.astral.sh/uv/) installed globally:
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```
- A Google Cloud project with **Sheets API** enabled and a `credentials.json` service account file
- API keys for Claude and SerpAPI

---

### 7.2 Create the Project

```bash
uv init lead-agent
cd lead-agent
```

This creates:
```
lead-agent/
├── pyproject.toml
├── README.md
└── hello.py          ← delete this
```

---

### 7.3 Create the Virtual Environment

```bash
uv venv
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate         # Windows
```

---

### 7.4 Install Dependencies

```bash
uv add playwright beautifulsoup4 requests anthropic gspread google-auth python-dotenv
playwright install chromium
```

Your `pyproject.toml` will auto-update with pinned versions.

---

### 7.5 Final Project Structure

```
lead-agent/
├── .venv/
├── .env                  ← API keys (never commit)
├── .gitignore
├── pyproject.toml
├── credentials.json      ← Google service account (never commit)
├── PRD.md
├── run.py                ← Master runner (entry point)
├── scraper.py            ← Stage 1: Google Maps
├── enricher.py           ← Stage 2 + 3: Claude + SerpAPI
├── sheets.py             ← Stage 4: Google Sheets
├── businesses.json       ← Intermediate: raw scrape output
└── enriched.json         ← Intermediate: enriched output
```

---

### 7.6 `.env` File

Create `.env` in the project root:

```env
ANTHROPIC_API_KEY=your-claude-api-key
SERPAPI_KEY=your-serpapi-key
GOOGLE_SHEET_ID=your-google-sheet-id
```

---

### 7.7 `.gitignore`

```gitignore
.env
credentials.json
.venv/
__pycache__/
*.pyc
businesses.json
enriched.json
```

---

## 8. Source Files

### 8.1 `scraper.py` — Stage 1: Google Maps Scraper

```python
import asyncio
from playwright.async_api import async_playwright
import json

async def scrape_google_maps(query: str, max_results: int = 50):
    businesses = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        search_url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}"
        await page.goto(search_url)
        await page.wait_for_timeout(3000)

        # Scroll to load more results
        results_panel = page.locator('div[role="feed"]')
        for _ in range(10):
            await results_panel.evaluate("el => el.scrollBy(0, 1000)")
            await page.wait_for_timeout(1000)

        listings = await page.locator('a[href*="/maps/place/"]').all()

        for listing in listings[:max_results]:
            try:
                await listing.click()
                await page.wait_for_timeout(2000)

                name = await page.locator('h1').first.inner_text()

                phone = ""
                phone_el = page.locator('button[data-tooltip="Copy phone number"]')
                if await phone_el.count() > 0:
                    phone = await phone_el.get_attribute("data-item-id") or ""
                    phone = phone.replace("phone:", "")

                website = ""
                web_el = page.locator('a[data-tooltip="Open website"]')
                if await web_el.count() > 0:
                    website = await web_el.get_attribute("href") or ""

                category = ""
                cat_el = page.locator('button[jsaction*="category"]')
                if await cat_el.count() > 0:
                    category = await cat_el.first.inner_text()

                address = ""
                addr_el = page.locator('button[data-tooltip="Copy address"]')
                if await addr_el.count() > 0:
                    address = await addr_el.get_attribute("aria-label") or ""

                businesses.append({
                    "name": name.strip(),
                    "phone": phone.strip(),
                    "website": website.strip(),
                    "address": address.strip(),
                    "category": category.strip(),
                    "email": "",
                    "instagram": "",
                    "facebook": "",
                    "linkedin": "",
                    "twitter": "",
                    "founder": ""
                })
                print(f"✓ Scraped: {name}")

            except Exception as e:
                print(f"✗ Error on listing: {e}")
                continue

        await browser.close()

    return businesses


if __name__ == "__main__":
    results = asyncio.run(scrape_google_maps("restaurants in Lahore", 30))
    with open("businesses.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nDone. Scraped {len(results)} businesses.")
```

---

### 8.2 `enricher.py` — Stage 2 + 3: AI Enrichment + Social Search

```python
import anthropic
import requests
from bs4 import BeautifulSoup
import json
import time
import os
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


def fetch_website_text(url: str) -> str:
    if not url:
        return ""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, timeout=8, headers=headers)
        soup = BeautifulSoup(res.text, "html.parser")
        text = soup.get_text(separator=" ", strip=True)[:3000]
        links = [a.get("href", "") for a in soup.find_all("a", href=True)]
        return text + "\n\nLINKS FOUND: " + " ".join(links)
    except:
        return ""


def enrich_with_claude(business: dict, website_content: str) -> dict:
    prompt = f"""You are a data extraction agent. Extract the following from this business website content.

Business name: {business['name']}

Website content:
{website_content}

Extract and return ONLY a valid JSON object with these exact keys:
{{
  "email": "email address or empty string",
  "founder": "founder/owner name or empty string",
  "instagram": "full instagram URL or empty string",
  "facebook": "full facebook URL or empty string",
  "linkedin": "full linkedin URL or empty string",
  "twitter": "full twitter/X URL or empty string"
}}

Rules:
- Only return real data found in the content, never guess
- Return full URLs not just handles
- If not found, return empty string
- Return ONLY the JSON, no explanation"""

    try:
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = message.content[0].text.strip()
        if "```" in raw:
            raw = raw.split("```")[1].replace("json", "").strip()
        extracted = json.loads(raw)
        business.update(extracted)
    except Exception as e:
        print(f"  Claude error for {business['name']}: {e}")

    return business


def search_socials_google(business_name: str, serpapi_key: str) -> dict:
    socials = {}
    platforms = {
        "instagram": f"site:instagram.com {business_name}",
        "facebook": f"site:facebook.com {business_name}",
        "linkedin": f"site:linkedin.com/company {business_name}"
    }
    for platform, query in platforms.items():
        try:
            res = requests.get("https://serpapi.com/search", params={
                "q": query,
                "api_key": serpapi_key,
                "num": 1
            })
            results = res.json().get("organic_results", [])
            if results:
                socials[platform] = results[0].get("link", "")
        except:
            pass
        time.sleep(0.5)
    return socials


def enrich_all_businesses(input_file="businesses.json", output_file="enriched.json"):
    serpapi_key = os.getenv("SERPAPI_KEY")

    with open(input_file) as f:
        businesses = json.load(f)

    enriched = []

    for i, biz in enumerate(businesses):
        print(f"\n[{i+1}/{len(businesses)}] Enriching: {biz['name']}")

        content = fetch_website_text(biz.get("website", ""))

        if content:
            biz = enrich_with_claude(biz, content)
            print(f"  ✓ Claude extracted data")

        missing = not biz.get("instagram") or not biz.get("facebook")
        if missing and serpapi_key:
            found = search_socials_google(biz["name"], serpapi_key)
            for key, val in found.items():
                if val and not biz.get(key):
                    biz[key] = val
            print(f"  ✓ Google search filled gaps")

        enriched.append(biz)
        time.sleep(1.5)

    with open(output_file, "w") as f:
        json.dump(enriched, f, indent=2)

    print(f"\n✅ Done. {len(enriched)} businesses enriched.")
    return enriched


if __name__ == "__main__":
    enrich_all_businesses()
```

---

### 8.3 `sheets.py` — Stage 4: Google Sheets Writer

```python
import gspread
from google.oauth2.service_account import Credentials
import json
import os
from dotenv import load_dotenv

load_dotenv()


def push_to_sheets(data_file="enriched.json"):
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
    client = gspread.authorize(creds)

    sheet = client.open_by_key(os.getenv("GOOGLE_SHEET_ID")).sheet1

    headers = [
        "Business Name", "Category", "Phone", "Email", "Website",
        "Address", "Instagram", "Facebook", "LinkedIn", "Twitter", "Founder"
    ]
    sheet.clear()
    sheet.append_row(headers)

    sheet.format("A1:K1", {
        "textFormat": {"bold": True},
        "backgroundColor": {"red": 0.2, "green": 0.2, "blue": 0.8}
    })

    with open(data_file) as f:
        businesses = json.load(f)

    rows = []
    for biz in businesses:
        rows.append([
            biz.get("name", ""),
            biz.get("category", ""),
            biz.get("phone", ""),
            biz.get("email", ""),
            biz.get("website", ""),
            biz.get("address", ""),
            biz.get("instagram", ""),
            biz.get("facebook", ""),
            biz.get("linkedin", ""),
            biz.get("twitter", ""),
            biz.get("founder", "")
        ])

    sheet.append_rows(rows)
    print(f"✅ Pushed {len(rows)} rows to Google Sheets!")


if __name__ == "__main__":
    push_to_sheets()
```

---

### 8.4 `run.py` — Master Entry Point

```python
import asyncio
import json
from scraper import scrape_google_maps
from enricher import enrich_all_businesses
from sheets import push_to_sheets


async def main():
    query = input("Enter search query (e.g. 'restaurants in Lahore'): ")
    max_results = int(input("How many businesses? (e.g. 50): "))

    print("\n🔍 Stage 1: Scraping Google Maps...")
    businesses = await scrape_google_maps(query, max_results)
    with open("businesses.json", "w") as f:
        json.dump(businesses, f, indent=2)

    print("\n🤖 Stage 2 + 3: AI Enrichment + Social Search...")
    enrich_all_businesses()

    print("\n📊 Stage 4: Pushing to Google Sheets...")
    push_to_sheets()

    print("\n✅ ALL DONE! Check your Google Sheet.")


if __name__ == "__main__":
    asyncio.run(main())
```

---

## 9. Running the Agent

```bash
# Activate the virtual environment (if not already active)
source .venv/bin/activate

# Run the full pipeline
python run.py
```

You'll be prompted:
```
Enter search query (e.g. 'restaurants in Lahore'): restaurants in Lahore
How many businesses? (e.g. 50): 30
```

Then the agent runs all four stages automatically.

---

## 10. Free API Keys

| Service | URL | Free Tier |
|---------|-----|-----------|
| Claude API | https://console.anthropic.com | Free credits on signup |
| SerpAPI | https://serpapi.com | 100 searches/day |
| Google Sheets API | Google Cloud Console | Free (needs `credentials.json`) |

---

## 11. Limitations & Known Issues

| Issue | Mitigation |
|-------|------------|
| Google Maps may block repeated scraping | Add `time.sleep()` between requests; use headless with random delays |
| SerpAPI 100/day limit | Batch runs; upgrade plan for larger datasets |
| Some websites block bots | `requests` with User-Agent header; Playwright fallback for v2 |
| Claude may hallucinate if page content is noisy | Strict prompt with "never guess" instruction |
| Google Maps UI changes break selectors | Pin Playwright version; monitor selector failures |

---

## 12. v2 Roadmap

- [ ] Playwright-based website scraping for JS-heavy sites
- [ ] Retry logic and exponential backoff on failures
- [ ] Proxy rotation for large-scale scraping
- [ ] Scheduled runs via cron / GitHub Actions
- [ ] Email outreach module (Stage 5)
- [ ] Deduplication across multiple runs
- [ ] CSV export as an alternative to Google Sheets

---

*Last updated: 2026-05-29*
