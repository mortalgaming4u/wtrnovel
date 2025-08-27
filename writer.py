def save_markdown(chapters, filename):
    with open(filename, "w", encoding="utf-8") as f:
        for i, ch in enumerate(chapters, 1):
            f.write(f"# Chapter {i}\n\n{ch['text']}\n\n")