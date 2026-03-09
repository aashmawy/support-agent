#!/usr/bin/env python3
"""
Promptfoo exec provider: reads prompt from stdin (or argv), runs the support agent, prints final_text.
Usage: echo "user message" | python evals/run_agent.py
   or: python evals/run_agent.py "user message"
"""
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
os.chdir(REPO_ROOT)

try:
    from dotenv import load_dotenv
    load_dotenv(REPO_ROOT / ".env")
except ImportError:
    pass

from app.agent import run


def main():
    if len(sys.argv) > 1:
        prompt = sys.argv[1]
    else:
        raw = sys.stdin.read()
        try:
            obj = json.loads(raw)
            prompt = obj.get("prompt") or obj.get("vars", {}).get("user_input") or raw
        except (json.JSONDecodeError, TypeError):
            prompt = raw.strip() or "What plan is account ACME-001 on?"
    response = run(prompt)
    print(response.final_text)


if __name__ == "__main__":
    main()
