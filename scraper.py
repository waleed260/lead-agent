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
