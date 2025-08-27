import requests
import time

def safe_request(url, retries=3, delay=2):
    for attempt in range(retries):
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return response
            else:
                print(f"[WARN] Status {response.status_code} on attempt {attempt+1}")
        except Exception as e:
            print(f"[ERROR] {e} on attempt {attempt+1}")
        time.sleep(delay)
    return None