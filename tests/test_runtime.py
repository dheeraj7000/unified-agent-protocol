import asyncio
import time
import unittest

from uap import (
    Actor,
    CapabilityCard,
    Intent,
    Policy,
    PolicyEngine,
    TaskEnvelope,
    UAPRuntime,
)
from uap.errors import PolicyDeniedError


class RuntimeTest(unittest.TestCase):
    def test_runtime_executes_task(self):
        runtime = UAPRuntime()

        def hello(input_value, envelope):
            return {"message": "hello", "extra": "remove"}

        runtime.registry.register(
            CapabilityCard(
                capability_id="hello.say",
                purpose="Say hello",
                input_schema={"type": "object"},
                output_schema={"type": "object"},
                risk="low",
                tags=["hello"],
            ),
            hello,
        )
        payload = {
            "uap": "1.0",
            "type": "task.invoke",
            "task_id": "tsk_test",
            "actor": {"agent_id": "agent"},
            "intent": {"goal": "hello"},
            "context_request": {"fields": ["message"], "max_items": 5},
            "policy": {"allowed_tools": ["hello.say"], "max_risk": "low"},
        }
        result = asyncio.run(runtime.invoke(payload))
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["result"]["nodes"]["n1"], {"message": "hello"})
        events = [event.type for event in runtime.event_bus.history("tsk_test")]
        self.assertIn("task.completed", events)

    def test_validation_error_on_invoke(self):
        runtime = UAPRuntime()
        invalid_payload = {
            "uap": "1.0",
            "type": "task.invoke",
            "task_id": "tsk_invalid",
        }
        result = asyncio.run(runtime.invoke(invalid_payload))
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error"]["code"], "INVALID_ENVELOPE")

        events = [event.type for event in runtime.event_bus.history("tsk_invalid")]
        self.assertIn("error.terminal", events)
        self.assertIn("task.failed", events)

    def test_custom_graph_execution(self):
        runtime = UAPRuntime()

        def step1(input_value, envelope):
            return {"step": 1}

        def step2(input_value, envelope):
            prev = input_value.get("previous_results", {})
            return {"step": 2, "from_step1": prev.get("n1", {}).get("step")}

        runtime.registry.register(
            CapabilityCard("step1", "Step 1", {}, {}, risk="low"),
            step1,
        )
        runtime.registry.register(
            CapabilityCard("step2", "Step 2", {}, {}, risk="low"),
            step2,
        )

        payload = {
            "uap": "1.0",
            "type": "task.invoke",
            "task_id": "tsk_custom_graph",
            "actor": {"agent_id": "agent"},
            "intent": {"goal": "run custom graph"},
            "execution": {
                "parallelism": 2,
                "graph": {
                    "nodes": [
                        {"id": "n1", "capability": "step1"},
                        {"id": "n2", "capability": "step2", "depends_on": ["n1"]},
                    ]
                },
            },
        }
        result = asyncio.run(runtime.invoke(payload))
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["result"]["nodes"]["n1"], {"step": 1})
        self.assertEqual(result["result"]["nodes"]["n2"], {"step": 2, "from_step1": 1})

    def test_version_negotiation_unsupported(self):
        runtime = UAPRuntime()
        payload = {
            "uap": "99.0",
            "type": "task.invoke",
            "task_id": "tsk_unsupported",
            "actor": {"agent_id": "agent"},
            "intent": {"goal": "hello"},
        }
        result = asyncio.run(runtime.invoke(payload))
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error"]["code"], "UNSUPPORTED_VERSION")

    def test_dag_cycle_detection(self):
        runtime = UAPRuntime()
        payload = {
            "uap": "1.0",
            "type": "task.invoke",
            "task_id": "tsk_cycle",
            "actor": {"agent_id": "agent"},
            "intent": {"goal": "run cycle graph"},
            "execution": {
                "graph": {
                    "nodes": [
                        {"id": "n1", "capability": "c1", "depends_on": ["n2"]},
                        {"id": "n2", "capability": "c2", "depends_on": ["n1"]},
                    ]
                }
            },
        }
        result = asyncio.run(runtime.invoke(payload))
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error"]["code"], "PLAN_GRAPH_CYCLE")

    def test_dag_missing_dependency(self):
        runtime = UAPRuntime()
        payload = {
            "uap": "1.0",
            "type": "task.invoke",
            "task_id": "tsk_missing_dep",
            "actor": {"agent_id": "agent"},
            "intent": {"goal": "run graph with missing dep"},
            "execution": {
                "graph": {
                    "nodes": [
                        {"id": "n1", "capability": "c1", "depends_on": ["n_nonexistent"]},
                    ]
                }
            },
        }
        result = asyncio.run(runtime.invoke(payload))
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error"]["code"], "PLAN_MISSING_DEPENDENCY")

    def test_node_timeout(self):
        runtime = UAPRuntime()

        def slow_say(input_value, envelope):
            time.sleep(0.5)
            return {"message": "slow hello"}

        runtime.registry.register(
            CapabilityCard(
                capability_id="slow.say",
                purpose="Slow say",
                input_schema={},
                output_schema={},
                risk="low",
            ),
            slow_say,
        )
        payload = {
            "uap": "1.0",
            "type": "task.invoke",
            "task_id": "tsk_timeout",
            "actor": {"agent_id": "agent"},
            "intent": {"goal": "hello"},
            "constraints": {"node_timeout_ms": 10},
            "policy": {"allowed_tools": ["slow.say"]},
        }
        result = asyncio.run(runtime.invoke(payload))
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error"]["code"], "CAPABILITY_TIMEOUT")

    def test_approval_lifecycle_resume(self):
        runtime = UAPRuntime()

        def approval_tool(input_value, envelope):
            return {"status": "ok"}

        runtime.registry.register(
            CapabilityCard(
                capability_id="approve.tool",
                purpose="Tool that requires approval",
                input_schema={},
                output_schema={},
                risk="low",
                requires_approval=True,
            ),
            approval_tool,
        )
        payload = {
            "uap": "1.0",
            "type": "task.invoke",
            "task_id": "tsk_approve",
            "actor": {"agent_id": "agent"},
            "intent": {"goal": "hello"},
            "policy": {"allowed_tools": ["approve.tool"]},
        }
        result = asyncio.run(runtime.invoke(payload))
        self.assertEqual(result["status"], "waiting_for_approval")
        self.assertEqual(result["error"]["code"], "APPROVAL_REQUIRED")

        resume_result = asyncio.run(runtime.resume_after_approval("tsk_approve", "admin_approver"))
        self.assertEqual(resume_result["status"], "completed")
        self.assertEqual(resume_result["result"]["nodes"]["n1"], {"status": "ok"})

    def test_strict_scopes(self):
        pe_permissive = PolicyEngine(strict_scopes=False)
        envelope = TaskEnvelope(
            actor=Actor(agent_id="agent", scopes=[]),
            intent=Intent(goal="test"),
            policy=Policy(allowed_tools=["t"]),
        )
        card = CapabilityCard("t", "T", {}, {}, risk="low", permissions=["t.read"])
        pe_permissive.check(envelope, card)

        pe_strict = PolicyEngine(strict_scopes=True)
        with self.assertRaises(PolicyDeniedError) as ctx:
            pe_strict.check(envelope, card)
        self.assertEqual(ctx.exception.code, "MISSING_PERMISSION")


if __name__ == "__main__":
    unittest.main()


# cache_bust = 1
