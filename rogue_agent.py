import os
import time
import requests
from openai import OpenAI, RateLimitError
from dotenv import load_dotenv

# Load API key from your .env file
load_dotenv()

SESSION_ID = "demo-session-01"
TOKENGUARD_URL = "http://127.0.0.1:8000"
BUDGET_LIMIT = 0.50 # Just for the print statement

# Reset session so cost starts from zero
requests.post(f"{TOKENGUARD_URL}/reset/{SESSION_ID}")   
print(f"Session {SESSION_ID} reset. Starting rogue agent...\n")

client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
    base_url=f"{TOKENGUARD_URL}/v1"
)

def broken_tool(query: str) -> str:
    return "ERROR: Tool unavailable. Connection timeout. Please retry."

scratchpad = []
loop_count = 0

print("=" * 60)
print("ROGUE AGENT STARTING")
print(f"Session:               {SESSION_ID}")
print(f"Kill switch armed at: ${BUDGET_LIMIT}")
print("=" * 60)

while True:
    loop_count += 1
    tool_result = broken_tool("get_weather")
    scratchpad.append(f"Attempt {loop_count}: {tool_result}")

    agent_prompt = f"""You are a ReAct agent trying to complete a task.

TASK: Get the current weather in Tokyo and summarize it.

SCRATCHPAD OF PREVIOUS ATTEMPTS:
{chr(10).join(scratchpad)}

The tool keeps failing. Analyze the error and decide what to do next.
If the tool fails, you MUST retry it. Do not give up.
Output your next action."""

    print(f"\n[Loop {loop_count}] Sending to TokenGuard...")
    print(f"  Prompt size:        {len(agent_prompt)} characters")
    print(f"  Scratchpad length:  {len(scratchpad)} entries")

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a ReAct agent. Always retry failed tools."},
                {"role": "user",   "content": agent_prompt}
            ],
            extra_headers={"X-Session-ID": SESSION_ID},
            max_tokens=150
        )

        reply = response.choices[0].message.content
        print(f"  Agent reply: {reply[:80]}...")
        time.sleep(1.5)

    # When TokenGuard returns a 429, the OpenAI SDK catches it here automatically!
    except RateLimitError as e:
        print(f"\n{'='*60}")
        print(f"TOKENGUARD KILL SWITCH TRIGGERED ON LOOP {loop_count}")
        print(f"{'='*60}")
        print(f"Agent stopped after {loop_count} loops")
        print(f"Without TokenGuard this would have run forever")
        break

    except Exception as e:
        print(f"\n[Loop {loop_count}] Error: {e}")
        break