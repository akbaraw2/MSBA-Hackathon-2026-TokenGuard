import requests
import json

# Your local server URL
URL = "http://127.0.0.1:8000/v1/chat/completions"

# A highly bloated prompt full of "fluff" that Gemini should compress
payload = {
    "model": "gpt-4o",
    "messages": [
        {
            "role": "user",
            "content": "Oh my goodness, hello there! I was wondering if you could possibly be so kind as to tell me what the capital city of France is? I would appreciate it so very much, thank you!"
        }
    ]
}

print("Sending request to TokenGuard proxy...")

# Send a raw HTTP POST request to bypass SDK filtering
response = requests.post(URL, json=payload)
data = response.json()

if "tokenguard_stats" in data:
    print("\n✅ SUCCESS! TokenGuard Intercepted the Request.")
    print("\n--- ACTUAL AI ANSWER ---")
    print(data["choices"][0]["message"]["content"])
    
    print("\n--- TOKENGUARD STATS ---")
    stats = data["tokenguard_stats"]
    print(f"Original Prompt: '{stats['original_prompt']}'")
    print(f"Compressed Prompt: '{stats['compressed_prompt']}'")
    print(f"Original Cost: {stats['original_cost_estimate']}")
    print(f"Actual Cost: {stats['actual_cost']}")
    print(f"Money Saved: {stats['money_saved']}")
    print(f"Session Total: {stats['session_total']}")
else:
    print("\n❌ Error or Kill Switch Triggered:")
    print(json.dumps(data, indent=2))