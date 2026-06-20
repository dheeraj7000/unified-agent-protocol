# UAP Specification v0.1 - Errors

The following table details the standard UAP error taxonomy. Compliant runtimes MUST use these specific code strings, recoverable flags, and safe retry values.

| Error Code | Description | Recoverable | Safe Retry |
| :--- | :--- | :---: | :---: |
| `INVALID_ENVELOPE` | Syntax or type error in task envelope | True | False |
| `INVALID_ACTOR` | Actor identity fields are invalid | True | False |
| `INVALID_INTENT` | Intent or goal is missing or invalid | True | False |
| `INVALID_CONSTRAINTS` | Invalid constraints parameters | True | False |
| `INVALID_CONTEXT_REQUEST` | Invalid context request details | True | False |
| `INVALID_POLICY` | Invalid policy definitions | True | False |
| `INVALID_EXECUTION` | Invalid execution parameters | True | False |
| `INVALID_EXECUTION_GRAPH` | Mismatch or invalid properties in DAG | True | False |
| `INVALID_RETURN` | Invalid return specifications | True | False |
| `TOOL_NOT_ALLOWED` | Capability blocked by policy `allowed_tools` | True | False |
| `TOOL_DENIED` | Capability blocked by policy `denied_tools` | False | False |
| `RISK_EXCEEDS_POLICY` | Risk level exceeds `max_risk` | True | False |
| `MISSING_PERMISSION` | Actor lacks capability scope permissions | True | False |
| `APPROVAL_REQUIRED` | Triggered gate awaiting human response | True | False |
| `TASK_CANCELLED` | Execution was cancelled by client request | False | False |
| `CAPABILITY_TIMEOUT` | Capability execution exceeded latency limit | True | True |
| `PLAN_GRAPH_CYCLE` | Execution graph contains a cycle dependency | False | False |
| `PLAN_MISSING_DEPENDENCY` | Node references a missing dependency | False | False |
| `UNHANDLED_ERROR` | Internal server execution error | False | False |
| `UNSUPPORTED_VERSION` | UAP version in envelope is not supported | False | False |
| `TASK_NOT_FOUND` | Task ID is unknown or has expired | False | False |
