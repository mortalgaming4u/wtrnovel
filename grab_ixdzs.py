import os
import sys
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

BASE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}
REQUEST_TIMEOUT = 15
RETRY_LIMIT = 3
DELAY_BETWEEN_REQUESTS = 1.5  # seconds


def get_full_toc_url(book_url):
    """Try to find the full TOC link, or fallback to main page."""
    try:
        r = requests.get(book_url, headers=BASE_HEADERS, timeout=REQUEST_TIMEOUT)
        r.encoding = 'utf-8'
        soup = BeautifulSoup(r.text, 'html.parser')

        toc_link = soup.find('a', string=lambda t: t and '完整章節' in t)
        if toc_link:
            resolved = urljoin(book_url, toc_link['href'])
            print(f"[INFO] Found TOC link: {resolved}")
            return resolved

        if soup.find('div', class_='chapter-list'):
            print("[INFO] No TOC link found, using main page as TOC.")
            return book_url

        print("[ERROR] TOC not found on page.")
        return None

    except Exception as e:
        print(f"[ERROR] Failed to get TOC URL: {e}")
        return None


def parse_toc(toc_url):
    """Iterate through all TOC pages and collect unique chapter URLs in order."""
    links = []
    visited = set()

    while toc_url:
        print(f"Parsing TOC page: {toc_url}")
        try:
            r = requests.get(toc_url, headers=BASE_HEADERS, timeout=REQUEST_TIMEOUT)
            r.encoding = 'utf-8'
            soup = BeautifulSoup(r.text, 'html.parser')

            toc_container = soup.find('div', class_='chapter-list') or soup
            for a in toc_container.find_all('a', href=True):
                href = a['href']
                if '/read/' in href and a.text.strip():
                    full_link = urljoin(toc_url, href)
                    if full_link not in visited:
                        visited.add(full_link)
                        links.append(full_link)

            next_link = soup.find('a', string=lambda t: t and '下一頁' in t)
            toc_url = urljoin(toc_url, next_link['href']) if next_link else None

        except Exception as e:
            print(f"[ERROR] Failed to parse TOC page: {e}")
            break

    return links


def fetch_and_clean(ch_url):
    """Fetch a chapter page and return cleaned text."""
    for attempt in range(1, RETRY_LIMIT + 1):
        try:
            r = requests.get(ch_url, headers=BASE_HEADERS, timeout=REQUEST_TIMEOUT)
            r.encoding = 'utf-8'
            soup = BeautifulSoup(r.text, 'html.parser')
            content_div = soup.find(id='content')
            if not content_div:
                print(f"[WARN] No content found at {ch_url}")
                return ''

            for tag in content_div(['script', 'style']):
                tag.decompose()

            text = content_div.get_text('\n', strip=True)
            clean_lines = [
                line for line in text.splitlines()
                if 'ixdzs' not in line.lower() and line.strip()
            ]
            return '\n'.join(clean_lines)

        except Exception as e:
            print(f"[ERROR] Attempt {attempt}: {e} while fetching {ch_url}")
            time.sleep(2)

    print(f"[FAIL] Could not fetch {ch_url} after {RETRY_LIMIT} attempts.")
    return ''


def save_chapter(text, idx):
    """Save chapter text to sequential .text file in chapters/ folder."""
    if not text.strip():
        print(f"[WARN] Skipping empty chapter {idx}")
        return
    os.makedirs('chapters', exist_ok=True)
    fname = f'chapters/ch{idx:03}.text'
    with open(fname, 'w', encoding='utf-8') as f:
        f.write(text)


def debug_chapter_dir():
    """List saved chapters for validation."""
    print("\n[DEBUG] Listing saved chapters:")
    for fname in sorted(os.listdir('chapters')):
        print(f" - {fname}")


def grab_book(book_url):
    """Main routine to grab the entire book."""
    print(f"Getting full TOC from {book_url}")
    toc_url = get_full_toc_url(book_url)
    if not toc_url:
        print("[FATAL] Could not resolve TOC URL. Exiting.")
        return

    chapter_links = parse_toc(toc_url)
    print(f"[INFO] Parsed {len(chapter_links)} chapter links.")

    if not chapter_links:
        print("[FATAL] No chapters found. Exiting.")
        return

    success_count = 0
    for i, link in enumerate(chapter_links, start=1):
        print(f"[{i}/{len(chapter_links)}] Fetching: {link}")
        text = fetch_and_clean(link)
        if text:
            save_chapter(text, i)
            success_count += 1
        time.sleep(DELAY_BETWEEN_REQUESTS)

    print(f"\n✅ Completed: {success_count}/{len(chapter_links)} chapters saved.")
    debug_chapter_dir()


if __name__ == '__main__':
    try:
        if len(sys.argv) < 2:
            print("Usage: python grab_ixdzs.py <book_url>")
            sys.exit(0)
        grab_book(sys.argv[1])
    except Exception
