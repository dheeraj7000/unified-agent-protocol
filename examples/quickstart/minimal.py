import asyncio

from uap import CapabilityCard, UAPRuntime


async def main():
    runtime = UAPRuntime()

    def greet_hello(input_value, envelope):
        return {"message": "Hello, UAP!", "version": "0.1"}

    runtime.registry.register(
        CapabilityCard(
            capability_id="greet.hello",
            purpose="Greet the user",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            risk="low",
            tags=["greet"],
        ),
        greet_hello,
    )

    payload = {
        "uap": "1.0",
        "type": "task.invoke",
        "task_id": "tsk_quickstart",
        "actor": {"agent_id": "agent_quickstart"},
        "intent": {"goal": "hello"},
        "policy": {"allowed_tools": ["greet.hello"]},
    }

    result = await runtime.invoke(payload)
    events = [event.type for event in runtime.event_bus.history(result["task_id"])]
    events_str = " → ".join(events)
    nodes = result.get("result", {}).get("nodes", {})
    output_val = nodes.get("n1", {})
    print(
        f"Task {result['task_id']} {result['status']} · result: {output_val} · events: {events_str}"
    )


if __name__ == "__main__":
    asyncio.run(main())
