import requests
import time

def safe_request(url, retries=3, delay=2):
    for _ in range(retries):
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return response
        except Exception:
            time.sleep(delay)
    return None