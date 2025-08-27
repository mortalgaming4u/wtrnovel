import os

CHAPTER_DIR = "chapters"

def get_chapter_list():
    files = sorted(os.listdir(CHAPTER_DIR))
    return [f.replace(".md", "").replace("_", " ") for f in files]

def get_chapter_content(num):
    files = sorted(os.listdir(CHAPTER_DIR))
    path = os.path.join(CHAPTER_DIR, files[num - 1])
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    title = lines[0].strip("# \n")
    body = "".join(lines[1:])
    return {
        "title": title,
        "body": body,
        "prev": num - 1 if num > 1 else 1,
        "next": num + 1 if num < len(files) else num
    }