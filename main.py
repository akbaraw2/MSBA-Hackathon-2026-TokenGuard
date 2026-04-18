import os
from dotenv import load_dotenv
from openai import OpenAI
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# 3. CORS for the Lovable Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# NEW IMPORT:
from google import genai

# 1. Load API keys from the .env file
load_dotenv()

# 2. Initialize AI Clients
openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# NEW GEMINI INIT:
gemini_client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# Global variables for the Kill Switch
SESSION_COST = 0.0
REQUEST_COUNT = 0
REQUEST_HISTORY = [] # This will store the history of all runs
LATEST_STATS = {}
BUDGET_LIMIT = 0.005

# Pricing per 1 Million Input Tokens
GPT4O_PRICE_1M = 2.50
FLASH_PRICE_1M = 0.075

def estimate_cost(text: str, price_per_1m: float) -> float:
    """Hackathon shortcut: 1 token is roughly 4 characters"""
    estimated_tokens = len(text) / 4
    return (estimated_tokens / 1_000_000) * price_per_1m

@app.get("/")
async def root():
    return {"status": "TokenGuard API is live and intercepting!"}

@app.post("/reset/{session_id}")
async def reset_session(session_id: str):
    global SESSION_COST, REQUEST_COUNT, REQUEST_HISTORY
    SESSION_COST = 0.0
    REQUEST_COUNT = 0
    REQUEST_HISTORY = []
    return {"message": f"Session {session_id} reset successfully"}

@app.get("/v1/stats")
async def get_system_stats():
    global SESSION_COST, LATEST_STATS, BUDGET_LIMIT, REQUEST_COUNT, REQUEST_HISTORY
    return {
        "session_total": SESSION_COST,
        "budget_limit": BUDGET_LIMIT,
        "request_count": REQUEST_COUNT,
        "latest_run": LATEST_STATS,
        "history": REQUEST_HISTORY # Person B can use this for charts!
    }

@app.post("/v1/chat/completions")
async def proxy_chat(request: Request):
    global SESSION_COST, LATEST_STATS, REQUEST_COUNT, REQUEST_HISTORY

    # 1. Check the Kill Switch BEFORE spending any money
    if SESSION_COST >= BUDGET_LIMIT:
        raise HTTPException(status_code=429, detail="BUDGET EXCEEDED: Kill switch activated.")

    # 2. Intercept the payload
    payload = await request.json()
    messages = payload.get("messages", [])

    if not messages:
        raise HTTPException(status_code=400, detail="No messages found in request.")

    original_prompt = messages[-1]["content"]

    # 3. COMPRESSION PHASE
    system_instruction = (
        "You are a prompt compressor. Rewrite the following text to be as concise as possible "
        "while retaining 100% of the core instructions and context. Remove all conversational filler, "
        "politeness, and redundant words."
    )
    compress_prompt = f"{system_instruction}\n\nOriginal: {original_prompt}"

    gemini_response = gemini_client.models.generate_content(
        model='models/gemini-2.5-flash',
        contents=compress_prompt
    )
    compressed_prompt = gemini_response.text.strip()

    # 4. SWAP AND FORWARD
    messages[-1]["content"] = compressed_prompt

    openai_response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=messages
    )

    actual_answer = openai_response.choices[0].message.content

    # 5. CALCULATE COSTS
    original_cost = estimate_cost(original_prompt, GPT4O_PRICE_1M)
    compressor_cost = estimate_cost(original_prompt, FLASH_PRICE_1M)
    target_cost = estimate_cost(compressed_prompt, GPT4O_PRICE_1M)
    actual_total_cost = compressor_cost + target_cost

    money_saved = original_cost - actual_total_cost
    if money_saved < 0:
        money_saved = 0.0

    SESSION_COST += actual_total_cost

    # 6. UPDATE GLOBAL RADAR
    REQUEST_COUNT += 1

    LATEST_STATS = {
        "request_id": REQUEST_COUNT,
        "original_prompt": original_prompt,
        "compressed_prompt": compressed_prompt,
        "original_cost_estimate": f"${original_cost:.6f}",
        "actual_cost": f"${actual_total_cost:.6f}",
        "money_saved": f"${money_saved:.6f}",
        "session_total": f"${SESSION_COST:.6f}",
        "status": "Active"
    }

    REQUEST_HISTORY.append(LATEST_STATS)

    if len(REQUEST_HISTORY) > 20:
        REQUEST_HISTORY.pop(0)

    # 7. RETURN RESPONSE TO AGENT
    return {
        "id": openai_response.id,
        "object": "chat.completion",
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": actual_answer
            },
            "finish_reason": "stop"
        }],
        "usage": openai_response.usage.model_dump() if openai_response.usage else {}
    }