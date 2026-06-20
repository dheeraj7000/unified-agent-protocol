# UAP Specification v0.1 - Policy

A UAP runtime MUST enforce policies before executing any capability. The evaluation order is strictly defined and MUST follow this sequence:

1. **Allowed Tools**: Validate that the capability ID is allowed by `allowed_tools` if specified.
2. **Denied Tools**: Validate that the capability ID is not in `denied_tools`.
3. **Risk Level**: Validate that the capability's risk does not exceed the allowed `max_risk`.
4. **Scope Check**: Check that the actor scopes cover the required permissions of the capability.
5. **Approval Gate**: Trigger an approval gate if the capability or task requires human consent.

The runtime MUST apply all five validation checks in this exact order before invoking any capability.
