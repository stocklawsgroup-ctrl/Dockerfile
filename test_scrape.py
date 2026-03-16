"""
Airbnb Multicalendar scraper — multi-property
- Scrapes multiple Airbnb accounts (one per property)
- Each property has its own saved Chrome profile (login once, reused forever)
- Data is sent in real-time to the server via receive.php

Setup:
  pip install playwright
  playwright install chromium

Usage:
  python test_scrape.py                  # scrape all properties
  python test_scrape.py goettingen       # scrape one property by name
"""

import asyncio
import json
import re
import os
import sys
import urllib.request
from datetime import date
from playwright.async_api import async_playwright

# ── Properties config ────────────────────────────────────────────────────────
# Add a new dict here for each property.
# Chrome profiles are saved per-property so logins persist.
# Load properties from properties.json
_props_file = os.path.join(os.path.dirname(__file__), "properties.json")
with open(_props_file, encoding="utf-8") as _f:
    PROPERTIES = [
        {"name": p["name"], "profile": f"chrome_profile_{p['name']}"}
        for p in json.load(_f)
    ]
# ─────────────────────────────────────────────────────────────────────────────

AIRBNB_CALENDAR_URL = "https://www.airbnb.com/multicalendar"
MONTHS_TO_SCRAPE    = 3
WEEKS_PER_MONTH     = 4
OUTPUT_FILE         = "test_output.json"

# URL of the PHP receiver on your server
RECEIVER_URL = "https://gogokyoto.com/airbnb/receive.php?key=gogo2026"


# ── Database upload ───────────────────────────────────────────────────────────

def send_to_server(rows):
    if not rows:
        return 0
    payload = json.dumps(rows).encode('utf-8')
    req = urllib.request.Request(
        RECEIVER_URL,
        data=payload,
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode())
            return result.get('inserted', 0)
    except Exception as e:
        print(f"  Server error: {e}")
        return 0


# ── Per-property scraper ──────────────────────────────────────────────────────

class PropertyScraper:
    def __init__(self, prop):
        self.name    = prop["name"]
        self.profile = os.path.join(os.path.dirname(__file__), prop["profile"])
        self.data    = {"prices": {}, "availability": {}, "listings": {}}

    def parse_response_body(self, body_text):
        # Extract listing names
        for lid, lname in re.findall(r'"listingId":"(\d+)"[^}]{0,300}"listingName":"([^"]+)"', body_text):
            self.data["listings"][lid] = lname
        for lname, lid in re.findall(r'"listingName":"([^"]+)"[^}]{0,300}"listingId":"(\d+)"', body_text):
            self.data["listings"][lid] = lname

        entries = re.findall(
            r'"available":(true|false),"bookable":(true|false),"day":"(\d{4}-\d{2}-\d{2})","listingId":"(\d+)"[^}]{0,400}"nativeAdjustedPrice":(\d+)',
            body_text
        )

        rows  = []
        count = 0
        for available, bookable, day, listing_id, price in entries:
            room_name    = self.data["listings"].get(listing_id, f"listing_{listing_id}")
            is_available = available == "true"

            if room_name not in self.data["prices"]:
                self.data["prices"][room_name]       = {}
                self.data["availability"][room_name] = {}

            self.data["prices"][room_name][day]       = int(price)
            self.data["availability"][room_name][day] = {
                "available": is_available,
                "booked":    not is_available,
                "price":     int(price)
            }
            rows.append({
                "property":  self.name,
                "room":      room_name,
                "date":      day,
                "available": 1 if is_available else 0,
                "booked":    0 if is_available else 1,
                "price":     int(price)
            })
            count += 1

        if rows:
            send_to_server(rows)

        return count

    async def setup_interception(self, page):
        async def handle_response(response):
            url = response.url
            if "api.airbnb.com" in url or "/api/v3/" in url or "graphql" in url.lower():
                try:
                    body = await response.text()
                    if "PatekCalendarDay" in body or "nativeAdjustedPrice" in body:
                        count = self.parse_response_body(body)
                        if count > 0:
                            total = sum(len(v) for v in self.data["prices"].values())
                            print(f"  [{self.name}] Captured {count} entries → {total} total")
                except:
                    pass
        page.on("response", handle_response)

    async def wait_for_login(self, page):
        print(f"\n[{self.name}] Opening Airbnb...")
        print(f"  Please log in with the {self.name} Airbnb account.")
        print(f"  The script continues automatically once logged in.\n")

        # Show a clear label screen before Airbnb loads
        await page.set_content(f"""
            <html><body style="background:#e00b41;display:flex;align-items:center;justify-content:center;height:100vh;margin:0;font-family:sans-serif;">
            <div style="text-align:center;color:white;">
                <div style="font-size:18px;opacity:0.8;margin-bottom:12px;">Log in with this Airbnb account:</div>
                <div style="font-size:72px;font-weight:bold;letter-spacing:4px;">{self.name.upper()}</div>
                <div style="font-size:16px;opacity:0.7;margin-top:20px;">Navigating to Airbnb in 3 seconds...</div>
            </div>
            </body></html>
        """)
        await page.wait_for_timeout(3000)

        await page.goto(AIRBNB_CALENDAR_URL)
        await page.wait_for_load_state("domcontentloaded")

        print(f"  Waiting for login... (3 minutes)")
        await page.wait_for_function(
            "() => !window.location.href.includes('login') && !window.location.href.includes('signup')",
            timeout=180000
        )

        print(f"  Logged in! Navigating to calendar...")
        await page.goto(AIRBNB_CALENDAR_URL, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(4000)

        try:
            close_btn = await page.query_selector('[aria-label="Close"], [data-testid="modal-close-btn"], button[aria-label="閉じる"]')
            if close_btn:
                await close_btn.click()
                await page.wait_for_timeout(500)
        except:
            pass

        print(f"  Calendar loaded!\n")

    async def run(self, p):
        print(f"\n{'='*50}")
        print(f"  Property: {self.name}")
        print(f"{'='*50}")

        context = await p.chromium.launch_persistent_context(
            user_data_dir=self.profile,
            headless=False,
            channel="chrome",
            args=[
                "--start-maximized",
                "--disable-blink-features=AutomationControlled",
            ],
            viewport={"width": 1400, "height": 900},
            locale="ja-JP",
            timezone_id="Asia/Tokyo",
            ignore_default_args=["--enable-automation"],
        )
        page = await context.new_page()

        try:
            await self.setup_interception(page)
            await self.wait_for_login(page)

            total_weeks = MONTHS_TO_SCRAPE * WEEKS_PER_MONTH
            print(f"  Navigating {total_weeks} weeks ({MONTHS_TO_SCRAPE} months)...")

            # Initial load
            await page.wait_for_timeout(2500)
            html = await page.content()
            self.parse_response_body(html)

            # Navigate week by week
            for i in range(total_weeks):
                print(f"  Week {i+1}/{total_weeks}...")
                btn = await page.query_selector('[aria-label="次の週"]')
                if btn:
                    await btn.click()
                    await page.wait_for_timeout(1200)
                else:
                    print("  Warning: next week button not found")

            await page.wait_for_timeout(2000)

            price_count = sum(len(v) for v in self.data["prices"].values())
            print(f"\n  ✓ {self.name} done — {price_count} entries, {len(self.data['prices'])} rooms")

        except Exception as e:
            print(f"\n  ✗ Error on {self.name}: {e}")
            await page.screenshot(path=f"error_{self.name}.png")

        finally:
            await context.close()

        return self.data


# ── Main ──────────────────────────────────────────────────────────────────────

async def main():
    # Filter to specific property if given as argument
    target = sys.argv[1].lower() if len(sys.argv) > 1 else None
    props  = [p for p in PROPERTIES if target is None or p["name"].lower() == target]

    if not props:
        print(f"ERROR: Property '{target}' not found. Available: {[p['name'] for p in PROPERTIES]}")
        return

    all_data = {"scraped_at": date.today().isoformat(), "prices": {}, "availability": {}}

    async with async_playwright() as p:
        # Run all properties in parallel
        results = await asyncio.gather(*[PropertyScraper(prop).run(p) for prop in props])

        for data in results:
            all_data["prices"].update(data["prices"])
            all_data["availability"].update(data["availability"])

    # Save combined JSON backup
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)

    total = sum(len(v) for v in all_data["prices"].values())
    print(f"\n✓ All done! {total} total entries across {len(all_data['prices'])} rooms")
    print(f"  Backup saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    asyncio.run(main())
