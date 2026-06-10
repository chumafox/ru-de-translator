import urllib.request
import json
import os

os.environ["HTTP_PROXY"] = "http://127.0.0.1:8888"
os.environ["HTTPS_PROXY"] = "http://127.0.0.1:8888"
os.environ["ALL_PROXY"] = "socks5://127.0.0.1:1080"

proxy_handler = urllib.request.ProxyHandler({})
opener = urllib.request.build_opener(proxy_handler)
req = urllib.request.Request(
    "http://127.0.0.1:11434/api/generate",
    data=json.dumps({"model": "qwen2.5:3b", "prompt": "hi", "stream": False}).encode(
        "utf-8"
    ),
    headers={"Content-Type": "application/json"},
)
try:
    with opener.open(req, timeout=5) as response:
        result = json.loads(response.read().decode("utf-8"))
        print("Success:", result.get("response"))
except Exception as e:
    print("Error:", e)
