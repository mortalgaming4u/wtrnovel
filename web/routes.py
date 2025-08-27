from flask import render_template
from writer import get_chapter_list, get_chapter_content

def register_routes(app):
    @app.route("/")
    def home():
        chapters = get_chapter_list()
        return render_template("toc.html", chapters=chapters)

    @app.route("/chapter/<int:num>")
    def chapter(num):
        content = get_chapter_content(num)
        return render_template("chapter.html", content=content)