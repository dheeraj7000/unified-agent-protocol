from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from uap import CapabilityCard, UAPRuntime  # noqa: E402


def build_runtime() -> UAPRuntime:
    runtime = UAPRuntime()

    def invoice_list_overdue(input_value, envelope):
        return [
            {
                "invoice_id": "INV-1001",
                "customer": "Acme",
                "amount": 1200,
                "due_date": "2026-05-01",
                "notes": "ignored by field mask",
            },
            {
                "invoice_id": "INV-1002",
                "customer": "Globex",
                "amount": 840,
                "due_date": "2026-05-12",
                "notes": "ignored by field mask",
            },
        ]

    def email_draft(input_value, envelope):
        return {
            "drafts": [
                {
                    "to": "billing@example.com",
                    "subject": "Payment reminder",
                    "body": "Please review the overdue invoice list.",
                }
            ],
            "internal_debug": "removed by field mask",
        }

    runtime.registry.register(
        CapabilityCard(
            capability_id="invoice.list_overdue",
            purpose="Find overdue invoices",
            input_schema={"type": "object"},
            output_schema={"type": "array"},
            risk="medium",
            permissions=["invoice.read"],
            tags=["invoice", "finance", "overdue"],
            context_cost={"typical_tokens": 400, "max_tokens": 2000},
        ),
        invoice_list_overdue,
    )
    runtime.registry.register(
        CapabilityCard(
            capability_id="email.draft",
            purpose="Create email drafts",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            risk="medium",
            permissions=["email.draft"],
            tags=["email", "draft"],
        ),
        email_draft,
    )
    return runtime


async def main() -> None:
    runtime = build_runtime()
    payload = json.loads((ROOT / "examples" / "task_invoke.json").read_text())
    result = await runtime.invoke(payload)
    print(json.dumps(result, indent=2))
    print("\nEvents:")
    for event in runtime.event_bus.history(payload["task_id"]):
        print(json.dumps(event.to_dict(), indent=2))


if __name__ == "__main__":
    asyncio.run(main())
