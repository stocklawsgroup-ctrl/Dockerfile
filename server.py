"""
Simple web interface to trigger the Airbnb scraper.
Visit /run?key=gogo2026 to run all properties.
Visit /run/goettingen?key=gogo2026 to run one property.
"""

import subprocess
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

SECRET_KEY = "gogo2026"
PORT = int(os.environ.get("PORT", 10000))


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # suppress access logs

    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        key = params.get("key", [""])[0]

        # Home page
        if parsed.path == "/":
            self.send_html("""
                <h2>Airbnb Scraper</h2>
                <p>Use the links below to run the scraper:</p>
                <ul>
                    <li><a href="/run?key=gogo2026">Run ALL properties</a></li>
                    <li><a href="/run/goettingen?key=gogo2026">Run goettingen only</a></li>
                    <li><a href="/run/iwatoyama?key=gogo2026">Run iwatoyama only</a></li>
                    <li><a href="/run/Comodita?key=gogo2026">Run Comodita only</a></li>
                    <li><a href="/run/konoha?key=gogo2026">Run konoha only</a></li>
                </ul>
            """)
            return

        # Auth check
        if key != SECRET_KEY:
            self.send_html("<h2>Unauthorized</h2>", status=403)
            return

        # Run scraper
        if parsed.path.startswith("/run"):
            parts = parsed.path.strip("/").split("/")
            prop = parts[1] if len(parts) > 1 else None
            cmd = ["python3", "test_scrape.py"]
            if prop:
                cmd.append(prop)

            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=600,
                    cwd="/app"
                )
                output = result.stdout + result.stderr
                if not output:
                    output = "(no output)"
            except subprocess.TimeoutExpired:
                output = "Timed out after 10 minutes"
            except Exception as e:
                output = f"Error: {e}"

            self.send_html(f"""
                <h2>Scraper Output</h2>
                <pre style="background:#111;color:#0f0;padding:20px;white-space:pre-wrap">{output}</pre>
                <a href="/">Back</a>
            """)
            return

        # Debug endpoint
        if parsed.path == "/debug":
            tests = {}
            for cmd, label in [
                (["python3", "--version"], "python version"),
                (["python3", "-c", "import playwright; print('playwright ok')"], "playwright import"),
                (["python3", "-c", "import os; print(os.listdir('/app'))"], "app files"),
                (["python3", "-c", "import json; f=open('/app/properties.json'); print(f.read())"], "properties.json"),
                (["find", "/root/.cache/ms-playwright", "-name", "chrome", "-type", "f"], "chromium binary"),
            ]:
                try:
                    r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                    tests[label] = (r.stdout + r.stderr).strip() or "(empty)"
                except Exception as e:
                    tests[label] = f"ERROR: {e}"
            rows = "".join(f"<tr><td><b>{k}</b></td><td><pre>{v}</pre></td></tr>" for k, v in tests.items())
            self.send_html(f"<h2>Debug</h2><table border=1 cellpadding=8>{rows}</table>")
            return

        self.send_html("<h2>Not Found</h2>", status=404)

    def send_html(self, body, status=200):
        html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>body{{font-family:sans-serif;max-width:900px;margin:40px auto;padding:20px}}</style>
</head><body>{body}</body></html>"""
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode())


if __name__ == "__main__":
    print(f"Starting server on port {PORT}")
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
