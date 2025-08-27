import requests
from bs4 import BeautifulSoup

def get_chapter_urls(toc_url):
    r = requests.get(toc_url)
    soup = BeautifulSoup(r.text, "html.parser")
    return [
        "https://ixdzs.tw" + a['href']
        for a in soup.select('a[href^="/read/548591/"]')
        if a['href'].count('/') == 3
    ]

def extract_chapter(url):
    r = requests.get(url)
    soup = BeautifulSoup(r.text, "html.parser")
    content = soup.select_one(".chapter-content")
    return content.get_text(strip=True) if content else ""