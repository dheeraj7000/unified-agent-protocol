# UAP Specification v0.1 - Context Contract

The context contract defines how outputs from capability executions are filtered, compacted, and budgeted:
- **Field Masking**: If `context_request.fields` is specified, the runtime MUST strip any unrequested fields from objects/dicts.
- **Item Limits**: If `context_request.max_items` is specified, lists/arrays MUST be truncated to that length. A truncation marker showing the number of omitted items SHOULD be appended.
- **Token Budgeting**: Output values MUST fit within the `constraints.max_context_tokens` limit. If the limit is exceeded, a text summary or truncation MUST be performed.
