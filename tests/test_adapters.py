import unittest

from uap.adapters.mcp import mcp_tool_to_capability
from uap.adapters.openapi import openapi_to_capabilities


class AdapterTest(unittest.TestCase):
    def test_openapi_adapter(self):
        spec = {"paths": {"/x": {"get": {"operationId": "x.get", "summary": "Get X"}}}}
        cards = openapi_to_capabilities(spec)
        self.assertEqual(cards[0].capability_id, "x.get")
        self.assertEqual(cards[0].risk, "low")

    def test_mcp_adapter(self):
        card = mcp_tool_to_capability({"name": "search", "description": "Search docs"}, "docs")
        self.assertEqual(card.capability_id, "docs.search")
        self.assertIn("mcp", card.tags)

    def test_openapi_adapter_complex_parsing(self):
        spec = {
            "paths": {
                "/users/{id}": {
                    "post": {
                        "operationId": "create_user",
                        "summary": "Create user summary",
                        "description": "Create user description",
                        "parameters": [
                            {
                                "name": "id",
                                "in": "path",
                                "required": True,
                                "schema": {"type": "string"},
                            },
                            {
                                "name": "debug",
                                "in": "query",
                                "required": False,
                                "schema": {"type": "boolean"},
                            },
                        ],
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "name": {"type": "string"},
                                            "email": {"type": "string"},
                                        },
                                        "required": ["name"],
                                    }
                                }
                            },
                        },
                        "responses": {
                            "201": {
                                "description": "Created",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {"status": {"type": "string"}},
                                        }
                                    }
                                },
                            }
                        },
                        "x-uap": {
                            "capability_id": "user.create",
                            "risk": {
                                "level": "critical",
                                "side_effect": True,
                            },
                            "tags": ["user", "admin"],
                            "context_cost": {"max_tokens": 100},
                        },
                    }
                }
            }
        }
        cards = openapi_to_capabilities(spec)
        self.assertEqual(len(cards), 1)
        card = cards[0]
        self.assertEqual(card.capability_id, "user.create")
        self.assertEqual(card.risk, "critical")
        self.assertTrue(card.requires_approval)
        self.assertEqual(card.context_cost, {"max_tokens": 100})
        self.assertIn("user", card.tags)
        self.assertIn("admin", card.tags)

        # Check input schema properties
        self.assertEqual(card.input_schema["properties"]["id"], {"type": "string"})
        self.assertEqual(card.input_schema["properties"]["debug"], {"type": "boolean"})
        self.assertEqual(card.input_schema["properties"]["name"], {"type": "string"})
        self.assertEqual(card.input_schema["properties"]["email"], {"type": "string"})
        self.assertEqual(card.input_schema["required"], ["id", "name"])

        # Check output schema properties
        self.assertEqual(card.output_schema["properties"]["status"], {"type": "string"})

    def test_cloudevent_adapter(self):
        from uap.adapters.cloudevents import uap_event_to_cloudevent
        from uap.models import UAPEvent

        event = UAPEvent(
            type="task.completed", task_id="tsk_123", data={"ok": True}, trace_id="trc_789"
        )
        ce = uap_event_to_cloudevent(event)
        self.assertEqual(ce["specversion"], "1.0")
        self.assertEqual(ce["id"], event.event_id)
        self.assertEqual(ce["source"], "/uap/tasks/tsk_123")
        self.assertEqual(ce["type"], "dev.uap.event.task.completed")
        self.assertEqual(ce["datacontenttype"], "application/json")
        self.assertEqual(ce["data"], {"ok": True})
        self.assertEqual(ce["traceid"], "trc_789")


if __name__ == "__main__":
    unittest.main()
