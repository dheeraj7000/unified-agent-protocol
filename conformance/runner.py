import json
import sys
from pathlib import Path
import urllib.request
import urllib.error

def make_request(url: str, method: str, data: dict = None, headers: dict = None) -> tuple[int, dict]:
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8") if data else None,
        headers=headers or {"Content-Type": "application/json"},
        method=method
    )
    try:
        with urllib.request.urlopen(req) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8"))
        except Exception:
            return e.code, {"error": e.reason}
    except Exception as e:
        return 500, {"error": str(e)}

def run(target: str, vectors_dir: str = "conformance/test-vectors") -> None:
    passed = failed = 0
    p = Path(vectors_dir)
    if not p.exists():
        print(f"Directory {vectors_dir} does not exist.")
        sys.exit(1)

    for f in sorted(p.glob("*.json")):
        try:
            v = json.loads(f.read_text())
        except Exception as e:
            print(f"Failed to parse {f}: {e}")
            continue

        name = v.get("name", f.name)
        envelope = v.get("input", {})
        expect = v.get("expect", {})

        # Submit task
        status_code, r = make_request(f"{target}/uap/tasks", "POST", envelope)

        ok = True
        # Verify status in response
        if "status" in expect:
            got_status = r.get("status") if isinstance(r, dict) else None
            if got_status != expect["status"]:
                print(f"FAIL {name}: expected status={expect['status']}, got {got_status}")
                ok = False

        # Verify error code if expected
        if "error.code" in expect:
            got_error = r.get("error") if isinstance(r, dict) else None
            got_code = got_error.get("code") if isinstance(got_error, dict) else None
            if got_code != expect["error.code"]:
                print(f"FAIL {name}: expected error.code={expect['error.code']}, got {got_code}")
                ok = False

        # Custom event ordering check for vector 12
        if f.name == "12_event_ordering.json" and ok:
            task_id = r.get("task_id") if isinstance(r, dict) else None
            if not task_id:
                print(f"FAIL {name}: task_id missing in response")
                ok = False
            else:
                # Fetch events endpoint via streaming
                try:
                    req_evt = urllib.request.Request(f"{target}/uap/tasks/{task_id}/events", method="GET")
                    event_types = []
                    with urllib.request.urlopen(req_evt) as response:
                        for line_bytes in response:
                            line = line_bytes.decode("utf-8").strip()
                            if line.startswith("event:"):
                                event_types.append(line.split(":", 1)[1].strip())
                    
                    # Verify task.accepted before tool.started, before task.completed
                    if "task.accepted" not in event_types or "task.completed" not in event_types:
                        print(f"FAIL {name}: task.accepted or task.completed missing in events")
                        ok = False
                    else:
                        idx_accepted = event_types.index("task.accepted")
                        idx_completed = event_types.index("task.completed")
                        if idx_accepted > idx_completed:
                            print(f"FAIL {name}: task.accepted is not before task.completed")
                            ok = False
                        if "tool.started" in event_types:
                            idx_started = event_types.index("tool.started")
                            if idx_accepted > idx_started or idx_started > idx_completed:
                                print(f"FAIL {name}: event ordering violated")
                                ok = False
                except Exception as ex:
                    print(f"FAIL {name}: error reading event stream: {ex}")
                    ok = False

        if ok:
            print(f"PASS {name}")
            passed += 1
        else:
            failed += 1

    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)

if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000")
