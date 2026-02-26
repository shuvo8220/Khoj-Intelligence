import os
import asyncio
import re
import hashlib
import trafilatura
from collections import deque
from urllib.parse import urlparse, urljoin, urldefrag
from datetime import datetime
from playwright.async_api import async_playwright

class UniversalCrawler:
    def __init__(self, start_url, max_pages=0, output_dir="crawled_data", websocket=None):
        self.start_url = start_url
        self.max_pages = int(max_pages)
        self.websocket = websocket
        
        parsed = urlparse(start_url)
        self.domain = parsed.netloc
        self.base_url = f"{parsed.scheme}://{parsed.netloc}"
        
        # Output Setup
        self.safe_domain = re.sub(r'[^\w]', '_', self.domain)
        self.output_folder = os.path.join(output_dir, self.safe_domain)
        self.auth_folder = "auth_sessions"
        
        os.makedirs(self.output_folder, exist_ok=True)
        os.makedirs(self.auth_folder, exist_ok=True)
        
        self.is_linkedin = "linkedin.com" in self.domain
        self.is_twitter = "twitter.com" in self.domain or "x.com" in self.domain
        self.is_social = self.is_linkedin or self.is_twitter

        self.visited = set()
        self.queue = deque([start_url])
        self.BATCH_SIZE = 5

    async def log(self, message, type="info"):
        print(f"[{type.upper()}] {message}")
        if self.websocket:
            await self.websocket.send_json({"message": message, "type": type})

    def _get_filename(self, url, title):
        url_hash = hashlib.md5(url.encode()).hexdigest()[:6]
        safe_title = re.sub(r'[^\w\-]', '_', title)[:40] or "page"
        return f"{safe_title}_{url_hash}.md"

    async def _process_page(self, context, url):
        page = await context.new_page()
        # Block Images for Speed
        await page.route("**/*", lambda route: route.abort() if route.request.resource_type in ["image", "media", "font", "stylesheet"] else route.continue_())

        try:
            try:
                await page.goto(url, timeout=15000, wait_until="domcontentloaded")
            except:
                await self.log(f"Timeout on {url}", "warning")

            html = await page.content()
            title = await page.title()
            
            extracted_text = trafilatura.extract(
                html, 
                output_format="markdown", 
                include_images=False, 
                include_links=True
            )
            
            final_content = extracted_text if extracted_text else ""

            if len(final_content) > 50:
                filename = self._get_filename(url, title)
                filepath = os.path.join(self.output_folder, filename)
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(f"# {title}\n\n> **Source:** [{url}]({url})\n> **Date:** {timestamp}\n\n---\n\n{final_content}")
                
                await self.log(f"💾 Saved: {filename}", "success")
                
                if self.websocket:
                    await self.websocket.send_json({"type": "file_saved", "domain": self.safe_domain, "filename": filename})
            
            links = await page.evaluate("() => Array.from(document.querySelectorAll('a')).map(a => a.href)")
            new_links = []
            for href in links:
                href = href.split('#')[0].rstrip('/')
                if href.startswith(self.base_url) and href not in self.visited:
                    if not href.lower().endswith(('.pdf', '.jpg', '.png', '.zip')):
                        new_links.append(href)
            return new_links

        except Exception as e:
            await self.log(f"Error processing {url}: {str(e)}", "error")
            return []
        finally:
            await page.close()

    async def run(self):
        await self.log(f"🚀 STARTING TEXT CRAWLER: {self.start_url}", "success")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False, args=['--disable-blink-features=AutomationControlled', '--start-maximized'])
            context = await browser.new_context(viewport={'width':1280,'height':720})

            while self.queue and (self.max_pages == 0 or len(self.visited) < self.max_pages):
                batch = []
                while self.queue and len(batch) < self.BATCH_SIZE:
                    url = self.queue.popleft()
                    if url not in self.visited:
                        self.visited.add(url)
                        batch.append(url)
                    if self.max_pages > 0 and len(self.visited) >= self.max_pages: break

                if not batch: break
                await self.log(f"⚡ Processing Batch: {len(batch)} URLs...", "info")
                tasks = [self._process_page(context, url) for url in batch]
                results = await asyncio.gather(*tasks)
                for links in results:
                    for link in links:
                        if link not in self.visited and link not in self.queue: self.queue.append(link)

            await browser.close()
            await self.log(f"✅ Text Crawling Done!", "success")