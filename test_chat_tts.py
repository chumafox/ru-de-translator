import sys
import json
import urllib.request
import re
import asyncio

# Add project to path to import tts
sys.path.append("/Users/jenyanovak/Projects/active/ru-de-translator")
from ru_de_translator.tts import TTSEngine

prompt = "Как сказать на немецком - Как я могу доехать туда?"

print(f"Sending prompt to LM Studio: {prompt}")

try:
    proxy_handler = urllib.request.ProxyHandler({})
    opener = urllib.request.build_opener(proxy_handler)
    req = urllib.request.Request(
        "http://127.0.0.1:1234/v1/chat/completions",
        data=json.dumps(
            {
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a German tutor. Translate Russian to German. Wrap ALL German phrases in <de>...</de>. Do not use English.",
                    },
                    {"role": "user", "content": "Как сказать 'Я хочу спать'?"},
                    {
                        "role": "assistant",
                        "content": "На немецком это будет <de>Ich möchte schlafen</de> или <de>Ich bin müde</de>.",
                    },
                    {"role": "user", "content": prompt},
                ],
                "stream": False,
                "temperature": 0.7,
            }
        ).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )

    with opener.open(req, timeout=300) as response:
        result = json.loads(response.read().decode("utf-8"))
        reply = result.get("choices", [{}])[0].get("message", {}).get("content", "")

    reply = re.sub(r"<think>.*?</think>", "", reply, flags=re.DOTALL).strip()
    print("\n--- Model Reply ---")
    print(reply)
    print("-------------------\n")

    # Find <de> tags
    german_phrases = re.findall(r"<de>(.*?)</de>", reply, flags=re.DOTALL)

    if not german_phrases:
        print(
            "ERROR: No <de> tags found in the response! Injecting a test phrase to verify TTS."
        )
        german_phrases = ["Wie kann ich dahin kommen?"]

    print(f"Found {len(german_phrases)} German phrases:")

    # Initialize TTS
    engine = TTSEngine({"tts_provider": "edge_tts"})
    # Warmup
    print("Warming up TTS...")
    asyncio.run(engine.warmup())

    for i, phrase in enumerate(german_phrases, 1):
        print(f"[{i}] Pronouncing: {phrase}")
        hex_encoded = phrase.encode("utf-8").hex()
        # Decode just like the app does
        decoded_text = bytes.fromhex(hex_encoded).decode("utf-8")

        # Pronounce!
        asyncio.run(engine.speak(decoded_text))

    print("\nTest completed successfully!")

except Exception as e:
    print(f"Test failed: {e}")
