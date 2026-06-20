from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from uap.adapters.openapi import openapi_to_capabilities  # noqa: E402

spec = {
    "openapi": "3.1.0",
    "info": {"title": "Invoices", "version": "1.0"},
    "paths": {
        "/invoices/overdue": {
            "get": {
                "operationId": "invoice.list_overdue",
                "summary": "List overdue invoices",
                "tags": ["finance", "invoice"],
            }
        }
    },
}

cards = openapi_to_capabilities(spec)
print(json.dumps([card.to_dict() for card in cards], indent=2))
