# UAP Specification v0.1 - Task Graph

1. A task execution graph MUST NOT contain any cycles. If a cycle is detected, the runtime MUST fail the task and raise `PLAN_GRAPH_CYCLE`.
2. A runtime MUST reject graphs where `depends_on` references a node ID not present in the graph, raising `PLAN_MISSING_DEPENDENCY`.
3. Independent nodes in the graph (those whose dependencies are already completed) SHOULD be executed concurrently, up to the limits specified by `execution.parallelism`.
