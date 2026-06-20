from __future__ import annotations

import json
from typing import Any

from .errors import UAPError
from .models import (
    SUPPORTED_UAP_VERSIONS,
    UAP_FEATURES,
    UAP_RUNTIME_VERSION,
    CapabilityCard,
)
from .policy import PolicyEngine
from .runtime import UAPRuntime

runtime = UAPRuntime(policy_engine=PolicyEngine(strict_permissions=False))


# Demo capabilities for local server mode.
def _register_demo_capabilities() -> None:
    if runtime.registry.list_cards():
        return

    def invoice_list_overdue(input_value: dict[str, Any], envelope):
        return [
            {
                "invoice_id": "INV-1001",
                "customer": "Acme",
                "amount": 1200,
                "due_date": "2026-05-01",
            },
            {
                "invoice_id": "INV-1002",
                "customer": "Globex",
                "amount": 840,
                "due_date": "2026-05-12",
            },
        ]

    def email_draft(input_value: dict[str, Any], envelope):
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
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.responses import StreamingResponse
except Exception:  # pragma: no cover
    FastAPI = None
    HTTPException = Exception
    Request = None
    StreamingResponse = None


if FastAPI:
    app = FastAPI(title="UAP — The Control Plane for Agentic Applications", version="0.1.0")

    @app.get("/health")
    async def health():
        return {
            "status": "ok",
            "protocol": "uap",
            "version": "0.1",
            "uap_version": UAP_RUNTIME_VERSION,
        }

    @app.get("/uap/capabilities")
    async def list_capabilities():
        return {"capabilities": [card.to_dict() for card in runtime.registry.list_cards()]}

    @app.post("/uap/tasks")
    async def invoke_task(payload: dict[str, Any]):
        return await runtime.invoke(payload)

    @app.get("/uap/tasks/{task_id}")
    async def get_task(task_id: str):
        if task_id not in runtime.tasks:
            raise HTTPException(status_code=404, detail="task not found")
        return {"task_id": task_id, **runtime.tasks[task_id]}

    @app.get("/uap/version")
    async def get_version():
        return {
            "protocol": "uap",
            "version": UAP_RUNTIME_VERSION,
            "supported_versions": sorted(list(SUPPORTED_UAP_VERSIONS)),
            "features": UAP_FEATURES,
        }

    @app.post("/uap/tasks/{task_id}/approve")
    async def approve_task(task_id: str, payload: dict[str, Any]):
        approver_id = payload.get("approver_id")
        if not approver_id:
            raise HTTPException(status_code=400, detail="Missing approver_id")
        try:
            return await runtime.resume_after_approval(task_id, approver_id)
        except UAPError as exc:
            if exc.code == "TASK_NOT_FOUND":
                raise HTTPException(status_code=404, detail=exc.message)
            raise HTTPException(status_code=400, detail=exc.message)

    @app.delete("/uap/tasks/{task_id}")
    async def cancel_task(task_id: str):
        if not runtime.cancel(task_id):
            raise HTTPException(status_code=404, detail="task not found")
        return {"task_id": task_id, "status": "cancelled"}

    @app.get("/uap/tasks/{task_id}/events")
    async def stream_events(task_id: str, request: Request):
        last_id = request.headers.get("last-event-id")

        async def generate():
            skip = last_id is not None
            async for event in runtime.event_bus.subscribe(task_id):
                if skip:
                    if event.event_id == last_id:
                        skip = False
                    continue
                yield f"id: {event.event_id}\n"
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
