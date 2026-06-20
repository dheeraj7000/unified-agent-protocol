import asyncio

from uap import UAPRuntime
from uap.adapters.mcp import mcp_tools_to_capabilities


async def main():
    # 1. Define 3 MCP tools
    mcp_tools = [
        {
            "name": "search_docs",
            "description": "Search documentation for keywords",
            "inputSchema": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
        {
            "name": "create_issue",
            "description": "Create a new issue in a repository",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "repo": {"type": "string"},
                    "title": {"type": "string"},
                    "body": {"type": "string"},
                },
                "required": ["repo", "title"],
            },
        },
        {
            "name": "list_repos",
            "description": "List repositories for an organization",
            "inputSchema": {
                "type": "object",
                "properties": {"org": {"type": "string"}},
                "required": ["org"],
            },
        },
    ]

    # 2. Convert MCP tools to UAP Capability Cards
    cards = mcp_tools_to_capabilities(mcp_tools, server_name="github")

    # 3. Create UAPRuntime and register the capabilities
    runtime = UAPRuntime()

    def handle_search_docs(input_value, envelope):
        return {"results": ["found match"]}

    def handle_create_issue(input_value, envelope):
        return {"issue_id": 42, "url": "http://github.com/issues/42"}

    def handle_list_repos(input_value, envelope):
        return {"repos": ["uap-reference", "mcp-bridge"]}

    handlers = {
        "github.search_docs": handle_search_docs,
        "github.create_issue": handle_create_issue,
        "github.list_repos": handle_list_repos,
    }

    for card in cards:
        runtime.registry.register(card, handlers[card.capability_id])

    # 4. Submit task with intent goal: "list repositories"
    payload = {
        "uap": "1.0",
        "type": "task.invoke",
        "task_id": "tsk_mcp_bridge",
        "actor": {"agent_id": "agent_mcp", "scopes": ["mcp.github.list_repos"]},
        "intent": {"goal": "list repositories", "parameters": {"org": "uap-dev"}},
        "policy": {"allowed_tools": ["github.list_repos"]},
    }

    result = await runtime.invoke(payload)

    # Print results and provenance records
    print(f"Task status: {result['status']}")
    print(f"Task output nodes: {result['result']['nodes']}")

    provenance_list = result["result"]["provenance"]
    for prov in provenance_list:
        print(f"Provenance record: capability_id: {prov['capability_id']}")
        print(f"  input_digest: {prov['input_digest']}")
        print(f"  output_digest: {prov['output_digest']}")


if __name__ == "__main__":
    asyncio.run(main())
