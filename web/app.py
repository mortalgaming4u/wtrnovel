from flask import Flask
from web.routes import register_routes  # Use full module path

app = Flask(__name__)
register_routes(app)