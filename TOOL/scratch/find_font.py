import requests

urls = [
    "https://raw.githubusercontent.com/googlefonts/bevietnam/master/fonts/ttf/BeVietnamPro-Regular.ttf",
    "https://raw.githubusercontent.com/google/fonts/main/ofl/bevietnampro/BeVietnamPro-Regular.ttf",
    "https://raw.githubusercontent.com/google/fonts/main/ofl/montserrat/static/Montserrat-Regular.ttf",
    "https://raw.githubusercontent.com/googlefonts/montserrat/master/fonts/ttf/Montserrat-Regular.ttf"
]

for url in urls:
    print(f"Trying {url}...")
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            if r.content.startswith(b"<!DOCTYPE") or r.content.startswith(b"\n\n"):
                print(f"  Failed: HTML content returned.")
            else:
                print(f"  Success! Size: {len(r.content)}")
                with open("fonts/BeVietnamPro-Regular.ttf", "wb") as f:
                    f.write(r.content)
                print(f"  Saved to fonts/BeVietnamPro-Regular.ttf")
                break
        else:
            print(f"  Failed: HTTP {r.status_code}")
    except Exception as e:
        print(f"  Error: {e}")
