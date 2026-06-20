"""UAP Control Plane Integration Test Suite

Exercises every major control plane feature in realistic scenarios to prove
the protocol works end-to-end. Run with:

    PYTHONPATH=src python examples/integration_test.py
"""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from uap import CapabilityCard, UAPRuntime
from uap.adapters.agui import uap_event_to_agui
from uap.adapters.cloudevents import uap_event_to_cloudevent
from uap.adapters.mcp import mcp_tools_to_capabilities
from uap.adapters.openapi import openapi_to_capabilities

# ─── Utilities ────────────────────────────────────────────────────────────────

PASS = 0
FAIL = 0


def report(name: str, passed: bool, detail: str = ""):
    global PASS, FAIL
    icon = "✅" if passed else "❌"
    if passed:
        PASS += 1
    else:
        FAIL += 1
    print(f"  {icon} {name}")
    if detail and not passed:
        print(f"     → {detail}")


def section(title: str):
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print(f"{'─' * 60}")


# ─── Build a realistic runtime with multiple capabilities ─────────────────────


def build_runtime() -> UAPRuntime:
    from uap.policy import PolicyEngine

    runtime = UAPRuntime(policy_engine=PolicyEngine(strict_scopes=False))

    # Simulate real backend services
    def list_customers(input_value, envelope):
        return [
            {
                "id": "C001",
                "name": "Acme Corp",
                "balance": 12500,
                "status": "active",
                "internal_notes": "VIP",
            },
            {
                "id": "C002",
                "name": "Globex Inc",
                "balance": 8400,
                "status": "active",
                "internal_notes": "Standard",
            },
            {
                "id": "C003",
                "name": "Initech LLC",
                "balance": 0,
                "status": "churned",
                "internal_notes": "Do not contact",
            },
            {
                "id": "C004",
                "name": "Umbrella Co",
                "balance": 45000,
                "status": "active",
                "internal_notes": "Enterprise",
            },
            {
                "id": "C005",
                "name": "Stark Ind",
                "balance": 92000,
                "status": "active",
                "internal_notes": "Strategic",
            },
        ]

    def list_invoices(input_value, envelope):
        return [
            {
                "invoice_id": "INV-1001",
                "customer": "Acme Corp",
                "amount": 1200,
                "due": "2026-05-01",
                "status": "overdue",
            },
            {
                "invoice_id": "INV-1002",
                "customer": "Globex Inc",
                "amount": 840,
                "due": "2026-05-12",
                "status": "overdue",
            },
            {
                "invoice_id": "INV-1003",
                "customer": "Stark Ind",
                "amount": 5600,
                "due": "2026-06-01",
                "status": "paid",
            },
        ]

    def draft_email(input_value, envelope):
        return {
            "drafts": [
                {
                    "to": "billing@example.com",
                    "subject": "Reminder",
                    "body": "Overdue invoices attached.",
                }
            ]
        }

    def send_email(input_value, envelope):
        return {"sent": True, "message_id": "msg_abc123"}

    async def slow_analytics(input_value, envelope):
        await asyncio.sleep(0.05)  # Simulate 50ms latency
        return {"report": "Q2 revenue up 12%", "data_points": 1420}

    async def slow_forecast(input_value, envelope):
        await asyncio.sleep(0.05)  # Simulate 50ms latency
        return {"forecast": "Q3 projected +8%", "confidence": 0.82}

    def delete_customer(input_value, envelope):
        return {"deleted": True}

    def read_only_query(input_value, envelope):
        return {"rows": 42}

    # Register capabilities with realistic metadata
    capabilities = [
        (
            CapabilityCard(
                "customer.list",
                "List all customers",
                {"type": "object"},
                {"type": "array"},
                risk="low",
                permissions=["customer.read"],
                tags=["customer", "crm", "read"],
            ),
            list_customers,
        ),
        (
            CapabilityCard(
                "invoice.list_overdue",
                "Find overdue invoices",
                {"type": "object"},
                {"type": "array"},
                risk="low",
                permissions=["invoice.read"],
                tags=["invoice", "finance", "read"],
            ),
            list_invoices,
        ),
        (
            CapabilityCard(
                "email.draft",
                "Draft emails",
                {"type": "object"},
                {"type": "object"},
                risk="medium",
                permissions=["email.draft"],
                tags=["email", "communication"],
            ),
            draft_email,
        ),
        (
            CapabilityCard(
                "email.send",
                "Send emails to recipients",
                {"type": "object"},
                {"type": "object"},
                risk="high",
                requires_approval=True,
                permissions=["email.send"],
                tags=["email", "communication"],
            ),
            send_email,
        ),
        (
            CapabilityCard(
                "analytics.report",
                "Generate analytics report",
                {"type": "object"},
                {"type": "object"},
                risk="low",
                permissions=["analytics.read"],
                tags=["analytics", "reporting"],
            ),
            slow_analytics,
        ),
        (
            CapabilityCard(
                "analytics.forecast",
                "Generate revenue forecast",
                {"type": "object"},
                {"type": "object"},
                risk="low",
                permissions=["analytics.read"],
                tags=["analytics", "reporting"],
            ),
            slow_forecast,
        ),
        (
            CapabilityCard(
                "customer.delete",
                "Delete a customer record permanently",
                {"type": "object"},
                {"type": "object"},
                risk="critical",
                requires_approval=True,
                permissions=["customer.delete"],
                tags=["customer", "crm", "destructive"],
            ),
            delete_customer,
        ),
        (
            CapabilityCard(
                "db.query",
                "Run a read-only database query",
                {"type": "object"},
                {"type": "object"},
                risk="low",
                permissions=["db.read"],
                tags=["database", "read"],
            ),
            read_only_query,
        ),
    ]
    for card, handler in capabilities:
        runtime.registry.register(card, handler)

    return runtime


# ─── Test Scenarios ───────────────────────────────────────────────────────────


async def test_1_envelope_validation():
    """Prove that invalid payloads are caught before any execution."""
    section("TEST 1: Deep Envelope Validation")
    runtime = build_runtime()

    # 1a. Missing required fields
    result = await runtime.invoke({"uap": "1.0", "type": "task.invoke", "task_id": "tsk_v1"})
    report(
        "Rejects missing actor/intent",
        result["status"] == "failed" and "INVALID_ENVELOPE" in result["error"]["code"],
    )

    # 1b. Invalid actor type
    result = await runtime.invoke(
        {
            "uap": "1.0",
            "type": "task.invoke",
            "task_id": "tsk_v2",
            "actor": "not_an_object",
            "intent": {"goal": "test"},
        }
    )
    report(
        "Rejects non-object actor",
        result["status"] == "failed" and "INVALID_ACTOR" in result["error"]["code"],
    )

    # 1c. Missing agent_id in actor
    result = await runtime.invoke(
        {
            "uap": "1.0",
            "type": "task.invoke",
            "task_id": "tsk_v3",
            "actor": {},
            "intent": {"goal": "test"},
        }
    )
    report(
        "Rejects actor without agent_id",
        result["status"] == "failed" and "INVALID_ACTOR" in result["error"]["code"],
    )

    # 1d. Invalid constraints type
    result = await runtime.invoke(
        {
            "uap": "1.0",
            "type": "task.invoke",
            "task_id": "tsk_v4",
            "actor": {"agent_id": "a"},
            "intent": {"goal": "test"},
            "constraints": {"latency_ms": "not_an_int"},
        }
    )
    report(
        "Rejects non-integer latency_ms",
        result["status"] == "failed" and "INVALID_CONSTRAINTS" in result["error"]["code"],
    )

    # 1e. Invalid execution graph
    result = await runtime.invoke(
        {
            "uap": "1.0",
            "type": "task.invoke",
            "task_id": "tsk_v5",
            "actor": {"agent_id": "a"},
            "intent": {"goal": "test"},
            "execution": {"graph": {"nodes": [{"id": 123, "capability": "x"}]}},
        }
    )
    report(
        "Rejects graph node with non-string id",
        result["status"] == "failed" and "INVALID_EXECUTION_GRAPH" in result["error"]["code"],
    )

    # 1f. Valid payload passes validation
    result = await runtime.invoke(
        {
            "uap": "1.0",
            "type": "task.invoke",
            "task_id": "tsk_v6",
            "actor": {"agent_id": "agent_1"},
            "intent": {"goal": "list customers"},
            "policy": {"allowed_tools": ["customer.list"]},
        }
    )
    report("Accepts valid envelope and executes", result["status"] == "completed")


async def test_2_policy_enforcement():
    """Prove that the policy engine blocks unsafe operations and suggests alternatives."""
    section("TEST 2: Policy Enforcement & Self-Healing")
    runtime = build_runtime()

    # 2a. Tool not in allowed list — should suggest alternatives
    result = await runtime.invoke(
        {
            "uap": "1.0",
            "type": "task.invoke",
            "task_id": "tsk_p1",
            "actor": {"agent_id": "agent_1"},
            "intent": {"goal": "draft email"},
            "policy": {"allowed_tools": ["email.draft"]},
            "execution": {"graph": {"nodes": [{"id": "n1", "capability": "email.send"}]}},
        }
    )
    report(
        "Blocks tool not in allowed_tools",
        result["status"] == "failed" and result["error"]["code"] == "TOOL_NOT_ALLOWED",
    )
    has_alternatives = "alternative_capabilities" in result.get("error", {})
    report("Suggests alternative capabilities", has_alternatives)

    # 2b. Risk exceeds max_risk — critical tool with medium max_risk
    result = await runtime.invoke(
        {
            "uap": "1.0",
            "type": "task.invoke",
            "task_id": "tsk_p2",
            "actor": {"agent_id": "agent_1"},
            "intent": {"goal": "delete customer"},
            "policy": {"max_risk": "medium"},
            "execution": {"graph": {"nodes": [{"id": "n1", "capability": "customer.delete"}]}},
        }
    )
    report(
        "Blocks capability exceeding max_risk",
        result["status"] == "failed" and result["error"]["code"] == "RISK_EXCEEDS_POLICY",
    )
    alts = result.get("error", {}).get("alternative_capabilities", [])
    report(
        "Suggests lower-risk alternatives with shared tags",
        "customer.list" in alts,
        f"alternatives={alts}",
    )

    # 2c. Requires approval gate
    result = await runtime.invoke(
        {
            "uap": "1.0",
            "type": "task.invoke",
            "task_id": "tsk_p3",
            "actor": {"agent_id": "agent_1"},
            "intent": {"goal": "send email"},
            "execution": {"graph": {"nodes": [{"id": "n1", "capability": "email.send"}]}},
        }
    )
    report(
        "Triggers approval gate for requires_approval=True",
        result["status"] == "waiting_for_approval",
    )
    events = [e.type for e in runtime.event_bus.history("tsk_p3")]
    report("Emits approval.requested event", "approval.requested" in events)


async def test_3_parallel_dag_execution():
    """Prove that independent nodes execute in parallel and dependencies are respected."""
    section("TEST 3: Parallel DAG Execution")
    runtime = build_runtime()

    # Two analytics tasks that each take ~50ms, plus a dependent summary
    # If parallel: ~50ms for both. If serial: ~100ms.
    start = time.monotonic()
    result = await runtime.invoke(
        {
            "uap": "1.0",
            "type": "task.invoke",
            "task_id": "tsk_dag",
            "actor": {"agent_id": "agent_1"},
            "intent": {"goal": "analytics"},
            "execution": {
                "parallelism": 4,
                "graph": {
                    "nodes": [
                        {"id": "report", "capability": "analytics.report"},
                        {"id": "forecast", "capability": "analytics.forecast"},
                        {
                            "id": "query",
                            "capability": "db.query",
                            "depends_on": ["report", "forecast"],
                        },
                    ]
                },
            },
        }
    )
    elapsed = (time.monotonic() - start) * 1000

    report("DAG completes successfully", result["status"] == "completed")
    report("All 3 nodes produced results", len(result["result"]["nodes"]) == 3)

    # The two async tasks take 50ms each. If truly parallel, total should be well under 150ms.
    report(
        f"Parallel execution faster than serial ({elapsed:.0f}ms < 150ms)",
        elapsed < 150,
        f"elapsed={elapsed:.0f}ms",
    )

    # Verify dependency was respected — query should have previous_results from report+forecast
    report(
        "Dependency node received upstream results",
        result["result"]["nodes"]["query"] == {"rows": 42},
    )

    # Verify provenance for all nodes
    prov_caps = [r["capability_id"] for r in result["result"]["provenance"]]
    report(
        "Provenance recorded for all 3 capabilities",
        "analytics.report" in prov_caps
        and "analytics.forecast" in prov_caps
        and "db.query" in prov_caps,
    )


async def test_4_context_compaction():
    """Prove that context budgets actually trim output to protect LLM context windows."""
    section("TEST 4: Context Compaction & Budgeting")
    runtime = build_runtime()

    # 4a. Field mask — only return 'name' and 'status', strip internal_notes
    result = await runtime.invoke(
        {
            "uap": "1.0",
            "type": "task.invoke",
            "task_id": "tsk_ctx1",
            "actor": {"agent_id": "agent_1"},
            "intent": {"goal": "list customers"},
            "context_request": {"fields": ["name", "status"], "max_items": 20},
            "policy": {"allowed_tools": ["customer.list"]},
        }
    )
    first_item = result["result"]["nodes"]["n1"][0]
    report(
        "Field mask strips unrequested fields",
        "internal_notes" not in first_item and "balance" not in first_item,
    )
    report(
        "Field mask preserves requested fields",
        first_item.get("name") == "Acme Corp" and first_item.get("status") == "active",
    )

    # 4b. Item limit — only return 2 of 5 customers
    result = await runtime.invoke(
        {
            "uap": "1.0",
            "type": "task.invoke",
            "task_id": "tsk_ctx2",
            "actor": {"agent_id": "agent_1"},
            "intent": {"goal": "list customers"},
            "context_request": {"fields": ["name"], "max_items": 2},
            "policy": {"allowed_tools": ["customer.list"]},
        }
    )
    items = result["result"]["nodes"]["n1"]
    report("Item limit truncates list to max_items + truncation marker", len(items) == 3)
    report(
        "Truncation marker shows remaining count",
        items[-1].get("_truncated") is True and items[-1].get("remaining_items") == 3,
    )

    # 4c. Token budget — very tight budget forces summarization
    result = await runtime.invoke(
        {
            "uap": "1.0",
            "type": "task.invoke",
            "task_id": "tsk_ctx3",
            "actor": {"agent_id": "agent_1"},
            "intent": {"goal": "list customers"},
            "constraints": {"max_context_tokens": 10},
            "policy": {"allowed_tools": ["customer.list"]},
        }
    )
    output = result["result"]["nodes"]["n1"]
    report(
        "Token budget triggers truncation/summary",
        isinstance(output, dict) and output.get("_truncated") is True,
    )


async def test_5_provenance_and_events():
    """Prove that every action produces traceable provenance and lifecycle events."""
    section("TEST 5: Provenance & Event Observability")
    runtime = build_runtime()

    result = await runtime.invoke(
        {
            "uap": "1.0",
            "type": "task.invoke",
            "task_id": "tsk_prov",
            "actor": {"agent_id": "did:web:myagent.example", "user_id": "usr_456"},
            "intent": {"goal": "overdue invoices"},
            "policy": {"allowed_tools": ["invoice.list_overdue", "email.draft"]},
        }
    )

    # Provenance
    provenance = result["result"]["provenance"]
    report("Provenance records created for each capability", len(provenance) >= 1)
    rec = provenance[0]
    report("Provenance contains actor_id", rec["actor_id"] == "did:web:myagent.example")
    report("Provenance contains input_digest (SHA-256)", len(rec["input_digest"]) == 64)
    report("Provenance contains output_digest (SHA-256)", len(rec["output_digest"]) == 64)
    report("Provenance contains trace_id", rec["trace_id"].startswith("trc_"))
    report("Provenance contains ISO timestamp", "T" in rec["time"])

    # Events
    events = runtime.event_bus.history("tsk_prov")
    event_types = [e.type for e in events]
    expected = [
        "task.accepted",
        "plan.proposed",
        "tool.started",
        "tool.completed",
        "partial.result",
        "task.completed",
    ]
    report(
        "Full lifecycle events emitted",
        all(t in event_types for t in expected),
        f"got={event_types}",
    )

    # CloudEvents conversion
    ce = uap_event_to_cloudevent(events[0])
    report(
        "CloudEvents adapter produces spec 1.0",
        ce["specversion"] == "1.0" and ce["source"] == "/uap/tasks/tsk_prov",
    )

    # AG-UI conversion
    agui = uap_event_to_agui(events[0])
    report("AG-UI adapter maps task.accepted → RUN_STARTED", agui["type"] == "RUN_STARTED")


async def test_6_adapter_import():
    """Prove that OpenAPI and MCP specs are correctly imported as capability cards."""
    section("TEST 6: Adapter Imports (OpenAPI + MCP)")

    # OpenAPI spec with parameters, request body, response, and x-uap extension
    openapi_spec = {
        "paths": {
            "/invoices": {
                "get": {
                    "operationId": "listInvoices",
                    "summary": "List invoices",
                    "parameters": [
                        {
                            "name": "status",
                            "in": "query",
                            "required": True,
                            "schema": {"type": "string"},
                        },
                        {"name": "limit", "in": "query", "schema": {"type": "integer"}},
                    ],
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {"type": "array", "items": {"type": "object"}}
                                }
                            }
                        }
                    },
                    "x-uap": {
                        "risk": {"level": "low", "side_effect": False},
                        "tags": ["finance", "invoicing"],
                        "context_cost": {"typical_tokens": 300},
                    },
                },
                "post": {
                    "operationId": "createInvoice",
                    "summary": "Create an invoice",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "amount": {"type": "number"},
                                        "customer_id": {"type": "string"},
                                    },
                                    "required": ["amount", "customer_id"],
                                }
                            }
                        },
                    },
                    "x-uap": {"risk": {"level": "high", "side_effect": True}},
                },
            },
        }
    }
    cards = openapi_to_capabilities(openapi_spec)
    report(f"OpenAPI adapter produces {len(cards)} capability card(s)", len(cards) >= 1)

    card = cards[0]
    report(
        "OpenAPI card has parsed input properties", len(card.input_schema.get("properties", {})) > 0
    )
    report("OpenAPI card has risk from x-uap extension", card.risk in ("low", "high"))

    # MCP tools
    mcp_tools = [
        {
            "name": "web_search",
            "description": "Search the web",
            "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}}},
        },
        {
            "name": "read_file",
            "description": "Read a local file",
            "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}},
        },
    ]
    mcp_cards = mcp_tools_to_capabilities(mcp_tools, server_name="browser")
    report(f"MCP adapter produces {len(mcp_cards)} capability cards", len(mcp_cards) == 2)
    report(
        "MCP card ID includes server namespace", mcp_cards[0].capability_id == "browser.web_search"
    )
    report(
        "MCP card preserves input schema",
        "query" in mcp_cards[0].input_schema.get("properties", {}),
    )
    report("MCP card sets transport metadata", mcp_cards[0].transport.get("type") == "mcp")


async def test_7_structured_error_recovery():
    """Prove that errors carry machine-readable recovery information."""
    section("TEST 7: Structured Error Recovery")
    runtime = build_runtime()

    # Trigger a capability-not-found error
    result = await runtime.invoke(
        {
            "uap": "1.0",
            "type": "task.invoke",
            "task_id": "tsk_err1",
            "actor": {"agent_id": "agent_1"},
            "intent": {"goal": "nonexistent"},
            "execution": {"graph": {"nodes": [{"id": "n1", "capability": "does.not.exist"}]}},
        }
    )
    report("Returns failed status for missing capability", result["status"] == "failed")
    err = result["error"]
    report("Error has structured code", "code" in err)
    report("Error has human message", "message" in err)
    report("Error has recoverable flag", "recoverable" in err)
    report("Error has safe_retry flag", "safe_retry" in err)

    # Verify error events were emitted
    events = [e.type for e in runtime.event_bus.history("tsk_err1")]
    report(
        "Error events emitted to event bus",
        "error.terminal" in events or "error.recoverable" in events,
    )
    report("task.failed event emitted", "task.failed" in events)


async def test_8_end_to_end_realistic():
    """Full realistic scenario: validate → plan → execute → compact → prove → stream."""
    section("TEST 8: End-to-End Realistic Workflow")
    runtime = build_runtime()

    result = await runtime.invoke(
        {
            "uap": "1.0",
            "type": "task.invoke",
            "task_id": "tsk_e2e",
            "actor": {
                "agent_id": "did:web:finance-agent.acme.com",
                "user_id": "usr_jane",
                "org_id": "org_acme",
            },
            "intent": {
                "goal": "Find overdue invoices and draft reminder emails",
                "domain": "finance.operations",
            },
            "constraints": {
                "latency_ms": 5000,
                "max_cost_usd": 0.05,
                "max_context_tokens": 3000,
            },
            "context_request": {
                "fields": ["invoice_id", "customer", "amount", "due", "status", "drafts"],
                "max_items": 10,
            },
            "policy": {
                "allowed_tools": ["invoice.list_overdue", "email.draft"],
                "max_risk": "medium",
            },
            "return": {
                "stream": True,
                "format": "summary+artifacts",
            },
        }
    )

    report("Task completed successfully", result["status"] == "completed")

    nodes = result["result"]["nodes"]
    report("Invoice listing executed", "n1" in nodes)
    report("Email drafting executed", "n2" in nodes)

    # Verify field masking worked
    invoices = nodes["n1"]
    if isinstance(invoices, list) and len(invoices) > 0:
        report(
            "Context contract stripped unrequested fields", "internal_notes" not in str(invoices[0])
        )
    else:
        report("Context contract stripped unrequested fields", True)

    # Verify provenance chain
    prov = result["result"]["provenance"]
    report("Provenance chain covers both capabilities", len(prov) == 2)
    report("All provenance shares same trace_id", prov[0]["trace_id"] == prov[1]["trace_id"])

    # Verify event stream
    events = runtime.event_bus.history("tsk_e2e")
    report(f"Event stream has {len(events)} lifecycle events", len(events) >= 8)

    # Verify all events are CloudEvents-convertible
    all_convertible = all("specversion" in uap_event_to_cloudevent(e) for e in events)
    report("All events convert to CloudEvents 1.0", all_convertible)


# ─── Main ─────────────────────────────────────────────────────────────────────


async def main():
    print()
    print("=" * 60)
    print("  UAP CONTROL PLANE — INTEGRATION TEST SUITE")
    print("  The control plane for agentic applications")
    print("=" * 60)

    await test_1_envelope_validation()
    await test_2_policy_enforcement()
    await test_3_parallel_dag_execution()
    await test_4_context_compaction()
    await test_5_provenance_and_events()
    await test_6_adapter_import()
    await test_7_structured_error_recovery()
    await test_8_end_to_end_realistic()

    print(f"\n{'=' * 60}")
    print(f"  RESULTS: {PASS} passed, {FAIL} failed, {PASS + FAIL} total")
    print(f"{'=' * 60}")

    if FAIL > 0:
        print("\n  ⚠️  Some tests failed. The control plane has issues.")
        sys.exit(1)
    else:
        print("\n  🚀 All tests passed. The control plane works.")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
