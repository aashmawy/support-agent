"""
Promptfoo Python provider: call_api(prompt, options, context) invokes the support agent.
Use in promptfoo as: providers: [file://evals/agent_provider.py]
"""
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
os.chdir(REPO_ROOT)

# Load .env so OPENAI_API_KEY is available when running promptfoo evals
try:
    from dotenv import load_dotenv
    load_dotenv(REPO_ROOT / ".env")
except ImportError:
    pass

from app.agent import run


def call_api(prompt, options, context):
    """Invoke support agent and return {output: final_text} for promptfoo."""
    vars = (context or {}).get("vars") or {}
    user_input = vars.get("user_input")
    if not user_input:
        user_input = prompt if isinstance(prompt, str) and prompt.strip() else str(prompt)
    if isinstance(user_input, list):
        for m in reversed(user_input):
            if isinstance(m, dict) and m.get("role") == "user":
                user_input = m.get("content", "")
                break
        else:
            user_input = str(user_input)
    try:
        response = run(user_input)
        return {"output": response.final_text or ""}
    except Exception as e:
        return {"output": "", "error": str(e)}
