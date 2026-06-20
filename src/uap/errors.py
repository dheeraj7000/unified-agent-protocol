from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class UAPError(Exception):
    code: str
    message: str
    recoverable: bool = False
    safe_retry: bool = False
    retry_after_ms: Optional[int] = None
    alternative_capabilities: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "code": self.code,
            "message": self.message,
            "recoverable": self.recoverable,
            "safe_retry": self.safe_retry,
        }
        if self.retry_after_ms is not None:
            result["retry_after_ms"] = self.retry_after_ms
        if self.alternative_capabilities:
            result["alternative_capabilities"] = self.alternative_capabilities
        if self.details:
            result["details"] = self.details
        return result


class ValidationError(UAPError):
    pass


class PolicyDeniedError(UAPError):
    pass


class ApprovalRequiredError(UAPError):
    pass


class CapabilityNotFoundError(UAPError):
    pass
