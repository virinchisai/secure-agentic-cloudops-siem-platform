"""Seed sample events (placeholder).

Next step: we'll publish events to Redpanda and verify an end-to-end alert flow.
"""

import time
import requests

def main():
    # For now, just verify services are reachable
    for url in ["http://127.0.0.1:8001/health", "http://127.0.0.1:8002/health"]:
        try:
            r = requests.get(url, timeout=3)
            print(url, r.status_code, r.json())
        except Exception as e:
            print(url, "ERROR", e)

    print("Seed complete (placeholder).")

if __name__ == "__main__":
    main()
