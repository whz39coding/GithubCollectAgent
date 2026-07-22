#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import os
import uvicorn
from dotenv import load_dotenv

# Load env variables from backend/.env if exists
from backend.core.config import BACKEND_ROOT

env_path = BACKEND_ROOT / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)


def main():
    parser = argparse.ArgumentParser(description="Start the GitHub Insight Agent Dashboard Server")
    parser.add_argument(
        "--host",
        type=str,
        default=os.getenv("HOST", "0.0.0.0"),
        help="Host to bind the server to (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("PORT", "8000")),
        help="Port to run the server on (default: 8000)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable uvicorn auto-reload (for development)",
    )

    args = parser.parse_args()

    print(f"============================================================")
    print(f"[*] GitHub Insight Agent Dashboard is starting...")
    print(f"[*] Access URL: http://{args.host}:{args.port}")
    print(f"============================================================")

    uvicorn.run(
        "backend.api.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
