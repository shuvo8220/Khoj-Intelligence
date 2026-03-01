import os
import asyncio
import re
import hashlib
import trafilatura
import time  # <--- Added for Timer
from collections import deque
from urllib.parse import urlparse, urljoin
from datetime import datetime
from playwright.async_api import async_playwright
from backend.utils import FileManager

class UniversalCrawler:
    def __init__(self, start_url, max_pages=0, output_dir="crawled_data", websocket=None, browser_instance=None, summarizer_instance=None):
        self.start_url = start_url
        self.max_pages = int(max_pages)
        self.websocket = websocket
        self.browser = browser_instance
        self.summarizer = summarizer_instance
        
        parsed = urlparse(start_url)
        self.domain = parsed.netloc
        self.base_url = f"{parsed.scheme}://{parsed.netloc}"
        
        self.safe_domain = re.sub(r'[^\w]', '_', self.domain)
        self.output_folder = os.path.join(output_dir, self.safe_domain)
        self.auth_folder = "auth_sessions"
        
        FileManager.ensure_directories([self.output_folder, self.auth_folder])
        self.is_social = any(x in self.domain for x in ["linkedin.com", "twitter.com", "x.com"])
        self.visited = set()
        self.queue = deque([start_url])
        
        # INCREASED BATCH SIZE FOR SPEED
        self.BATCH_SIZE = 5 

    async def log(self, message, type="info"):
        print(f"[{type.upper()}] {message}")
        if self.websocket:
            try: await self.websocket.send_json({"message": message, "type": type})
            except: pass

    async def _handle_login(self, context, page):
        # Login logic (kept simple for speed)
        pass

    def _clean_garbage(self, text):
        if not text: return ""
        lines = text.split('\n')
        clean_lines = []
        garbage = ["read more", "click here", "subscribe", "login", "cookie", "copyright", "just a moment", "verify"]
        for line in lines:
            line = line.strip()
            if len(line) > 20 and not any(g in line.lower() for g in garbage):
                clean_lines.append(line)
        return "\n".join(clean_lines)

    def _get_filename(self, url, title):
        """Generates filename using Title + Short Hash"""
        # Clean title to be filename safe
        safe_title = re.sub(r'[^\w\-]', '_', title)[:50]
        if not safe_title: safe_title = "page"
        
        # Add hash to ensure uniqueness even if titles are same
        url_hash = hashlib.md5(url.encode()).hexdigest()[:6]
        return f"{safe_title}_{url_hash}.md"

    async def _process_page(self, context, url):
        page = await context.new_page()
        
        # 1. AGGRESSIVE BLOCKING (Huge Speed Boost)
        # Block images, media, fonts, and other non-essential types
        await page.route("**/*", lambda route: route.abort() 
                         if route.request.resource_type in ["image", "media", "font", "stylesheet", "other"] 
                         else route.continue_())

        try:
            # 2. FAST NAVIGATION
            try:
                # domcontentloaded is much faster than networkidle
                await page.goto(url, timeout=25000, wait_until="domcontentloaded")
            except:
                await self.log(f"Timeout (partial load): {url}", "warning")

            # 3. SMART CLOUDFLARE CHECK
            title = await page.title()
            if "Just a moment" in title or "Cloudflare" in title:
                await self.log(f"🛡️ Security Check on {url}. Waiting...", "warning")
                # Poll every 1s instead of hard sleep
                for _ in range(10):
                    await asyncio.sleep(1)
                    title = await page.title()
                    if "Just a moment" not in title:
                        break

            # 4. QUICK SCROLL (Minimal wait)
            await page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
            await page.wait_for_timeout(1000) # Reduced from 2000

            # 5. EXTRACT TEXT
            html = await page.content()
            raw_text = ""
            
            if self.is_social:
                raw_text = await page.locator("body").inner_text()
            else:
                # Fast extraction settings
                raw_text = trafilatura.extract(html, output_format="markdown", include_images=False, include_links=True)
                if not raw_text: 
                    raw_text = await page.locator("body").inner_text()

            # 6. SAVE DATA
            clean_text = self._clean_garbage(raw_text)

            if clean_text and len(clean_text) > 100 and "Just a moment" not in title:
                # Summary Generation
                summary = self.summarizer.summarize(clean_text)
                
                # Generate specific filename
                filename = self._get_filename(url, title)
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # Save using Utility
                saved_file = FileManager.save_markdown(
                    folder=self.output_folder,
                    filename=filename,
                    title=title,
                    url=url,
                    date=timestamp,
                    summary=summary,
                    content=clean_text
                )
                
                if self.websocket:
                    await self.websocket.send_json({"type": "file_saved", "domain": self.safe_domain, "filename": saved_file})
                
                await self.log(f" Saved: {saved_file}", "success")
            else:
                await self.log(f" Skipped (Empty/Blocked): {url}", "warning")
            
            # 7. FAST LINK FINDER (JS Evaluation)
            links = await page.evaluate("""() => {
                return Array.from(document.querySelectorAll('a[href]')).map(a => a.href);
            }""")
            
            new_links = []
            for href in links:
                href = href.split('#')[0].rstrip('/')
                if self.domain in href and href not in self.visited:
                    bad_ext = ('.pdf', '.zip', '.png', '.jpg', '.css', '.js')
                    if not href.lower().endswith(bad_ext):
                        new_links.append(href)
            
            return new_links

        except Exception as e:
            await self.log(f"Error: {str(e)}", "error")
            return []
        finally:
            await page.close()

    async def run(self):
        # --- START TIMER ---
        start_time = time.time()
        await self.log(f" Processing: {self.start_url}", "success")
        
        if not self.browser:
            await self.log(" Browser error", "error")
            return

        try:
            context = await self.browser.new_context(
                viewport={'width':1920,'height':1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            
            if self.is_social:
                p = await context.new_page()
                await self._handle_login(context, p)
                await p.close()

            while self.queue and (self.max_pages == 0 or len(self.visited) < self.max_pages):
                batch = []
                while self.queue and len(batch) < self.BATCH_SIZE:
                    url = self.queue.popleft()
                    if url not in self.visited:
                        self.visited.add(url)
                        batch.append(url)
                    if self.max_pages > 0 and len(self.visited) >= self.max_pages: break

                if not batch: break
                
                await self.log(f"⚡ Processing batch of {len(batch)}...", "info")
                tasks = [self._process_page(context, url) for url in batch]
                results = await asyncio.gather(*tasks)
                
                for links in results:
                    for link in links:
                        if link not in self.visited and link not in self.queue:
                            self.queue.append(link)

            await context.close()
            
            # --- END TIMER & CALCULATE ---
            end_time = time.time()
            total_time = round(end_time - start_time, 2)
            
            await self.log(f"Job Finished! Total Pages: {len(self.visited)}", "success")
            await self.log(f" Total Execution Time: {total_time} seconds", "success")
            
        except Exception as e:
            await self.log(f"Critical Error: {str(e)}", "error")