import json
import urllib.request
import re
from rich.markup import escape

try:
    proxy_handler = urllib.request.ProxyHandler({})
    opener = urllib.request.build_opener(proxy_handler)
    req = urllib.request.Request(
        "http://127.0.0.1:11434/api/generate",
        data=json.dumps(
            {
                "model": "german-tutor",
                "prompt": "Ich bin ein gutes Buch gelesen. Проверь мою грамматику.",
                "stream": False,
            }
        ).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with opener.open(req, timeout=60) as response:
        result = json.loads(response.read().decode("utf-8"))
        reply = result.get("response", "")

        escaped_text = escape(reply)

        def replace_match(match):
            inner_text = match.group(1)
            safe_text = inner_text.replace("'", "\\'").replace("\n", " ")
            return f'[@click="speak_text(\'{safe_text}\')"][underline bright_yellow]"{inner_text}"[/][/]'

        processed_text = re.sub(r'"([^"]+)"', replace_match, escaped_text)
        print("PROCESSED TEXT:\n", processed_text)

        # Test if it renders correctly in Rich
        from rich.markup import render

        render(f"[cyan]Qwen:[/cyan] {processed_text}")
        print("RENDER SUCCESSFUL")

except Exception as e:
    print(f"Error: {e}")
