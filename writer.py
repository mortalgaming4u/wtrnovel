import os

# Detect base directory dynamically
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Use absolute path to avoid deployment issues
CHAPTER_DIR = os.path.join(BASE_DIR, "..", "chapters")

def get_chapter_list():
    if not os.path.exists(CHAPTER_DIR):
        return ["[No chapters found]"]
    files = sorted(f for f in os.listdir(CHAPTER_DIR) if f.endswith(".md"))
    return [f.replace(".md", "").replace("_", " ") for f in files]

def get_chapter_content(num):
    files = sorted(f for f in os.listdir(CHAPTER_DIR) if f.endswith(".md"))
    if not files or num < 1 or num > len(files):
        return {
            "title": "[Invalid chapter]",
            "body": "Chapter not found.",
            "prev": max(num - 1, 1),
            "next": min(num + 1, len(files))
        }
    path = os.path.join(CHAPTER_DIR, files[num - 1])
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    title = lines[0].strip("# \n") if lines else "[Untitled]"
    body = "".join(lines[1:]) if len(lines) > 1 else "[No content]"
    return {
        "title": title,
        "body": body,
        "prev": num - 1 if num > 1 else 1,
        "next": num + 1 if num < len(files) else num
    }