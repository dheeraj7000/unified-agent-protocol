from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from .runtime import UAPRuntime
from .validation import validate_envelope_minimal


def main() -> None:
    parser = argparse.ArgumentParser(description="UAP reference CLI")
    parser.add_argument("command", choices=["validate", "run-empty"])
    parser.add_argument("file", nargs="?", help="JSON payload file")
    args = parser.parse_args()

    if args.command == "validate":
        if not args.file:
            raise SystemExit("validate requires a JSON file")
        data = json.loads(Path(args.file).read_text())
        validate_envelope_minimal(data)
        print(json.dumps({"valid": True}, indent=2))
    elif args.command == "run-empty":
        if not args.file:
            raise SystemExit("run-empty requires a JSON file")
        data = json.loads(Path(args.file).read_text())
        runtime = UAPRuntime()
        print(json.dumps(asyncio.run(runtime.invoke(data)), indent=2))


if __name__ == "__main__":
    main()
