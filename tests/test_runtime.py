import asyncio
import unittest

from uap import CapabilityCard, UAPRuntime


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
                }
            }
        }
        result = asyncio.run(runtime.invoke(payload))
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["result"]["nodes"]["n1"], {"step": 1})
        self.assertEqual(result["result"]["nodes"]["n2"], {"step": 2, "from_step1": 1})


if __name__ == "__main__":
    unittest.main()
