import os, time, requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

BASE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

def get_full_toc_url(book_url):
    r = requests.get(book_url, headers=BASE_HEADERS)
    r.encoding = 'utf-8'
    soup = BeautifulSoup(r.text, 'html.parser')
    toc_link = soup.find('a', string=lambda t: t and '完整章節' in t)
    return urljoin(book_url, toc_link['href'])

def parse_toc(toc_url):
    r = requests.get(toc_url, headers=BASE_HEADERS)
    r.encoding = 'utf-8'
    soup = BeautifulSoup(r.text, 'html.parser')
    links = []
    for a in soup.select('a'):
        if '/read/' in a.get('href', '') and a.text.strip():
            links.append(urljoin(toc_url, a['href']))
    return links

def fetch_and_clean(ch_url):
    r = requests.get(ch_url, headers=BASE_HEADERS)
    r.encoding = 'utf-8'
    soup = BeautifulSoup(r.text, 'html.parser')
    content_div = soup.find(id='content')
    if not content_div:
        return ''
    # Remove unwanted tags
    for tag in content_div(['script', 'style']):
        tag.decompose()
    return content_div.get_text('\n', strip=True)

def save_chapter(text, idx):
    os.makedirs('chapters', exist_ok=True)
    fname = f'chapters/ch{idx:03}.text'
    with open(fname, 'w', encoding='utf-8') as f:
        f.write(text)

def grab_book(book_url):
    toc_url = get_full_toc_url(book_url)
    chapter_links = parse_toc(toc_url)
    for i, link in enumerate(chapter_links, start=1):
        print(f'Fetching {i}/{len(chapter_links)}: {link}')
        text = fetch_and_clean(link)
        save_chapter(text, i)
        time.sleep(1.5)  # be polite

if __name__ == '__main__':
    grab_book("https://ixdzs.tw/read/576246/")
