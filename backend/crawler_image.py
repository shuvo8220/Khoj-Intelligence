import os
import asyncio
import re
import hashlib
import time
from collections import deque
from urllib.parse import urlparse
from datetime import datetime
from playwright.async_api import async_playwright

class UniversalImageCrawler:
    def __init__(self, start_url, max_pages=0, output_dir="crawled_data", websocket=None, browser_instance=None):
        self.start_url = start_url
        self.max_pages = int(max_pages)
        self.websocket = websocket
        self.browser = browser_instance 
        
        parsed = urlparse(start_url)
        self.domain = parsed.netloc
        self.base_url = f"{parsed.scheme}://{parsed.netloc}"
        self.safe_domain = re.sub(r'[^\w]', '_', self.domain)
        self.output_folder = os.path.join(output_dir, self.safe_domain)
        self.images_folder = os.path.join(self.output_folder, "images")
        
        os.makedirs(self.images_folder, exist_ok=True)
        self.visited = set()
        self.queue = deque([start_url])
        self.BATCH_SIZE = 5 

    async def log(self, message, type="info"):
        if self.websocket:
            try: await self.websocket.send_json({"message": message, "type": type})
            except: pass

    async def _process_page(self, context, url):
        page = await context.new_page()
        captured_files = []

        # অপ্রয়োজনীয় রিসোর্স ব্লক করা (স্পিড বাড়ানোর জন্য)
        await page.route("**/*", lambda route: route.abort() if route.request.resource_type in ["font", "media", "stylesheet"] else route.continue_())

        async def capture_image(response):
            if response.request.resource_type == "image":
                try:
                    img_url = response.url
                    if not img_url.startswith("http") or any(x in img_url for x in ["google", "analytics", "ads"]): return

                    buffer = await response.body()
                    if len(buffer) > 8000: # ৮ কেবি'র নিচের ফাইল বাদ (আইকন ফিল্টার)
                        file_hash = hashlib.md5(img_url.encode()).hexdigest()[:10]
                        ext = ".jpg"
                        if "png" in response.headers.get("content-type", ""): ext = ".png"
                        elif "webp" in response.headers.get("content-type", ""): ext = ".webp"
                        
                        filename = f"img_{file_hash}{ext}"
                        filepath = os.path.join(self.images_folder, filename)

                        if not os.path.exists(filepath):
                            with open(filepath, "wb") as f: f.write(buffer)
                            captured_files.append(f"images/{filename}")
                except: pass

        page.on("response", capture_image)

        try:
            # পেজ লোড টাইম আউট কমিয়ে ৩০ সেকেন্ড করা হয়েছে
            await page.goto(url, timeout=30000, wait_until="domcontentloaded")

            # ফাস্ট অটো স্ক্রলিং (JS দিয়ে দ্রুত স্ক্রল)
            await page.evaluate("""async () => {
                await new Promise(resolve => {
                    let totalHeight = 0;
                    let distance = 1000;
                    let timer = setInterval(() => {
                        window.scrollBy(0, distance);
                        totalHeight += distance;
                        if(totalHeight >= document.body.scrollHeight || totalHeight > 8000){
                            clearInterval(timer);
                            resolve();
                        }
                    }, 300); // প্রতি ৩০০ মিলিসেকেন্ডে ১০০০ পিক্সেল স্ক্রল
                });
            }""")
            
            await asyncio.sleep(1) # স্ক্রল শেষে জাস্ট ১ সেকেন্ড ওয়েট

            if captured_files:
                title = (await page.title())[:30]
                md_filename = f"gallery_{hashlib.md5(url.encode()).hexdigest()[:5]}.md"
                md_path = os.path.join(self.output_folder, md_filename)
                
                content = f"# 📸 Captured: {title}\n\nURL: {url}\n\n---\n\n"
                for img_path in list(set(captured_files)):
                    content += f"![Image]({img_path})\n"
                
                with open(md_path, "w", encoding="utf-8") as f: f.write(content)
                if self.websocket:
                    await self.websocket.send_json({"type": "file_saved", "domain": self.safe_domain, "filename": md_filename})

            # লিঙ্ক কালেকশন
            links = await page.evaluate("() => Array.from(document.querySelectorAll('a')).map(a => a.href)")
            new_links = [l.split('#')[0].rstrip('/') for l in links if l.startswith(self.base_url)]
            
            await page.close()
            return new_links

        except:
            await page.close()
            return []

    async def run(self):
        start_time = time.time()
        await self.log(f"🚀 Speed Image Crawler Started", "success")
        
        own_browser = False
        if not self.browser:
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(headless=True)
            own_browser = True

        try:
            context = await self.browser.new_context(
                viewport={'width': 1280, 'height': 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            )

            while self.queue and (self.max_pages == 0 or len(self.visited) < self.max_pages):
                # ব্যাচ প্রসেসিং (একসাথে অনেক লিঙ্ক প্রসেস হবে)
                batch = []
                while self.queue and len(batch) < self.BATCH_SIZE:
                    url = self.queue.popleft()
                    if url not in self.visited:
                        self.visited.add(url)
                        batch.append(url)
                    if self.max_pages > 0 and len(self.visited) >= self.max_pages: break

                if not batch: break
                
                await self.log(f"⚡ Processing batch of {len(batch)} pages...", "info")
                tasks = [self._process_page(context, url) for url in batch]
                results = await asyncio.gather(*tasks) # একসাথে সব টাস্ক রান হবে
                
                for links in results:
                    for link in links:
                        if link not in self.visited: self.queue.append(link)
            
            await context.close()
            await self.log(f"🏁 Fast Finish! Time: {round(time.time()-start_time)}s", "success")

        finally:
            if own_browser: await self.browser.close()