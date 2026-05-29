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
