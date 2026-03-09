"""CLI entry point for the support agent."""
import argparse
import sys
from pathlib import Path

# Load .env from repo root so OPENAI_API_KEY is set when user copies .env.example to .env
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

from app.agent import run
from app.config import get_config


def main() -> int:
    parser = argparse.ArgumentParser(description="Support agent CLI")
    parser.add_argument("--query", "-q", required=True, help="User support question")
    parser.add_argument("--role", default="support_agent", help="Role for tool allowance (default: support_agent)")
    args = parser.parse_args()
    try:
        get_config(require_api_key=True)
    except ValueError as e:
        print(e, file=sys.stderr)
        return 1
    response = run(args.query, role=args.role)
    print(response.final_text)
    if response.refused:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
