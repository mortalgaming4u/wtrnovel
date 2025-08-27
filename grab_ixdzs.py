import os
import sys
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re

BASE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}
REQUEST_TIMEOUT = 15
RETRY_LIMIT = 3
DELAY_BETWEEN_REQUESTS = 1.5  # seconds


def get_full_toc_url(book_url):
    """Try to find the full TOC link, or fallback to main page."""
    try:
        print(f"[DEBUG] Fetching main page: {book_url}")
        r = requests.get(book_url, headers=BASE_HEADERS, timeout=REQUEST_TIMEOUT)
        r.encoding = 'utf-8'
        soup = BeautifulSoup(r.text, 'html.parser')
        
        print(f"[DEBUG] Page title: {soup.title.string if soup.title else 'No title'}")
        
        # Try multiple patterns for TOC links
        toc_patterns = [
            lambda s: s.find('a', string=lambda t: t and '完整章節' in t),
            lambda s: s.find('a', string=lambda t: t and '章節目錄' in t),
            lambda s: s.find('a', string=lambda t: t and '目錄' in t),
            lambda s: s.find('a', href=lambda h: h and 'chapter' in h.lower()),
            lambda s: s.find('a', href=lambda h: h and 'list' in h.lower()),
        ]
        
        for pattern in toc_patterns:
            toc_link = pattern(soup)
            if toc_link and toc_link.get('href'):
                resolved = urljoin(book_url, toc_link['href'])
                print(f"[INFO] Found TOC link: {resolved}")
                return resolved
        
        # Look for common TOC container patterns
        toc_containers = [
            soup.find('div', class_='chapter-list'),
            soup.find('div', class_='catalog'),
            soup.find('div', class_='mulu'),
            soup.find('div', id='list'),
            soup.find('ul', class_='chapter'),
            soup.find('div', class_='book-list'),
        ]
        
        for container in toc_containers:
            if container:
                print("[INFO] Found chapter list container on main page.")
                return book_url
        
        # Look for any links that might be chapters
        chapter_links = soup.find_all('a', href=True)
        chapter_count = 0
        for link in chapter_links:
            href = link.get('href', '')
            text = link.get_text().strip()
            if (('/read/' in href or '/chapter/' in href) and 
                (re.search(r'第.*章', text) or re.search(r'Chapter', text, re.I) or
                 re.search(r'\d+', text))):
                chapter_count += 1
        
        if chapter_count > 0:
            print(f"[INFO] Found {chapter_count} potential chapter links on main page.")
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
    page_count = 0
    max_pages = 50  # Safety limit

    while toc_url and page_count < max_pages:
        page_count += 1
        print(f"Parsing TOC page {page_count}: {toc_url}")
        try:
            r = requests.get(toc_url, headers=BASE_HEADERS, timeout=REQUEST_TIMEOUT)
            r.encoding = 'utf-8'
            soup = BeautifulSoup(r.text, 'html.parser')

            # Try multiple container patterns
            containers = [
                soup.find('div', class_='chapter-list'),
                soup.find('div', class_='catalog'),
                soup.find('div', class_='mulu'),
                soup.find('div', id='list'),
                soup.find('ul', class_='chapter'),
                soup.find('div', class_='book-list'),
                soup  # fallback to entire page
            ]
            
            toc_container = None
            for container in containers:
                if container:
                    toc_container = container
                    break
            
            if not toc_container:
                toc_container = soup
            
            # Look for chapter links with various patterns
            for a in toc_container.find_all('a', href=True):
                href = a['href']
                text = a.get_text().strip()
                
                # Check if this looks like a chapter link
                is_chapter = any([
                    '/read/' in href,
                    '/chapter/' in href,
                    re.search(r'第.*章', text),
                    re.search(r'Chapter', text, re.I),
                    (re.search(r'\d+', text) and len(text) < 100)  # Short text with numbers
                ])
                
                if is_chapter and text:
                    full_link = urljoin(toc_url, href)
                    if full_link not in visited:
                        visited.add(full_link)
                        links.append(full_link)
                        print(f"  Found chapter: {text[:50]}...")

            # Look for next page
            next_patterns = [
                lambda s: s.find('a', string=lambda t: t and '下一頁' in t),
                lambda s: s.find('a', string=lambda t: t and 'next' in t.lower()),
                lambda s: s.find('a', string=lambda t: t and '>' in t),
                lambda s: s.find('a', class_='next'),
            ]
            
            next_link = None
            for pattern in next_patterns:
                next_link = pattern(soup)
                if next_link:
                    break
            
            toc_url = urljoin(toc_url, next_link['href']) if next_link else None

        except Exception as e:
            print(f"[ERROR] Failed to parse TOC page: {e}")
            break

    print(f"[INFO] Found {len(links)} total chapter links across {page_count} pages")
    return links


def fetch_and_clean(ch_url):
    """Fetch a chapter page and return cleaned text."""
    for attempt in range(1, RETRY_LIMIT + 1):
        try:
            r = requests.get(ch_url, headers=BASE_HEADERS, timeout=REQUEST_TIMEOUT)
            r.encoding = 'utf-8'
            soup = BeautifulSoup(r.text, 'html.parser')
            
            # Try multiple content container patterns
            content_containers = [
                soup.find(id='content'),
                soup.find('div', class_='content'),
                soup.find('div', class_='chapter-content'),
                soup.find('div', class_='text'),
                soup.find('div', class_='novel-content'),
                soup.find('div', class_='book-content'),
                soup.find('article'),
                soup.find('main'),
            ]
            
            content_div = None
            for container in content_containers:
                if container:
                    content_div = container
                    break
            
            if not content_div:
                print(f"[WARN] No content container found at {ch_url}")
                return ''

            # Remove unwanted elements
            for tag in content_div(['script', 'style', 'nav', 'header', 'footer', 'aside']):
                tag.decompose()
            
            # Remove ads and unwanted content
            for element in content_div.find_all(['div', 'span', 'p']):
                text = element.get_text().strip().lower()
                if any(keyword in text for keyword in ['ixdzs', '廣告', '推薦', 'ads', 'advertisement']):
                    element.decompose()

            text = content_div.get_text('\n', strip=True)
            
            # Clean up the text
            clean_lines = []
            for line in text.splitlines():
                line = line.strip()
                if line and not any(keyword in line.lower() for keyword in ['ixdzs', '廣告', '推薦']):
                    clean_lines.append(line)
            
            return '\n'.join(clean_lines)

        except Exception as e:
            print(f"[ERROR] Attempt {attempt}: {e} while fetching {ch_url}")
            if attempt < RETRY_LIMIT:
                time.sleep(2)

    print(f"[FAIL] Could not fetch {ch_url} after {RETRY_LIMIT} attempts.")
    return ''


def save_chapter(text, idx):
    """Save chapter text to sequential .txt file in chapters/ folder."""
    if not text.strip():
        print(f"[WARN] Skipping empty chapter {idx}")
        return
    os.makedirs('chapters', exist_ok=True)
    fname = f'chapters/ch{idx:03}.txt'
    with open(fname, 'w', encoding='utf-8') as f:
        f.write(text)
    print(f"[INFO] Saved chapter {idx} ({len(text)} characters)")


def debug_chapter_dir():
    """List saved chapters for validation."""
    if not os.path.exists('chapters'):
        print("\n[DEBUG] No chapters directory found.")
        return
    
    chapters = [f for f in os.listdir('chapters') if f.endswith('.txt')]
    if not chapters:
        print("\n[DEBUG] No chapter files found.")
        return
        
    print(f"\n[DEBUG] Listing {len(chapters)} saved chapters:")
    for fname in sorted(chapters):
        file_path = os.path.join('chapters', fname)
        file_size = os.path.getsize(file_path)
        print(f" - {fname} ({file_size} bytes)")


def grab_book(book_url):
    """Main routine to grab the entire book."""
    print(f"[DEBUG] Starting grab_book with URL: {book_url}")
    
    # Ensure URL is properly formatted
    if not book_url.startswith('http'):
        book_url = 'https://' + book_url
    
    toc_url = get_full_toc_url(book_url)
    print(f"[DEBUG] TOC URL resolved: {toc_url}")
    if not toc_url:
        print("[FATAL] Could not resolve TOC URL. Exiting.")
        return

    chapter_links = parse_toc(toc_url)
    print(f"[DEBUG] Parsed {len(chapter_links)} chapter links.")

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
            sys.exit(1)
        grab_book(sys.argv[1])
    except KeyboardInterrupt:
        print("\n[INFO] Script interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"[FATAL] Script crashed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
