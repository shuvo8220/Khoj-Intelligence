import os
import sys
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from playwright.async_api import async_playwright

# Path fix
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

# Import both crawlers
from backend.crawler import UniversalCrawler
from backend.crawler_image import UniversalImageCrawler # <--- Import Image Crawler
from backend.summarizer import TextSummarizer

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# ==============================================================================
# GLOBAL RESOURCES
# ==============================================================================
GLOBAL_VARS = {
    "playwright": None,
    "browser": None,
    "summarizer": None
}

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🌍 Initializing Global Resources...")
    
    print("🧠 Loading AI Model...")
    GLOBAL_VARS["summarizer"] = TextSummarizer()
    
    print("🚀 Launching Headless Browser...")
    GLOBAL_VARS["playwright"] = await async_playwright().start()
    GLOBAL_VARS["browser"] = await GLOBAL_VARS["playwright"].chromium.launch(
        headless=True,
        args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
    )
    
    print("✅ SERVER READY!")
    yield
    
    print("🛑 Shutting down...")
    await GLOBAL_VARS["browser"].close()
    await GLOBAL_VARS["playwright"].stop()

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

os.makedirs("crawled_data", exist_ok=True)
app.mount("/data", StaticFiles(directory="crawled_data"), name="data")

MAX_USERS = 500
semaphore = asyncio.Semaphore(MAX_USERS)
waiting_users = 0

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    global waiting_users
    await websocket.accept()
    
    try:
        if semaphore.locked():
            waiting_users += 1
            await websocket.send_json({"message": f"Server busy. Queue: {waiting_users}", "type": "warning"})

        async with semaphore:
            if waiting_users > 0: waiting_users -= 1
            
            # 1. Receive Payload (URL + Limit + Mode)
            data = await websocket.receive_json()
            url = data.get("url")
            limit = int(data.get("limit", 5))
            mode = data.get("mode", "text")  # <--- Receive Mode
            
            print(f"📡 Request: URL={url}, Mode={mode.upper()}") # Debug Log
            await websocket.send_json({"message": f"🚀 Starting {mode.upper()} Crawl...", "type": "success"})

            # 2. Logic to choose Crawler based on Mode
            if mode == "image":
                # --- IMAGE MODE ---
                crawler = UniversalImageCrawler(
                    start_url=url, 
                    max_pages=limit, 
                    output_dir="crawled_data", 
                    websocket=websocket, 
                    browser_instance=GLOBAL_VARS["browser"]
                )
            else:
                # --- TEXT MODE (Default) ---
                crawler = UniversalCrawler(
                    start_url=url, 
                    max_pages=limit, 
                    output_dir="crawled_data", 
                    websocket=websocket, 
                    browser_instance=GLOBAL_VARS["browser"],
                    summarizer_instance=GLOBAL_VARS["summarizer"]
                )
                
            await crawler.run()
            
            await websocket.send_json({"message": "Done", "type": "finished"})
            
    except Exception as e:
        print(f"WS Error: {e}")
        try: await websocket.send_json({"message": f"Error: {str(e)}", "type": "error"})
        except: pass
    finally:
        try: await websocket.close()
        except: pass

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