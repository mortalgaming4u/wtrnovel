import os
import sys
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs
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
DELAY_BETWEEN_REQUESTS = 2.0  # seconds


def extract_book_id(book_url):
    """Extract book ID from the URL."""
    # Pattern: https://ixdzs.tw/read/576246/
    match = re.search(r'/read/(\d+)/?', book_url)
    if match:
        return match.group(1)
    return None


def find_chapter_list_page(book_url):
    """Try to find the chapter list page for the book."""
    try:
        print(f"[DEBUG] Analyzing book page: {book_url}")
        r = requests.get(book_url, headers=BASE_HEADERS, timeout=REQUEST_TIMEOUT)
        r.encoding = 'utf-8'
        soup = BeautifulSoup(r.text, 'html.parser')
        
        print(f"[DEBUG] Page title: {soup.title.string if soup.title else 'No title'}")
        
        # Method 1: Look for direct chapter list link
        chapter_list_patterns = [
            lambda s: s.find('a', string=lambda t: t and any(x in t for x in ['目录', '目錄', '章节', '章節', '完整章节', '完整章節'])),
            lambda s: s.find('a', href=lambda h: h and any(x in h.lower() for x in ['list', 'catalog', 'chapter', 'mulu'])),
            lambda s: s.find('a', class_=lambda c: c and any(x in c.lower() for x in ['list', 'catalog', 'chapter', 'mulu'])),
        ]
        
        for pattern in chapter_list_patterns:
            link = pattern(soup)
            if link and link.get('href'):
                chapter_url = urljoin(book_url, link['href'])
                print(f"[INFO] Found chapter list link: {chapter_url}")
                return chapter_url
        
        # Method 2: Check if current page already has chapters
        chapter_links = soup.find_all('a', href=True)
        chapter_count = 0
        for link in chapter_links:
            href = link.get('href', '')
            text = link.get_text().strip()
            if is_chapter_link(href, text):
                chapter_count += 1
        
        if chapter_count >= 5:  # If we found several chapter links
            print(f"[INFO] Current page has {chapter_count} chapter links, using as chapter list")
            return book_url
        
        # Method 3: Try constructing common chapter list URLs
        book_id = extract_book_id(book_url)
        if book_id:
            possible_urls = [
                f"https://ixdzs.tw/read/{book_id}/list/",
                f"https://ixdzs.tw/read/{book_id}/catalog/",
                f"https://ixdzs.tw/read/{book_id}/mulu/",
                f"https://ixdzs.tw/book/{book_id}/",
                f"https://ixdzs.tw/list/{book_id}/",
            ]
            
            for url in possible_urls:
                try:
                    print(f"[DEBUG] Trying constructed URL: {url}")
                    test_r = requests.get(url, headers=BASE_HEADERS, timeout=REQUEST_TIMEOUT)
                    if test_r.status_code == 200:
                        test_soup = BeautifulSoup(test_r.text, 'html.parser')
                        test_links = test_soup.find_all('a', href=True)
                        test_count = sum(1 for link in test_links if is_chapter_link(link.get('href', ''), link.get_text().strip()))
                        if test_count >= 5:
                            print(f"[INFO] Found working chapter list URL: {url} ({test_count} chapters)")
                            return url
                except:
                    continue
        
        # Method 4: Try to find the first chapter and work backwards
        first_chapter_patterns = [
            lambda s: s.find('a', string=lambda t: t and any(x in t for x in ['第一章', '第1章', 'Chapter 1', 'Ch.1'])),
            lambda s: s.find('a', href=lambda h: h and '/p1.html' in h),
            lambda s: s.find('a', href=lambda h: h and '/1/' in h),
        ]
        
        for pattern in first_chapter_patterns:
            link = pattern(soup)
            if link and link.get('href'):
                first_chapter_url = urljoin(book_url, link['href'])
                print(f"[INFO] Found first chapter, will try to extract chapter list from: {first_chapter_url}")
                return first_chapter_url
        
        print("[ERROR] Could not find chapter list page")
        return None
        
    except Exception as e:
        print(f"[ERROR] Failed to find chapter list: {e}")
        return None


def is_chapter_link(href, text):
    """Determine if a link is likely a chapter link."""
    if not href or not text:
        return False
    
    # URL patterns
    url_patterns = [
        r'/p\d+\.html',  # /p1.html, /p2.html, etc.
        r'/\d+\.html',   # /1.html, /2.html, etc.
        r'/\d+/$',       # /1/, /2/, etc.
        r'chapter.*\d+', # chapter1, chapter-1, etc.
    ]
    
    for pattern in url_patterns:
        if re.search(pattern, href, re.I):
            return True
    
    # Text patterns
    text_patterns = [
        r'第\s*\d+\s*章',      # 第1章, 第 1 章, etc.
        r'Chapter\s*\d+',       # Chapter 1, Chapter1, etc.
        r'Ch\.\s*\d+',          # Ch.1, Ch. 1, etc.
        r'^\s*\d+\s*$',         # Just a number
        r'^\s*\d+\.',           # 1., 2., etc.
    ]
    
    for pattern in text_patterns:
        if re.search(pattern, text, re.I):
            return True
    
    return False


def parse_toc(toc_url):
    """Parse the table of contents and collect chapter URLs."""
    links = []
    visited = set()
    page_count = 0
    max_pages = 100
    
    current_url = toc_url
    
    while current_url and page_count < max_pages:
        page_count += 1
        print(f"[INFO] Parsing page {page_count}: {current_url}")
        
        try:
            r = requests.get(current_url, headers=BASE_HEADERS, timeout=REQUEST_TIMEOUT)
            r.encoding = 'utf-8'
            soup = BeautifulSoup(r.text, 'html.parser')
            
            # Find all potential chapter links
            all_links = soup.find_all('a', href=True)
            found_chapters = 0
            
            for a in all_links:
                href = a['href']
                text = a.get_text().strip()
                
                if is_chapter_link(href, text):
                    full_link = urljoin(current_url, href)
                    if full_link not in visited:
                        visited.add(full_link)
                        links.append((full_link, text))
                        found_chapters += 1
                        print(f"  Found: {text[:50]}... -> {full_link}")
            
            print(f"[INFO] Found {found_chapters} new chapters on this page")
            
            # Look for next page
            next_link = None
            next_patterns = [
                lambda s: s.find('a', string=lambda t: t and any(x in t for x in ['下一页', '下一頁', 'Next', 'next', '>', '>>'])),
                lambda s: s.find('a', class_=lambda c: c and 'next' in c.lower()),
                lambda s: s.find('a', href=lambda h: h and 'page=' in h.lower()),
            ]
            
            for pattern in next_patterns:
                next_link = pattern(soup)
                if next_link:
                    break
            
            if next_link and next_link.get('href'):
                current_url = urljoin(current_url, next_link['href'])
                print(f"[INFO] Found next page: {current_url}")
            else:
                print("[INFO] No more pages found")
                break
                
        except Exception as e:
            print(f"[ERROR] Failed to parse page {page_count}: {e}")
            break
    
    # Sort chapters by their likely order
    def extract_chapter_number(text):
        # Try to extract chapter number for sorting
        patterns = [
            r'第\s*(\d+)\s*章',
            r'Chapter\s*(\d+)',
            r'Ch\.\s*(\d+)',
            r'^(\d+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.I)
            if match:
                return int(match.group(1))
        return 999999  # Put unmatched items at the end
    
    # Sort by chapter number
    links.sort(key=lambda x: extract_chapter_number(x[1]))
    
    print(f"[INFO] Total chapters found: {len(links)}")
    return [link[0] for link in links]  # Return just URLs


def fetch_and_clean(ch_url):
    """Fetch a chapter page and return cleaned text."""
    for attempt in range(1, RETRY_LIMIT + 1):
        try:
            print(f"[DEBUG] Fetching chapter (attempt {attempt}): {ch_url}")
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
                soup.find('div', class_='read-content'),
                soup.find('article'),
                soup.find('main'),
            ]
            
            content_div = None
            for container in content_containers:
                if container and container.get_text().strip():
                    content_div = container
                    break
            
            if not content_div:
                print(f"[WARN] No content container found at {ch_url}")
                # Try to get any meaningful text from the page
                body = soup.find('body')
                if body:
                    content_div = body
                else:
                    return ''

            # Remove unwanted elements
            for tag in content_div(['script', 'style', 'nav', 'header', 'footer', 'aside']):
                tag.decompose()
            
            # Remove ads and navigation
            for element in content_div.find_all(['div', 'span', 'p', 'a']):
                text = element.get_text().strip().lower()
                classes = ' '.join(element.get('class', []))
                if any(keyword in text + classes.lower() for keyword in [
                    'ixdzs', '广告', '廣告', '推荐', '推薦', 'ads', 'advertisement', 
                    'next', 'prev', 'previous', '上一章', '下一章', '目录', '目錄'
                ]):
                    element.decompose()

            text = content_div.get_text('\n', strip=True)
            
            # Clean up the text
            clean_lines = []
            for line in text.splitlines():
                line = line.strip()
                if line and len(line) > 1 and not any(keyword in line.lower() for keyword in [
                    'ixdzs', '广告', '廣告', '推荐', '推薦', 'copyright', '版权'
                ]):
                    clean_lines.append(line)
            
            result = '\n'.join(clean_lines)
            
            if len(result) < 100:  # Very short content, might be an error page
                print(f"[WARN] Chapter content seems too short ({len(result)} chars)")
                if attempt < RETRY_LIMIT:
                    continue
            
            return result

        except Exception as e:
            print(f"[ERROR] Attempt {attempt}: {e} while fetching {ch_url}")
            if attempt < RETRY_LIMIT:
                time.sleep(3)

    print(f"[FAIL] Could not fetch {ch_url} after {RETRY_LIMIT} attempts.")
    return ''


def save_chapter(text, idx, title=""):
    """Save chapter text to sequential .txt file in chapters/ folder."""
    if not text.strip():
        print(f"[WARN] Skipping empty chapter {idx}")
        return False
    
    os.makedirs('chapters', exist_ok=True)
    
    # Create filename with title if available
    if title:
        # Clean title for filename
        clean_title = re.sub(r'[^\w\s-]', '', title)[:50]
        fname = f'chapters/ch{idx:03}_{clean_title}.txt'
    else:
        fname = f'chapters/ch{idx:03}.txt'
    
    try:
        with open(fname, 'w', encoding='utf-8') as f:
            f.write(text)
        print(f"[INFO] Saved chapter {idx} ({len(text)} characters) -> {fname}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to save chapter {idx}: {e}")
        return False


def debug_chapter_dir():
    """List saved chapters for validation."""
    if not os.path.exists('chapters'):
        print("\n[DEBUG] No chapters directory found.")
        return
    
    chapters = [f for f in os.listdir('chapters') if f.endswith('.txt')]
    if not chapters:
        print("\n[DEBUG] No chapter files found.")
        return
        
    total_size = sum(os.path.getsize(os.path.join('chapters', f)) for f in chapters)
    print(f"\n[DEBUG] Successfully saved {len(chapters)} chapters ({total_size:,} bytes total):")
    
    for fname in sorted(chapters)[:10]:  # Show first 10
        file_path = os.path.join('chapters', fname)
        file_size = os.path.getsize(file_path)
        print(f" - {fname} ({file_size:,} bytes)")
    
    if len(chapters) > 10:
        print(f" ... and {len(chapters) - 10} more chapters")


def grab_book(book_url):
    """Main routine to grab the entire book."""
    print(f"[INFO] Starting book download from: {book_url}")
    
    # Ensure URL is properly formatted
    if not book_url.startswith('http'):
        book_url = 'https://' + book_url
    
    # Step 1: Find the chapter list page
    toc_url = find_chapter_list_page(book_url)
    if not toc_url:
        print("[FATAL] Could not find chapter list page. Exiting.")
        return

    # Step 2: Parse the chapter list
    chapter_links = parse_toc(toc_url)
    if not chapter_links:
        print("[FATAL] No chapters found. Exiting.")
        return

    print(f"[INFO] Found {len(chapter_links)} chapters to download")
    
    # Step 3: Download chapters
    success_count = 0
    for i, link in enumerate(chapter_links, start=1):
        print(f"\n[{i}/{len(chapter_links)}] Processing: {link}")
        text = fetch_and_clean(link)
        if text and save_chapter(text, i):
            success_count += 1
        
        # Be respectful to the server
        time.sleep(DELAY_BETWEEN_REQUESTS)

    print(f"\n✅ Download completed: {success_count}/{len(chapter_links)} chapters saved successfully")
    debug_chapter_dir()


if __name__ == '__main__':
    try:
        if len(sys.argv) < 2:
            print("Usage: python grab_ixdzs.py <book_url>")
            print("Example: python grab_ixdzs.py https://ixdzs.tw/read/576246/")
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
