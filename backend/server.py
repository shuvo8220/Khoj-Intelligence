import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__)) # backend folder
parent_dir = os.path.dirname(current_dir) # root folder (UltimateCrawler)
sys.path.append(parent_dir)


from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from backend.crawler import UniversalCrawler
from backend.crawler_image import UniversalImageCrawler
import asyncio

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("crawled_data", exist_ok=True)
app.mount("/data", StaticFiles(directory="crawled_data"), name="data")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        data = await websocket.receive_json()
        url = data.get("url")
        limit = int(data.get("limit", 5))
        mode = data.get("mode", "text") # <--- Get Mode (text/image)
        
        if mode == "image":
            # Run Image Crawler
            crawler = UniversalImageCrawler(url, limit, "crawled_data", websocket)
        else:
            # Run Text Crawler
            crawler = UniversalCrawler(url, limit, "crawled_data", websocket)
            
        await crawler.run()
        await websocket.close()
    except Exception as e:
        print(f"WebSocket Error: {e}")

@app.get("/api/files")
def get_files():
    data = []
    root = "crawled_data"
    if not os.path.exists(root): return []
    for domain in os.listdir(root):
        d_path = os.path.join(root, domain)
        if os.path.isdir(d_path):
            files = [f for f in os.listdir(d_path) if f.endswith(".md")]
            data.append({"domain": domain, "files": files})
    return data