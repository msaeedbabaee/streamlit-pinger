import requests

def ping_urls():
    with open("urls.txt", "r") as file:
        urls = [line.strip() for line in file if line.strip()]
    
    print(f"Total apps to ping: {len(urls)}")
    
    for url in urls:
        try:
            response = requests.get(url, timeout=15)
            print(f"[SUCCESS] Pinged: {url} | Status: {response.status_code}")
        except Exception as e:
            print(f"[FAILED] Could not ping {url}: {e}")

if __name__ == "__main__":
    ping_urls()
