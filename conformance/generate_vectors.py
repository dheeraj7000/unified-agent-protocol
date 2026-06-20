import json
import os

vectors = {
    "01_valid_minimal.json": {
        "name": "01_valid_minimal",
        "description": "Minimal valid envelope that runs invoice.list_overdue",
        "input": {
            "uap": "1.0",
            "type": "task.invoke",
            "task_id": "tsk_01",
            "actor": {"agent_id": "agent_01"},
            "intent": {"goal": "list overdue invoices"},
            "policy": {"allowed_tools": ["invoice.list_overdue"]}
        },
        "expect": {"status": "completed"}
    },
    "02_valid_full.json": {
        "name": "02_valid_full",
        "description": "Full valid envelope that runs invoice.list_overdue and email.draft",
        "input": {
            "uap": "1.0",
            "type": "task.invoke",
            "task_id": "tsk_02",
            "actor": {
                "agent_id": "agent_02",
                "user_id": "user_123",
                "org_id": "org_abc",
                "service_id": "service_xyz",
                "delegation_token": "token_123",
                "scopes": ["invoice.read", "email.draft"]
            },
            "intent": {
                "goal": "list overdue invoices and draft emails",
                "domain": "billing",
                "parameters": {"limit": 5}
            },
            "constraints": {
                "latency_ms": 5000,
                "max_cost_usd": 1.5,
                "max_context_tokens": 4000,
                "risk_level": "medium"
            },
            "context_request": {
                "detail": "standard",
                "fields": ["invoice_id", "drafts"],
                "evidence_required": True,
                "max_items": 10,
                "max_tokens": 2000
            },
            "policy": {
                "allowed_tools": ["invoice.list_overdue", "email.draft"],
                "max_risk": "medium"
            }
        },
        "expect": {"status": "completed"}
    },
    "03_missing_actor.json": {
        "name": "03_missing_actor",
        "description": "Envelope missing actor field",
        "input": {
            "uap": "1.0",
            "type": "task.invoke",
            "task_id": "tsk_03",
            "intent": {"goal": "list overdue invoices"}
        },
        "expect": {
            "status": "failed",
            "error.code": "INVALID_ENVELOPE"
        }
    },
    "04_missing_intent_goal.json": {
        "name": "04_missing_intent_goal",
        "description": "Envelope missing intent.goal",
        "input": {
            "uap": "1.0",
            "type": "task.invoke",
            "task_id": "tsk_04",
            "actor": {"agent_id": "agent_04"},
            "intent": {}
        },
        "expect": {
            "status": "failed",
            "error.code": "INVALID_INTENT"
        }
    },
    "05_actor_no_agent_id.json": {
        "name": "05_actor_no_agent_id",
        "description": "Envelope where actor lacks agent_id",
        "input": {
            "uap": "1.0",
            "type": "task.invoke",
            "task_id": "tsk_05",
            "actor": {},
            "intent": {"goal": "list overdue invoices"}
        },
        "expect": {
            "status": "failed",
            "error.code": "INVALID_ACTOR"
        }
    },
    "06_tool_denied.json": {
        "name": "06_tool_denied",
        "description": "Envelope where target tool is denied by policy",
        "input": {
            "uap": "1.0",
            "type": "task.invoke",
            "task_id": "tsk_06",
            "actor": {"agent_id": "agent_06"},
            "intent": {"goal": "list overdue invoices"},
            "policy": {
                "denied_tools": ["invoice.list_overdue"]
            }
        },
        "expect": {
            "status": "failed",
            "error.code": "TOOL_DENIED"
        }
    },
    "07_tool_not_allowed.json": {
        "name": "07_tool_not_allowed",
        "description": "Envelope where target tool is not in allowed_tools list",
        "input": {
            "uap": "1.0",
            "type": "task.invoke",
            "task_id": "tsk_07",
            "actor": {"agent_id": "agent_07"},
            "intent": {"goal": "list overdue invoices"},
            "policy": {
                "allowed_tools": ["email.draft"]
            }
        },
        "expect": {
            "status": "failed",
            "error.code": "TOOL_NOT_ALLOWED"
        }
    },
    "08_risk_too_high.json": {
        "name": "08_risk_too_high",
        "description": "Envelope where tool risk exceeds policy max_risk",
        "input": {
            "uap": "1.0",
            "type": "task.invoke",
            "task_id": "tsk_08",
            "actor": {"agent_id": "agent_08"},
            "intent": {"goal": "list overdue invoices"},
            "policy": {
                "max_risk": "low"
            }
        },
        "expect": {
            "status": "failed",
            "error.code": "RISK_EXCEEDS_POLICY"
        }
    },
    "09_approval_required.json": {
        "name": "09_approval_required",
        "description": "Envelope targeting a tool requiring approval",
        "input": {
            "uap": "1.0",
            "type": "task.invoke",
            "task_id": "tsk_09",
            "actor": {"agent_id": "agent_09"},
            "intent": {"goal": "list overdue invoices"},
            "policy": {
                "requires_approval": ["invoice.list_overdue"]
            }
        },
        "expect": {
            "status": "waiting_for_approval",
            "error.code": "APPROVAL_REQUIRED"
        }
    },
    "10_dag_chain.json": {
        "name": "10_dag_chain",
        "description": "Valid execution graph representing a DAG chain",
        "input": {
            "uap": "1.0",
            "type": "task.invoke",
            "task_id": "tsk_10",
            "actor": {"agent_id": "agent_10"},
            "intent": {"goal": "run chain"},
            "execution": {
                "graph": {
                    "nodes": [
                        {"id": "n1", "capability": "invoice.list_overdue"},
                        {"id": "n2", "capability": "email.draft", "depends_on": ["n1"]}
                    ]
                }
            }
        },
        "expect": {"status": "completed"}
    },
    "11_field_masking.json": {
        "name": "11_field_masking",
        "description": "Valid envelope requesting field masking in context request",
        "input": {
            "uap": "1.0",
            "type": "task.invoke",
            "task_id": "tsk_11",
            "actor": {"agent_id": "agent_11"},
            "intent": {"goal": "list overdue invoices"},
            "context_request": {
                "fields": ["invoice_id"]
            }
        },
        "expect": {"status": "completed"}
    },
    "12_event_ordering.json": {
        "name": "12_event_ordering",
        "description": "Valid envelope to test correct lifecycle event ordering",
        "input": {
            "uap": "1.0",
            "type": "task.invoke",
            "task_id": "tsk_12",
            "actor": {"agent_id": "agent_12"},
            "intent": {"goal": "list overdue invoices"},
            "policy": {
                "allowed_tools": ["invoice.list_overdue"]
            }
        },
        "expect": {"status": "completed"}
    },
    "13_unsupported_version.json": {
        "name": "13_unsupported_version",
        "description": "Envelope sending unsupported UAP version 99.0",
        "input": {
            "uap": "99.0",
            "type": "task.invoke",
            "task_id": "tsk_13",
            "actor": {"agent_id": "agent_13"},
            "intent": {"goal": "list overdue invoices"}
        },
        "expect": {
            "status": "failed",
            "error.code": "UNSUPPORTED_VERSION"
        }
    },
    "14_empty_graph.json": {
        "name": "14_empty_graph",
        "description": "Envelope with empty graph nodes",
        "input": {
            "uap": "1.0",
            "type": "task.invoke",
            "task_id": "tsk_14",
            "actor": {"agent_id": "agent_14"},
            "intent": {"goal": "list overdue invoices"},
            "execution": {
                "graph": {
                    "nodes": []
                }
            }
        },
        "expect": {
            "status": "completed"
        }
    }
}

os.makedirs("conformance/test-vectors", exist_ok=True)
for filename, data in vectors.items():
    with open(f"conformance/test-vectors/{filename}", "w") as f:
        json.dump(data, f, indent=2)
print("Vectors generated successfully!")
