"""Call the configured Stitch MCP without copying credentials into project files."""

import json
import os
from pathlib import Path
import sys
import tomllib

import requests


def call_tool(name, arguments):
    home = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))
    config = tomllib.loads((home / "config.toml").read_text(encoding="utf-8-sig"))
    server = config["mcp_servers"]["stitch"]
    response = requests.post(
        server["url"],
        headers={**server["http_headers"], "Accept": "application/json, text/event-stream"},
        json={"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": name, "arguments": arguments}},
        timeout=600,
        allow_redirects=False,
    )
    response.raise_for_status()
    return response.json()


if __name__ == "__main__":
    request_path, output_path = map(Path, sys.argv[1:3])
    request = json.loads(request_path.read_text(encoding="utf-8"))
    try:
        result = call_tool(request["name"], request["arguments"])
    except requests.RequestException as exc:
        print(f"Stitch request failed: {type(exc).__name__}. Do not retry generation blindly.")
        sys.exit(1)
    output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Saved Stitch response: {output_path}")
    body = result.get("result", {})
    print("MCP error:", bool(result.get("error") or body.get("isError")))
    for item in body.get("content", []):
        if item.get("type") == "text":
            print(item.get("text", "")[:14000])
