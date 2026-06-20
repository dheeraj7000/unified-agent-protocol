from __future__ import annotations

import asyncio
import json
from typing import Any, Dict

from .models import CapabilityCard
from .runtime import UAPRuntime

runtime = UAPRuntime()

# Demo capabilities for local server mode.
def _register_demo_capabilities() -> None:
    if runtime.registry.list_cards():
        return

    def invoice_list_overdue(input_value: Dict[str, Any], envelope):
        return [
            {"invoice_id": "INV-1001", "customer": "Acme", "amount": 1200, "due_date": "2026-05-01"},
            {"invoice_id": "INV-1002", "customer": "Globex", "amount": 840, "due_date": "2026-05-12"},
        ]

    def email_draft(input_value: Dict[str, Any], envelope):
        invoices = input_value.get("previous_results", {})
        return {
            "drafts": [
                {
                    "to": "billing@example.com",
                    "subject": "Payment reminder",
                    "body": "Please review the overdue invoice list.",
                    "source": invoices,
                }
            ]
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
            requires_approval=False,
            tags=["email", "draft"],
        ),
        email_draft,
    )


_register_demo_capabilities()

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import StreamingResponse
except Exception:  # pragma: no cover
    FastAPI = None
    HTTPException = Exception
    StreamingResponse = None


if FastAPI:
    app = FastAPI(title="UAP — The Control Plane for Agentic Applications", version="0.1.0")

    @app.get("/health")
    async def health():
        return {"status": "ok", "protocol": "uap", "version": "0.1"}

    @app.get("/uap/capabilities")
    async def list_capabilities():
        return {"capabilities": [card.to_dict() for card in runtime.registry.list_cards()]}

    @app.post("/uap/tasks")
    async def invoke_task(payload: Dict[str, Any]):
        return await runtime.invoke(payload)

    @app.get("/uap/tasks/{task_id}")
    async def get_task(task_id: str):
        if task_id not in runtime.tasks:
            raise HTTPException(status_code=404, detail="task not found")
        return runtime.tasks[task_id]

    @app.get("/uap/tasks/{task_id}/events")
    async def stream_events(task_id: str):
        async def generate():
            async for event in runtime.event_bus.subscribe(task_id):
                yield f"event: {event.type}\n"
                yield "data: " + json.dumps(event.to_dict()) + "\n\n"
        return StreamingResponse(generate(), media_type="text/event-stream")
else:
    app = None


def main() -> None:
    if not FastAPI:
        raise SystemExit("Install server dependencies: pip install -e '.[server]'")
    import uvicorn

    uvicorn.run("uap.server:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    main()
