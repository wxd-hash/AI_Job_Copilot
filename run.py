"""Entry point for running the AI Job Copilot API server.

Usage:
    python run.py              # Default: http://0.0.0.0:8000
    python run.py --port 8080  # Custom port
    python run.py --reload     # Dev mode with auto-reload
"""

import argparse
import socket
import sys
import uvicorn


def _is_port_in_use(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            return False
        except OSError:
            return True


def main():
    parser = argparse.ArgumentParser(description="AI Job Copilot API Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    args = parser.parse_args()

    if _is_port_in_use(args.host, args.port):
        print(f"\n  Port {args.port} is already in use.\n")
        print(f"  Fix: python run.py --port {args.port + 1}")
        print(f"   Or: kill the process on port {args.port}\n")
        sys.exit(1)

    print(f"\n  Starting AI Job Copilot on http://{args.host}:{args.port}")
    print(f"  API docs: http://localhost:{args.port}/docs\n")

    uvicorn.run(
        "backend.api.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info",
    )


if __name__ == "__main__":
    main()
