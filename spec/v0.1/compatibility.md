# UAP Specification v0.1 - Compatibility

1. **Version Format**: UAP uses semantic versioning format (`MAJOR.MINOR`).
2. **Unknown Field Handling**: The runtime MUST preserve unknown top-level metadata fields or custom fields in the envelope.
3. **Breaking Change Definition**: A change is considered breaking if it removes required fields, adds new required fields, or changes the expected response structure.
4. **Client Version Semantics**: Client requests include version strings. Servers MUST validate capability versions against supported versions, raising `UNSUPPORTED_VERSION` on unsupported versions.
