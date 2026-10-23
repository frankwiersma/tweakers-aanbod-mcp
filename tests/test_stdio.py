import json
import subprocess
import sys

DISCOVER_PROBE = {
    "jsonrpc": "2.0",
    "id": "probe",
    "method": "server/discover",
    "params": {"_meta": {"io.modelcontextprotocol/protocolVersion": "2026-07-28"}},
}
INITIALIZE = {
    "jsonrpc": "2.0",
    "id": 0,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-11-25",
        "capabilities": {},
        "clientInfo": {"name": "test", "version": "0"},
    },
}


def test_initialize_after_discover_probe_is_accepted():
    """Claude Code probes with `server/discover`, then sends `initialize` on the same connection."""
    frames = "".join(json.dumps(frame) + "\n" for frame in (DISCOVER_PROBE, INITIALIZE))
    process = subprocess.run(
        [sys.executable, "-c", "from tweakers_aanbod_mcp.server import main; main()"],
        input=frames,
        capture_output=True,
        text=True,
        timeout=30,
    )

    replies = {reply["id"]: reply for reply in map(json.loads, process.stdout.splitlines())}
    assert "error" in replies["probe"]
    assert replies[0]["result"]["serverInfo"]["name"] == "tweakers-aanbod"
