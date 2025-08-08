import os
import asyncio
import httpx
from playwright.async_api import async_playwright

# Configuration from environment variables
SEARCH_TEXT = os.getenv('SEARCH_TEXT', 'funko pop')
INCLUDE = [s.strip().lower() for s in os.getenv('INCLUDE', '').split(',') if s.strip()]
EXCLUDE = [s.strip().lower() for s in os.getenv('EXCLUDE', '').split(',') if s.strip()]
MAX_PRICE = float(os.getenv('MAX_PRICE_EUR', '60'))
POLL_INTERVAL = int(os.getenv('POLL_INTERVAL', '300'))
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
VINTED_DOMAIN = os.getenv('VINTED_DOMAIN', 'vinted.nl')

async def notify(message: str):
    """Send a message via Telegram if token and chat ID are set."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message,
        'disable_web_page_preview': True,
    }
    async with httpx.AsyncClient() as client:
        try:
            await client.post(url, data=data)
        except Exception:
            pass

async def scrape_vinted():
    """Continuously scan Vinted for Funko Pop deals and send alerts."""
    seen = set()
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        while True:
            # Build the search URL with price cap
            search_url = (
                f"https://{VINTED_DOMAIN}/catalog?search_text="
                f"{SEARCH_TEXT.replace(' ', '%20')}&price_to={MAX_PRICE}"
            )
            await page.goto(search_url)
            # Select all item elements on the page
            items = await page.locator('div.feed-grid__item').all()
            for item in items:
                try:
                    title = await item.locator('div.tile__title').inner_text()
                    price_text = await item.locator('meta[itemprop="price"]').get_attribute('content')
                    price = float(price_text)
                    href = await item.locator('a.item-box').get_attribute('href')
                    url = f"https://{VINTED_DOMAIN}{href}"
                except Exception:
                    continue
                lower_title = title.lower()
                # Apply include and exclude filters
                if INCLUDE and not any(kw in lower_title for kw in INCLUDE):
                    continue
                if any(kw in lower_title for kw in EXCLUDE):
                    continue
                if price > MAX_PRICE:
                    continue
                if url in seen:
                    continue
                message = f"\U0001F525 Funko gezien: {title} | €{price:.2f}\n{url}"
                await notify(message)
                seen.add(url)
            await asyncio.sleep(POLL_INTERVAL)

if __name__ == '__main__':
    asyncio.run(scrape_vinted())
