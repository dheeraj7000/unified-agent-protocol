from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Delegation:
    subject: str
    actor: str
    scopes: list[str] = field(default_factory=list)
    audience: str | None = None
    expires_at: str | None = None

    def allows(self, scope: str) -> bool:
        return scope in self.scopes or "*" in self.scopes


class DelegationVerifier:
    """Placeholder for OAuth/DPoP/DID-backed verification.

    Production implementations should verify signatures, token audiences,
    expirations, nonces, and revocation status.
    """

    def verify(self, token: str | None) -> bool:
        return bool(token is None or token.strip())
