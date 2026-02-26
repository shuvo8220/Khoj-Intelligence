import os
import asyncio
import re
import hashlib
import requests
from collections import deque
from urllib.parse import urlparse, urljoin
from datetime import datetime
from playwright.async_api import async_playwright

class UniversalImageCrawler:
    def __init__(self, start_url, max_pages=0, output_dir="crawled_data", websocket=None):
        self.start_url = start_url
        self.max_pages = int(max_pages)
        self.websocket = websocket
        
        parsed = urlparse(start_url)
        self.domain = parsed.netloc
        self.base_url = f"{parsed.scheme}://{parsed.netloc}"
        
        self.safe_domain = re.sub(r'[^\w]', '_', self.domain)
        self.output_folder = os.path.join(output_dir, self.safe_domain)
        self.images_folder = os.path.join(self.output_folder, "images")
        
        os.makedirs(self.output_folder, exist_ok=True)
        os.makedirs(self.images_folder, exist_ok=True)
        
        self.auth_folder = "auth_sessions"
        os.makedirs(self.auth_folder, exist_ok=True)
        
        self.visited = set()
        self.queue = deque([start_url])
        self.BATCH_SIZE = 6

    async def log(self, message, type="info"):
        print(f"[{type.upper()}] {message}")
        if self.websocket:
            await self.websocket.send_json({"message": message, "type": type})

    def _get_filename(self, url, title):
        url_hash = hashlib.md5(url.encode()).hexdigest()[:6]
        safe_title = re.sub(r'[^\w\-]', '_', title)[:30] or "gallery"
        return f"{safe_title}_{url_hash}.md"

    def _download_image(self, img_url):
        try:
            if not img_url or img_url.startswith("data:"): return None
            if not img_url.startswith(('http', 'https')):
                img_url = urljoin(self.base_url, img_url)
            
            clean_url = img_url.split('?')[0]
            ext = os.path.splitext(clean_url)[1]
            if not ext or len(ext) > 5: ext = ".jpg"
            
            img_hash = hashlib.md5(img_url.encode()).hexdigest()[:10]
            filename = f"img_{img_hash}{ext}"
            local_path = os.path.join(self.images_folder, filename)
            rel_path = f"images/{filename}"

            if os.path.exists(local_path): return rel_path

            r = requests.get(img_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5, stream=True)
            if r.status_code == 200:
                with open(local_path, 'wb') as f:
                    for chunk in r.iter_content(1024):
                        f.write(chunk)
                return rel_path
        except:
            pass
        return None

    async def _process_page(self, context, url):
        page = await context.new_page()
        # Block fonts/css but Allow Images
        await page.route("**/*", lambda route: route.abort() if route.request.resource_type in ["font", "stylesheet", "media"] else route.continue_())

        try:
            await page.goto(url, timeout=20000, wait_until="domcontentloaded")
            for _ in range(3):
                await page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
                await page.wait_for_timeout(1000)
            
            image_urls = await page.evaluate("""() => {
                const images = Array.from(document.querySelectorAll('img, source'));
                const urls = new Set();
                images.forEach(img => {
                    if (img.srcset) urls.add(img.srcset.split(',').pop().trim().split(' ')[0]);
                    else if (img.dataset.src) urls.add(img.dataset.src);
                    else if (img.src) urls.add(img.src);
                });
                return Array.from(urls);
            }""")

            valid_images = []
            for img in image_urls:
                if not img.endswith('.svg') and 'icon' not in img:
                    local_path = self._download_image(img)
                    if local_path: valid_images.append(local_path)

            if valid_images:
                title = await page.title()
                filename = self._get_filename(url, title)
                filepath = os.path.join(self.output_folder, filename)
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                content = f"# 📸 Gallery: {title}\n\n> **Source:** [{url}]({url})\n> **Time:** {timestamp}\n> **Images:** {len(valid_images)}\n\n---\n\n"
                for img_path in valid_images:
                    content += f"![Image]({img_path})\n"
                
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)

                await self.log(f"💾 Saved {len(valid_images)} images: {filename}", "success")
                if self.websocket:
                    await self.websocket.send_json({"type": "file_saved", "domain": self.safe_domain, "filename": filename})

            new_links = []
            links = await page.evaluate("() => Array.from(document.querySelectorAll('a')).map(a => a.href)")
            for href in links:
                href = href.split('#')[0].rstrip('/')
                if href.startswith(self.base_url) and href not in self.visited:
                        if not href.lower().endswith(('.pdf', '.zip')):
                            new_links.append(href)
            return new_links

        except Exception as e:
            await self.log(f"Error: {e}", "error")
            return []
        finally:
            await page.close()

    async def run(self):
        await self.log(f"🚀 STARTING IMAGE CRAWLER: {self.start_url}", "success")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False, args=['--disable-blink-features=AutomationControlled', '--start-maximized'])
            context = await browser.new_context(viewport={'width':1920,'height':1080})

            while self.queue and (self.max_pages == 0 or len(self.visited) < self.max_pages):
                batch = []
                while self.queue and len(batch) < self.BATCH_SIZE:
                    url = self.queue.popleft()
                    if url not in self.visited:
                        self.visited.add(url)
                        batch.append(url)
                    if self.max_pages > 0 and len(self.visited) >= self.max_pages: break

                if not batch: break
                await self.log(f"⚡ extracting images from {len(batch)} pages...", "info")
                tasks = [self._process_page(context, url) for url in batch]
                results = await asyncio.gather(*tasks)
                for links in results:
                    for link in links:
                        if link not in self.visited and link not in self.queue: self.queue.append(link)

            await browser.close()
            await self.log(f"✅ Image Crawling Done!", "success")