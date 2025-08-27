import json

def save_book(chapters, filename):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(chapters, f, ensure_ascii=False, indent=2)