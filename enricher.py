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
