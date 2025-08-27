from tqdm import tqdm
from parser_ixdzs import get_chapter_urls, extract_chapter
from writer import save_book, save_markdown

def main():
    toc_url = "https://ixdzs.tw/read/548591/"
    chapter_urls = get_chapter_urls(toc_url)
    book = []

    for url in tqdm(chapter_urls, desc="Extracting chapters"):
        text = extract_chapter(url)
        book.append({"url": url, "text": text})

    save_book(book, "xiaoshidi.json")
    save_markdown(book, "xiaoshidi.md")  # Optional Markdown output