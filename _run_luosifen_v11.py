"""v1.1 修正版螺蛳粉封面 - 带3次重试"""
import os, sys, json, time, requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

API_KEY = os.getenv("AGNES_API_KEY", "")
URL = "https://apihub.agnes-ai.com/v1/images/generations"
OUT = Path(__file__).parent / "outputs" / "food_image_test" / "cover_luosifen.png"
OUT.parent.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(Path(__file__).parent))
from _generate_food_images import IMAGES
prompt = ""
for img in IMAGES:
    if img['filename'] == 'cover_luosifen.png':
        prompt = img['prompt']
        break

print(f"Prompt: {len(prompt)} chars")

for attempt in range(1, 5):
    print(f"--- attempt {attempt}/4 ---")
    start = time.time()
    try:
        r = requests.post(URL,
            headers={"Content-Type":"application/json","Authorization":f"Bearer {API_KEY}"},
            json={"model":"agnes-image-2.0-flash","prompt":prompt,"size":"1024x1792","n":1},
            timeout=600)
        elapsed = time.time() - start
        print(f"Status: {r.status_code} ({elapsed:.1f}s)")
        if r.status_code == 200:
            data = r.json()
            url = data.get("data",[{}])[0].get("url") or data.get("url")
            if url:
                ir = requests.get(url, timeout=120)
                OUT.write_bytes(ir.content)
                print(f"OK! {OUT.stat().st_size/1024:.1f} KB")
                sys.exit(0)
        else:
            print(f"err: {r.text[:200]}")
            if attempt < 4:
                wait = 5 * attempt
                print(f"waiting {wait}s...")
                time.sleep(wait)
    except Exception as e:
        print(f"EXC: {e}")
        if attempt < 4:
            time.sleep(5)

print("all retries failed")
sys.exit(1)
