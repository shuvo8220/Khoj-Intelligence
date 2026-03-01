import os
import hashlib
import re

class FileManager:
    """Handles file operations and formatting cleanly."""
    
    @staticmethod
    def ensure_directories(paths):
        for path in paths:
            os.makedirs(path, exist_ok=True)

    @staticmethod
    def get_safe_filename(url, title):
        url_hash = hashlib.md5(url.encode()).hexdigest()[:6]
        safe_title = re.sub(r'[^\w\-]', '_', title)[:40] or "page"
        return f"{safe_title}_{url_hash}.md"

    @staticmethod
    def save_markdown(folder, filename, title, url, date, summary, content):
        """Generates the Markdown format and saves the file."""
        filepath = os.path.join(folder, filename)
        
        # Clean Template Logic Moved Here
        template = f"""# {title}

> ** Source:** [{url}]({url})
> ** Date:** {date}

---

##  AI Summary
{summary}

---

##  Full Content
{content}
"""
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(template)
        
        return filename