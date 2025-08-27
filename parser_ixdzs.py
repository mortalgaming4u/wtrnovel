from bs4 import BeautifulSoup
from utils import safe_request

def get_chapter_urls(toc_url):
    r = safe_request(toc_url)
    if not r:
        print(f"[WARN] Failed to fetch TOC: {toc_url}")
        return []

    soup = BeautifulSoup(r.text, "html.parser")
    return [
        "https://ixdzs.tw" + a['href']
        for a in soup.select('a[href^="/read/548591/"]')
        if a['href'].count('/') == 3
    ]

def extract_chapter(url):
    r = safe_request(url)
    if not r:
        print(f"[WARN] Failed to fetch chapter: {url}")
        return ""

    soup = BeautifulSoup(r.text, "html.parser")
    content = soup.select_one(".chapter-content")
    return content.get_text(strip=True) if content else ""