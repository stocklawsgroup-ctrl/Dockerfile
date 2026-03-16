async def run(self, p):
          print(f"\n{'='*50}")
          print(f"  Property: {self.name}")
          print(f"{'='*50}")

          session_file = os.path.join(os.path.dirname(__file__), f"session_{self.name}.json")
          if not os.path.exists(session_file):
              print(f"  ✗ No session file found: session_{self.name}.json — skipping")
              return self.data

          browser = await p.chromium.launch(
              headless=True,
              args=[
                  "--no-sandbox", 
                  "--disable-dev-shm-usage",
                  "--disable-blink-features=AutomationControlled",
                  "--disable-gpu",
              ],
          )
          context = await browser.new_context(
              storage_state=session_file,
              viewport={"width": 1400, "height": 900},
              locale="ja-JP",
              timezone_id="Asia/Tokyo",
          )
          page = await context.new_page()

          try:
              await self.setup_interception(page)

              print(f"  Navigating to calendar...")
              await page.goto(AIRBNB_CALENDAR_URL, wait_until="domcontentloaded", timeout=60000)
              await page.wait_for_timeout(4000)

              if "login" in page.url or "signup" in page.url:
                  print(f"  ✗ {self.name}: Session expired — re-run export_sessions.py on Windows")
                  return self.data

              print(f"  Logged in! Scraping {MONTHS_TO_SCRAPE * WEEKS_PER_MONTH} weeks...")

              await page.wait_for_timeout(2500)
              html = await page.content()
              self.parse_response_body(html)

              for i in range(MONTHS_TO_SCRAPE * WEEKS_PER_MONTH):
                  print(f"  Week {i+1}/{MONTHS_TO_SCRAPE * WEEKS_PER_MONTH}...")
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

          finally:
              await context.close()
              await browser.close()

          return self.data
