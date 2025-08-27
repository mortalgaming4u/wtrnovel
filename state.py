import json
import os

STATE_FILE = "resume.json"

def save_last_read(site, index):
    state = {}
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            state = json.load(f)
    state[site] = {"last_read": index}
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

def load_last_read(site):
    try:
        with open(STATE_FILE) as f:
            return json.load(f).get(site, {}).get("last_read", 0)
    except:
        return 0