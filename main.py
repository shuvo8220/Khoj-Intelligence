import os
import sys
import subprocess
import time
import threading
import webbrowser

def install_python_deps():
    print("📦 Installing Python dependencies...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    print("🌍 Installing Playwright Browsers...")
    os.system("playwright install chromium")

def run_backend():
    print("🐍 Starting Backend Server (FastAPI)...")
    # Using python -m uvicorn to ensure path consistency
    subprocess.run([sys.executable, "-m", "uvicorn", "backend.server:app", "--host", "0.0.0.0", "--port", "8000"])

def run_frontend():
    print("⚛️  Starting Frontend (React/Vite)...")
    frontend_dir = os.path.join(os.getcwd(), "frontend")
    
    # Check if node_modules exists
    if not os.path.exists(os.path.join(frontend_dir, "node_modules")):
        print("📦 Installing Frontend dependencies (npm install)...")
        # Use shell=True for Windows compatibility
        subprocess.run("npm install", cwd=frontend_dir, shell=True)
    
    # Start Vite Dev Server
    print("🚀 Launching UI...")
    subprocess.run("npm run dev", cwd=frontend_dir, shell=True)

if __name__ == "__main__":
    print("========================================")
    print("    CRAWLER: FULL STACK LAUNCHER")
    print("========================================")
    
    # 1. Install Python Deps if needed
    try:
        import fastapi
        import playwright
    except ImportError:
        install_python_deps()

    # 2. Start Backend in a separate thread
    backend_thread = threading.Thread(target=run_backend, daemon=True)
    backend_thread.start()

    # Wait a bit for backend to initialize
    time.sleep(3)

    # 3. Open Browser automatically
    webbrowser.open("http://localhost:5173")

    # 4. Run Frontend (This blocks the main thread until stopped)
    try:
        run_frontend()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")