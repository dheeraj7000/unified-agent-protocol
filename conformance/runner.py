#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


# Helper for HTTP requests
def make_request(
    url: str, method: str, data: dict = None, headers: dict = None, timeout: float = 5.0
) -> tuple[int, dict]:
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8") if data else None,
        headers=headers or {"Content-Type": "application/json"},
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8"))
        except Exception:
            return e.code, {"error": e.reason}
    except Exception as e:
        return 500, {"error": str(e)}


# Read SSE events line-by-line using a standard HTTP request with a socket timeout
def read_sse_events(url: str, timeout: float = 2.0) -> list[dict]:
    events = []
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            current_event = {}
            for line_bytes in response:
                line = line_bytes.decode("utf-8").strip()
                if not line:
                    if current_event:
                        events.append(current_event)
                        current_event = {}
                    continue
                if line.startswith("id:"):
                    current_event["id"] = line.split(":", 1)[1].strip()
                elif line.startswith("event:"):
                    current_event["type"] = line.split(":", 1)[1].strip()
                elif line.startswith("data:"):
                    try:
                        current_event["data"] = json.loads(line.split(":", 1)[1].strip())
                    except Exception:
                        current_event["data"] = line.split(":", 1)[1].strip()
            if current_event:
                events.append(current_event)
    except Exception:
        # Gracefully handle timeouts or clean disconnects on completed tasks
        pass
    return events


# Schema Validation functions
def validate_capability_list_schema(data: Any) -> list[str]:
    errors = []
    if not isinstance(data, dict) or "capabilities" not in data:
        return ["Response is not a dictionary or is missing 'capabilities' key"]
    caps = data["capabilities"]
    if not isinstance(caps, list):
        return ["'capabilities' key must be a list"]
    for i, cap in enumerate(caps):
        if not isinstance(cap, dict):
            errors.append(f"Capability index {i} is not a dictionary")
            continue
        for field in ["capability_id", "purpose", "input_schema", "output_schema", "risk", "tags"]:
            if field not in cap:
                errors.append(f"Capability index {i} missing field: {field!r}")
        if "capability_id" in cap and not isinstance(cap["capability_id"], str):
            errors.append(f"Capability index {i} 'capability_id' must be a string")
        if "purpose" in cap and not isinstance(cap["purpose"], str):
            errors.append(f"Capability index {i} 'purpose' must be a string")
        if "tags" in cap and not isinstance(cap["tags"], list):
            errors.append(f"Capability index {i} 'tags' must be a list")
    return errors


def validate_task_schema(data: Any) -> list[str]:
    errors = []
    if not isinstance(data, dict):
        return ["Response is not a dictionary"]
    if "task_id" not in data:
        errors.append("Response is missing 'task_id'")
    elif not isinstance(data["task_id"], str) or not data["task_id"]:
        errors.append("Response 'task_id' must be a non-empty string")
    if "status" not in data:
        errors.append("Response is missing 'status'")
    else:
        status = data["status"]
        valid_statuses = {"accepted", "completed", "failed", "waiting_for_approval", "cancelled"}
        if status not in valid_statuses:
            errors.append(f"Response 'status' must be one of {valid_statuses}, got {status!r}")
        if status in ("failed", "waiting_for_approval"):
            if "error" not in data:
                errors.append(f"Response 'error' key missing for status {status!r}")
            elif not isinstance(data["error"], dict):
                errors.append(f"Response 'error' key must be a dictionary for status {status!r}")
            else:
                err = data["error"]
                for field in ["code", "message", "recoverable", "safe_retry"]:
                    if field not in err:
                        errors.append(f"Response error object missing field: {field!r}")
                if status == "waiting_for_approval":
                    details = err.get("details", {})
                    if not isinstance(details, dict) or "capability_id" not in details:
                        errors.append(
                            "Response error.details must be a dict containing 'capability_id'"
                        )
    return errors


# Event Ordering validation
def check_event_ordering(events: list[dict], expected_status: str) -> list[str]:
    errors = []
    if not events:
        return ["No events received in stream"]

    event_types = [evt.get("type") for evt in events]

    # 1. First event must be task.accepted (or error.terminal/task.failed for upfront validation failures)
    if expected_status == "failed" and event_types[0] in ("error.terminal", "task.failed"):
        pass
    elif event_types[0] != "task.accepted":
        errors.append(f"First event in stream was {event_types[0]!r}, expected 'task.accepted'")

    # 2. Check terminal event matching expected_status
    last_event = event_types[-1]
    if expected_status == "completed":
        if "task.completed" not in event_types:
            errors.append("Expected 'task.completed' event to be present in stream")
        elif last_event != "task.completed":
            errors.append(f"Last event was {last_event!r}, expected 'task.completed'")
    elif expected_status == "failed":
        if "task.failed" not in event_types:
            errors.append("Expected 'task.failed' event to be present in stream")
        elif last_event != "task.failed":
            errors.append(f"Last event was {last_event!r}, expected 'task.failed'")
    elif expected_status == "cancelled":
        if "task.cancelled" not in event_types:
            errors.append("Expected 'task.cancelled' event to be present in stream")
        elif last_event != "task.cancelled":
            errors.append(f"Last event was {last_event!r}, expected 'task.cancelled'")

    # 3. Check tool execution order (tool.started -> tool.completed)
    for i, evt in enumerate(events):
        evt_type = evt.get("type")
        if evt_type == "tool.started":
            node_id = evt.get("data", {}).get("node_id")
            # Must have corresponding tool.completed later
            completed_found = False
            for next_evt in events[i + 1 :]:
                if (
                    next_evt.get("type") == "tool.completed"
                    and next_evt.get("data", {}).get("node_id") == node_id
                ):
                    completed_found = True
                    break
            if not completed_found:
                errors.append(
                    f"tool.started event for node {node_id!r} has no matching tool.completed event"
                )

    # 4. Check approval lifecycle order
    if "approval.requested" in event_types:
        idx_req = event_types.index("approval.requested")
        if "approval.granted" in event_types:
            idx_grant = event_types.index("approval.granted")
            if idx_req > idx_grant:
                errors.append("Event 'approval.requested' occurred after 'approval.granted'")
            if "task.completed" in event_types:
                idx_comp = event_types.index("task.completed")
                if idx_grant > idx_comp:
                    errors.append("Event 'approval.granted' occurred after 'task.completed'")
        else:
            # If not yet approved, check it stopped at approval.requested
            if "task.completed" in event_types or "tool.completed" in event_types[idx_req:]:
                errors.append(
                    "Execution continued after approval.requested without approval.granted"
                )

    # 5. Check trace_id consistency
    trace_ids = {
        evt.get("data", {}).get("trace_id") for evt in events if evt.get("data", {}).get("trace_id")
    }
    if len(trace_ids) > 1:
        errors.append(f"Multiple different trace_ids found in event stream: {trace_ids}")

    return errors


def run(
    target: str,
    vectors_dir: str = "conformance/test-vectors",
    report_path: str = "conformance-report.json",
) -> bool:
    print(f"Starting UAP Conformance Runner against {target}")

    # 1. Capability Discovery Check
    print("Running Capability Discovery Check...")
    status_code, caps_data = make_request(f"{target}/uap/capabilities", "GET")
    if status_code != 200:
        print(f"❌ Capability discovery failed with status {status_code}")
        return False
    caps_errors = validate_capability_list_schema(caps_data)
    if caps_errors:
        print("❌ Capability discovery schema validation errors:")
        for err in caps_errors:
            print(f"  - {err}")
        return False
    print("✅ Capability discovery passed schema validation.")

    # 2. Run Test Vectors
    p = Path(vectors_dir)
    if not p.exists():
        print(f"❌ Directory {vectors_dir} does not exist.")
        return False

    results = []
    all_passed = True

    for f in sorted(p.glob("*.json")):
        try:
            v = json.loads(f.read_text())
        except Exception as e:
            print(f"Failed to parse {f}: {e}")
            continue

        name = v.get("name", f.name)
        description = v.get("description", "")
        envelope = v.get("input", {})
        expect = v.get("expect", {})

        print(f"\nRunning test vector: {name} ({description})")

        test_result = {"name": name, "description": description, "passed": False, "errors": []}

        # Submit task
        status_code, r = make_request(f"{target}/uap/tasks", "POST", envelope)

        # Validate schema of response
        schema_errors = validate_task_schema(r)
        if schema_errors:
            test_result["errors"].extend([f"POST schema error: {e}" for e in schema_errors])

        # Verify status in response
        got_status = r.get("status") if isinstance(r, dict) else None
        if "status" in expect:
            if got_status != expect["status"]:
                test_result["errors"].append(
                    f"Expected status={expect['status']!r}, got {got_status!r}"
                )

        # Verify error code if expected
        if "error.code" in expect:
            got_error = r.get("error") if isinstance(r, dict) else {}
            got_code = got_error.get("code") if isinstance(got_error, dict) else None
            if got_code != expect["error.code"]:
                test_result["errors"].append(
                    f"Expected error.code={expect['error.code']!r}, got {got_code!r}"
                )

        task_id = r.get("task_id") if isinstance(r, dict) else None

        # Approval Lifecycle Check
        if (
            got_status == "waiting_for_approval"
            and expect.get("status") == "waiting_for_approval"
            and task_id
        ):
            print(f"  -> Testing approval lifecycle for task {task_id}...")
            # 1. Check GET /uap/tasks/{task_id} returns waiting_for_approval
            get_status, get_r = make_request(f"{target}/uap/tasks/{task_id}", "GET")
            if get_status != 200:
                test_result["errors"].append(f"GET /uap/tasks/{task_id} failed with {get_status}")
            else:
                get_schema_errors = validate_task_schema(get_r)
                if get_schema_errors:
                    test_result["errors"].extend(
                        [f"GET schema error: {e}" for e in get_schema_errors]
                    )
                if get_r.get("status") != "waiting_for_approval":
                    test_result["errors"].append(
                        f"GET task status expected 'waiting_for_approval', got {get_r.get('status')!r}"
                    )

            # 2. Approve the task
            approve_status, approve_r = make_request(
                f"{target}/uap/tasks/{task_id}/approve",
                "POST",
                {"approver_id": "conformance_approver"},
            )
            if approve_status != 200:
                test_result["errors"].append(
                    f"POST /uap/tasks/{task_id}/approve failed with {approve_status}: {approve_r}"
                )
            else:
                approve_schema_errors = validate_task_schema(approve_r)
                if approve_schema_errors:
                    test_result["errors"].extend(
                        [f"Approval response schema error: {e}" for e in approve_schema_errors]
                    )
                if approve_r.get("status") != "completed":
                    test_result["errors"].append(
                        f"Approval response status expected 'completed', got {approve_r.get('status')!r}"
                    )

            # 3. Verify GET /uap/tasks/{task_id} is completed
            get_status2, get_r2 = make_request(f"{target}/uap/tasks/{task_id}", "GET")
            if get_status2 != 200:
                test_result["errors"].append(
                    f"GET /uap/tasks/{task_id} after approval failed with {get_status2}"
                )
            elif get_r2.get("status") != "completed":
                test_result["errors"].append(
                    f"GET task status after approval expected 'completed', got {get_r2.get('status')!r}"
                )

            # For event ordering validation, we expect it to end in completed
            final_expected_status = "completed"
        else:
            final_expected_status = expect.get("status", got_status)

        # Event stream validation
        if task_id:
            print("  -> Fetching and validating event stream...")
            events = read_sse_events(f"{target}/uap/tasks/{task_id}/events")
            event_errors = check_event_ordering(events, final_expected_status)
            if event_errors:
                test_result["errors"].extend([f"Event ordering error: {e}" for e in event_errors])

        if not test_result["errors"]:
            print(f"✅ PASS: {name}")
            test_result["passed"] = True
        else:
            print(f"❌ FAIL: {name}")
            all_passed = False
            for err in test_result["errors"]:
                print(f"    - {err}")

        results.append(test_result)

    # Write report
    report = {
        "target": target,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "all_passed": all_passed,
        "total_count": len(results),
        "passed_count": sum(1 for r in results if r["passed"]),
        "failed_count": sum(1 for r in results if not r["passed"]),
        "results": results,
    }

    with open(report_path, "w") as rf:
        json.dump(report, rf, indent=2)
    print(f"\nWritten conformance report to {report_path}")
    print(f"Summary: {report['passed_count']} passed, {report['failed_count']} failed")

    return all_passed


def main():
    parser = argparse.ArgumentParser(description="UAP Conformance Runner")
    parser.add_argument("--target", default="http://localhost:8000", help="Target UAP server URL")
    parser.add_argument(
        "--vectors", default="conformance/test-vectors", help="Path to test vectors directory"
    )
    parser.add_argument(
        "--report", default="conformance-report.json", help="Path to write conformance report"
    )
    parser.add_argument(
        "--ci",
        action="store_true",
        help="Start the reference server in background, run tests, and shutdown",
    )
    args = parser.parse_args()

    if args.ci:
        print("CI Mode: Spawning uap-server in the background...")
        # Start server subprocess using PYTHONPATH=src to ensure local package imports work
        env = os.environ.copy()
        env["PYTHONPATH"] = str(Path("src").absolute())

        server_proc = subprocess.Popen(
            [sys.executable, "-m", "uap.server"],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # Wait for health check to pass
        health_url = f"{args.target}/health"
        healthy = False
        print(f"Waiting for server at {health_url} to start...")
        for _ in range(30):
            try:
                status, _ = make_request(health_url, "GET", timeout=1.0)
                if status == 200:
                    healthy = True
                    break
            except Exception:
                pass
            time.sleep(0.2)

        if not healthy:
            print("❌ Server failed to start or pass health check in time.")
            stdout, stderr = server_proc.communicate(timeout=1.0)
            print("Server stdout:", stdout.decode("utf-8"))
            print("Server stderr:", stderr.decode("utf-8"))
            sys.exit(1)

        print("Server is healthy! Running conformance tests...")

        try:
            success = run(args.target, args.vectors, args.report)
        finally:
            print("Stopping background server...")
            server_proc.terminate()
            try:
                server_proc.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                server_proc.kill()

        sys.exit(0 if success else 1)
    else:
        success = run(args.target, args.vectors, args.report)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
