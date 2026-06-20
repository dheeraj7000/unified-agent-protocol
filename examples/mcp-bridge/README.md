# UAP Model Context Protocol (MCP) Bridge Demo

This folder contains a demo bridging MCP tool descriptors to Unified Agent Protocol (UAP) capability cards.

## Purpose

The UAP MCP bridge allows existing MCP servers and tools to be registered under UAP governance. This adds policy checks, scopes, human-in-the-loop approvals, context compaction, and cryptographic provenance tracing to any existing MCP ecosystem.

## Files

- `demo.py`: Self-contained demo script defining 3 GitHub/docs-like MCP tools, converting them to UAP capability cards, registering them to `UAPRuntime`, and submitting a task.
- `README.md`: This file.

## Running the Demo

To run the demo:
```bash
python examples/mcp-bridge/demo.py
```
