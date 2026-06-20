import unittest

from uap.errors import ApprovalRequiredError, PolicyDeniedError
from uap.models import Actor, CapabilityCard, Intent, Policy, TaskEnvelope
from uap.policy import PolicyEngine


class PolicyEngineTest(unittest.TestCase):
    def test_denies_unallowed_tool(self):
        envelope = TaskEnvelope(
            actor=Actor(agent_id="a"),
            intent=Intent(goal="test"),
            policy=Policy(allowed_tools=["x"]),
        )
        card = CapabilityCard("y", "Y", {}, {}, risk="low")
        with self.assertRaises(PolicyDeniedError):
            PolicyEngine().check(envelope, card)

    def test_requires_approval(self):
        envelope = TaskEnvelope(actor=Actor(agent_id="a"), intent=Intent(goal="test"))
        card = CapabilityCard("send", "Send", {}, {}, risk="medium", requires_approval=True)
        with self.assertRaises(ApprovalRequiredError):
            PolicyEngine().check(envelope, card)

    def test_denies_unallowed_tool_suggests_alternatives(self):
        from uap.capabilities import CapabilityRegistry

        registry = CapabilityRegistry()
        card_allowed = CapabilityCard(
            "allowed_tool", "Allowed Tool", {}, {}, risk="low", tags=["email"]
        )
        card_denied = CapabilityCard(
            "denied_tool", "Denied Tool", {}, {}, risk="low", tags=["email"]
        )
        registry.register(card_allowed, lambda x, e: None)
        registry.register(card_denied, lambda x, e: None)

        envelope = TaskEnvelope(
            actor=Actor(agent_id="a"),
            intent=Intent(goal="test"),
            policy=Policy(allowed_tools=["allowed_tool"]),
        )
        with self.assertRaises(PolicyDeniedError) as context:
            PolicyEngine().check(envelope, card_denied, registry)
        self.assertEqual(context.exception.code, "TOOL_NOT_ALLOWED")
        self.assertIn("allowed_tool", context.exception.alternative_capabilities)

    def test_risk_exceeded_suggests_alternatives(self):
        from uap.capabilities import CapabilityRegistry

        registry = CapabilityRegistry()
        card_low = CapabilityCard(
            "low_risk_tool", "Low Risk Tool", {}, {}, risk="low", tags=["email"]
        )
        card_high = CapabilityCard(
            "high_risk_tool", "High Risk Tool", {}, {}, risk="high", tags=["email"]
        )
        registry.register(card_low, lambda x, e: None)
        registry.register(card_high, lambda x, e: None)

        envelope = TaskEnvelope(
            actor=Actor(agent_id="a"),
            intent=Intent(goal="test"),
            policy=Policy(max_risk="medium"),
        )
        with self.assertRaises(PolicyDeniedError) as context:
            PolicyEngine().check(envelope, card_high, registry)
        self.assertEqual(context.exception.code, "RISK_EXCEEDS_POLICY")
        self.assertIn("low_risk_tool", context.exception.alternative_capabilities)

    def test_strict_permissions(self):
        pe_permissive = PolicyEngine(strict_permissions=False)
        envelope = TaskEnvelope(
            actor=Actor(agent_id="agent", scopes=[]),
            intent=Intent(goal="test"),
            policy=Policy(allowed_tools=["t"]),
        )
        card = CapabilityCard("t", "T", {}, {}, risk="low", permissions=["t.read"])
        # Should not raise PolicyDeniedError under permissive mode
        pe_permissive.check(envelope, card)

        pe_strict = PolicyEngine(strict_permissions=True)
        with self.assertRaises(PolicyDeniedError) as ctx:
            pe_strict.check(envelope, card)
        self.assertEqual(ctx.exception.code, "MISSING_PERMISSION")


if __name__ == "__main__":
    unittest.main()
