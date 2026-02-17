import os
import asyncio
import re
import hashlib
import requests
import trafilatura
from collections import deque
from urllib.parse import urlparse, urljoin, urldefrag
from datetime import datetime
from playwright.async_api import async_playwright

class UniversalCrawler:
    def __init__(self, start_url, max_pages, output_dir, websocket=None):
        self.start_url = start_url
        self.max_pages = max_pages
        self.websocket = websocket
        
        parsed = urlparse(start_url)
        self.domain = parsed.netloc
        self.base_url = f"{parsed.scheme}://{parsed.netloc}"
        
        self.is_social = "linkedin.com" in self.domain or "twitter.com" in self.domain
        
        safe_domain = re.sub(r'[^\w]', '_', self.domain)
        self.output_folder = os.path.join(output_dir, safe_domain)
        self.images_folder = os.path.join(self.output_folder, "images")
        
        os.makedirs(self.images_folder, exist_ok=True)
        self.visited = set()
        self.queue = deque([start_url])

    async def log(self, message, type="info"):
        print(f"[{type.upper()}] {message}")
        if self.websocket:
            await self.websocket.send_json({"message": message, "type": type})

    def _get_filename(self, url, title):
        url_hash = hashlib.md5(url.encode()).hexdigest()[:6]
        safe_title = re.sub(r'[^\w\-]', '_', title)[:40] or "page"
        return f"{safe_title}_{url_hash}.md"

    def _download_image(self, img_url):
        try:
            if not img_url or img_url.startswith("data:"): return None
            if not img_url.startswith(('http', 'https')):
                img_url = urljoin(self.base_url, img_url)
            
            ext = os.path.splitext(urlparse(img_url).path)[1]
            if not ext or len(ext) > 5: ext = ".jpg"
            
            filename = f"img_{hashlib.md5(img_url.encode()).hexdigest()[:10]}{ext}"
            local_path = os.path.join(self.images_folder, filename)
            
            if not os.path.exists(local_path):
                headers = {"User-Agent": "Mozilla/5.0"}
                r = requests.get(img_url, headers=headers, timeout=10)
                if r.status_code == 200:
                    with open(local_path, 'wb') as f:
                        f.write(r.content)
            
            # Return relative path for Markdown
            return f"images/{filename}"
        except:
            return None

    async def run(self):
        await self.log(f" Starting crawl: {self.start_url}", "success")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False, slow_mo=50)
            context = await browser.new_context(viewport={'width':1920,'height':1080})
            page = await context.new_page()

            while self.queue and len(self.visited) < self.max_pages:
                url = self.queue.popleft()
                if url in self.visited: continue

                await self.log(f"Processing: {url}", "info")
                
                try:
                    # Smart Navigation (Tidio Fix)
                    try:
                        await page.goto(url, timeout=30000, wait_until="domcontentloaded")
                        await page.wait_for_timeout(3000)
                    except:
                        await self.log("Timeout loading page, proceeding anyway...", "warning")

                    # Scroll for Lazy Loading
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await page.wait_for_timeout(2000)

                    title = await page.title()
                    final_content = ""

                    if self.is_social:
                        # Social Logic
                        content = ""
                        for _ in range(3):
                            await page.evaluate("window.scrollBy(0, 800)")
                            await asyncio.sleep(1)
                            # Simplified selector for demo
                            content += await page.evaluate("document.body.innerText")
                        final_content = content[:5000] # Limit size
                    else:
                        # General/Apple Logic
                        html = await page.content()
                        text = trafilatura.extract(html, output_format="markdown", include_images=True)
                        
                        # Image Extraction (Apple Fix)
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

                        img_map = {}
                        for url_link in image_urls:
                            local = self._download_image(url_link)
                            if local: img_map[url_link] = local

                        if text:
                            for remote, local in img_map.items():
                                text = text.replace(remote, local)
                            
                            gallery = "\n\n### 📸 Detected Images\n"
                            for local in img_map.values():
                                gallery += f"![Img]({local})\n"
                            
                            final_content = text + gallery

                    # Save File
                    if len(final_content) > 50:
                        filename = self._get_filename(url, title)
                        filepath = os.path.join(self.output_folder, filename)
                        
                        with open(filepath, "w", encoding="utf-8") as f:
                            f.write(f"# {title}\n> **Source:** {url}\n\n{final_content}")
                        
                        await self.log(f"💾 Saved: {filename}", "success")
                    
                    # Recursive Links
                    if not self.is_social:
                        links = await page.query_selector_all('a')
                        for link in links:
                            href = await link.get_attribute('href')
                            if href:
                                abs_url = urljoin(url, href)
                                if urlparse(abs_url).netloc == self.domain and abs_url not in self.visited:
                                    self.queue.append(abs_url)

                    self.visited.add(url)
                    
                except Exception as e:
                    await self.log(f"Error: {str(e)}", "error")

            await browser.close()
            await self.log("✅ Crawling Completed!", "success")