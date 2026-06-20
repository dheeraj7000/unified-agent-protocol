# UAP Specification v0.1 - Capability Card

Capability cards define the capabilities available to the agent.
Each card MUST conform to the schema:
- `capability_id` (string, required): Unique identifier for the capability.
- `purpose` (string, required): A brief description of what the tool does.
- `input_schema` (object, required): A JSON schema defining inputs.
- `output_schema` (object, required): A JSON schema defining outputs.
- `risk` (enum[low, medium, high, critical], default: low): Risk categorization.
- `permissions` (array of string): Security permissions required by the actor to run this tool.
- `requires_approval` (boolean): If true, execution always requires an approval gate.
- `idempotent` (boolean, default: true): Indicates if execution is idempotent.
- `latency_p50_ms` and `latency_p95_ms` (integer): Expected execution latencies.
- `transport` (object): Metadata detailing the execution adapter/binding.
