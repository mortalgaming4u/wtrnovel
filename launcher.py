from parser_ixdzs import get_chapter_urls, extract_chapter
from writer import save_book

def main():
    toc_url = "https://ixdzs.tw/read/548591/"
    chapter_urls = get_chapter_urls(toc_url)
    book = []

    for url in chapter_urls:
        text = extract_chapter(url)
        book.append({"url": url, "text": text})

    save_book(book, "xiaoshidi.json")

if __name__ == "__main__":
    main()