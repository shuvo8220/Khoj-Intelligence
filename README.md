
![alt text](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python)

![alt text](https://img.shields.io/badge/React-18-61DAFB?style=for-the-badge&logo=react)

![alt text](https://img.shields.io/badge/FastAPI-0.95%2B-009688?style=for-the-badge&logo=fastapi)

![alt text](https://img.shields.io/badge/Playwright-Stealth-orange?style=for-the-badge&logo=playwright)

![alt text](https://img.shields.io/badge/Tailwind-CSS-38B2AC?style=for-the-badge&logo=tailwind-css)




Khoj is our first core product, an advanced web crawling and content intelligence tool designed to extract meaningful information from any website efficiently. The system automatically scans and processes web pages, filters out irrelevant elements (such as ads, scripts, and clutter), and parses only high-value content including structured text, images, and embedded media. Unlike traditional crawlers, Khoj is optimized to handle large and complex websites with high data volumes. It intelligently identifies important sections of a page, organizes the extracted data, and delivers clean, usable output for further analysis or integration. With its ability to process heavy websites at scale while maintaining accuracy and performance, Khoj serves as a powerful foundation for data-driven applications, research systems, and AI-powered platforms.The Ultimate Crawler is a powerful, full-stack web scraping solution combining the raw power of Python (FastAPI) with a modern, responsive React (Vite) interface. It is designed to extract text and high-resolution images from complex websites (like Apple, Tidio) and social media platforms (LinkedIn, Twitter/X) while bypassing modern anti-bot protections.


 **Key Features**
 Full-Stack Architecture: Seamless integration between a robust Python backend and a beautiful React frontend.
 Real-Time Logging: View live crawling progress and status updates via WebSockets.
 Stealth Mode: Uses Playwright with custom arguments to bypass Cloudflare, CAPTCHAs, and bot detection.
 Smart Image Extraction: Intelligent algorithm to fetch the highest resolution images from srcset, data-src, and lazy-loaded elements (perfect for Apple-like sites).
 Social Media Ready: Supports infinite scroll and session persistence (cookies) for LinkedIn and Twitter feeds.
 Organized Output: Automatically generates individual Markdown files with source references and categorized image folders.
 One-Click Start: The entire stack (Backend + Frontend) launches with a single command: python main.py.

**Tech Stack & Libraries**
This project leverages industry-standard libraries to ensure performance and reliability.
 **Backend (Python)**
Library	Purpose
FastAPI	High-performance async API server with WebSocket support.
Playwright	Headless browser automation for rendering JavaScript-heavy sites.
Trafilatura	Precision text extraction and main content parsing.
Uvicorn	ASGI server implementation to run FastAPI.
Requests	Efficient handling of image downloads.
Nest Asyncio	Patches the event loop to allow nested async calls.

 **Frontend (JavaScript/React)**
Library	Purpose
React.js	Building the interactive user interface.
Vite	Next-generation frontend tooling and build system.
Tailwind CSS	Utility-first CSS framework for modern styling.
Lucide React	Beautiful, consistent icon set.
React Markdown	Rendering the crawled Markdown data directly in the UI.

**Installation & Usage**
Prerequisites
Ensure you have the following installed on your machine:
       Python (3.8 or higher)
       Node.js & npm (for the frontend)

1. Clone the Repository
```bash
   git clone https://github.com/your-username/ultimate-crawler.git
   cd ultimate-crawler
```
2.Run the Project (The Magic Command )
You don't need to manually install dependencies or start servers separately. The main.py script handles everything.
```bash
   python main.py
```
Note: On the first run, the script will automatically:
Install all Python dependencies from requirements.txt.
Install Playwright browsers (Chromium).
Install Node.js modules for the frontend (npm install).
Launch the Backend Server and the React Frontend.

**Project Structure**
```bash
Khoj/
│
├── backend/                 # Python Backend Logic
│   ├── crawler.py           # Core crawling engine & logic
│   └── server.py            # FastAPI server & WebSocket endpoints
│
├── frontend/                # React Frontend Application
│   ├── src/                 # UI Source Code (Components, Hooks)
│   ├── package.json         # Frontend dependencies
│   └── tailwind.config.js   # Styling configuration
│
├── crawled_data/            # Output Directory (Auto-generated)
│   └── www_example_com/     # Domain-specific folders
│       ├── images/          # Downloaded high-res images
│       └── Page_Title.md    # Extracted content in Markdown
│
├── auth_sessions/           # Session cookies (for Social Media)
├── requirements.txt         # Python dependency list
└── main.py                  # Master Launcher Script

```

**How to Use**
Launch: Run python main.py and wait for the browser to open (usually at http://localhost:5173).
Configure:
Target URL: Enter the website URL (e.g., https://www.apple.com or https://www.linkedin.com/feed/).
Page Limit: Set how many pages or scroll depths you want to crawl.
Start: Click the Start Extraction button.
Monitor: Watch the Live Logs panel on the left to see the crawler in action.
View Results: Once finished, click on the files in the Output Files panel on the right to preview the extracted text and images instantly.<img width="1920" height="1080" alt="Screenshot (444)" src="https://github.com/user-attachments/assets/6a759991-13fb-435f-869f-57e42a120a80" />

