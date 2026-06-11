"""
Lab 11 — Part 4: Human-in-the-Loop Design
  TODO 12: Confidence Router
  TODO 13: Design 3 HITL decision points
"""


# ============================================================
# TODO 12: Implement ConfidenceRouter
#
# Route responses based on confidence score and action type.
# ============================================================

class ConfidenceRouter:
    """Route agent responses based on confidence and risk level."""

    # High-risk actions -> always need human approval
    HIGH_RISK_ACTIONS = [
        "transfer_money", "delete_account", "send_email",
        "change_password", "update_personal_info"
    ]

    def __init__(self, high_threshold=0.9, low_threshold=0.7):
        self.high_threshold = high_threshold
        self.low_threshold = low_threshold
        self.routing_log = []

    def route(self, response: str, confidence: float, action_type: str = "general") -> dict:
        """Route response to appropriate handler.

        Args:
            response: The agent's response text
            confidence: Confidence score (0.0 to 1.0)
            action_type: Type of action (e.g., 'general', 'transfer_money')

        Returns:
            dict with 'action' (auto_send/queue_review/escalate),
                      'hitl_model', and 'reason'
        """
        # 1. High-risk action -> always escalate (human makes the final call)
        if action_type in self.HIGH_RISK_ACTIONS:
            result = {
                "action": "escalate",
                "hitl_model": "Human-as-tiebreaker",
                "reason": f"High-risk action '{action_type}' always requires human approval",
            }
        # 2. High confidence -> auto-send, human reviews after
        elif confidence >= self.high_threshold:
            result = {
                "action": "auto_send",
                "hitl_model": "Human-on-the-loop",
                "reason": f"High confidence ({confidence:.2f}) — auto-send, human monitors",
            }
        # 3. Medium confidence -> queue for human approval before sending
        elif confidence >= self.low_threshold:
            result = {
                "action": "queue_review",
                "hitl_model": "Human-in-the-loop",
                "reason": f"Medium confidence ({confidence:.2f}) — needs review before sending",
            }
        # 4. Low confidence -> escalate to a human immediately
        else:
            result = {
                "action": "escalate",
                "hitl_model": "Human-as-tiebreaker",
                "reason": f"Low confidence ({confidence:.2f}) — escalating to human",
            }

        result["confidence"] = confidence
        result["action_type"] = action_type
        self.routing_log.append(result)
        return result


# ============================================================
# TODO 13: Design 3 HITL Decision Points
#
# Fill in 3 decision points for the VinBank agent.
# ============================================================

hitl_decision_points = [
    {
        "id": 1,
        "scenario": "Customer requests a large or unusual outbound money transfer",
        "trigger": "Transfer amount > 50,000,000 VND, OR a first-time / international beneficiary",
        "hitl_model": "Human-in-the-loop",
        "context_for_human": "Source balance, recent transaction history, beneficiary details, fraud-risk score, customer's stated reason",
        "expected_response_time": "< 5 minutes (customer is waiting in-session)",
    },
    {
        "id": 2,
        "scenario": "Agent gives loan/investment advice but is uncertain",
        "trigger": "Confidence score < 0.7, OR question involves regulated financial advice",
        "hitl_model": "Human-as-tiebreaker",
        "context_for_human": "Full user question, agent's draft answer, confidence score, any policy docs referenced",
        "expected_response_time": "< 30 minutes (can fall back to 'a specialist will call you')",
    },
    {
        "id": 3,
        "scenario": "Account security change under suspicious conditions",
        "trigger": "Password reset / contact-info change combined with new device or unusual login location",
        "hitl_model": "Human-on-the-loop",
        "context_for_human": "Account ID, recent login/device history, requested change, verification steps already passed",
        "expected_response_time": "Near real-time monitoring; analyst can intervene/revert within minutes",
    },
]


# ============================================================
# Quick tests
# ============================================================

def test_confidence_router():
    """Test ConfidenceRouter with sample scenarios."""
    router = ConfidenceRouter()

    test_scenarios = [
        ("Interest rate is 5.5%", 0.95, "general"),
        ("I'll transfer 10M VND", 0.85, "transfer_money"),
        ("Rate is probably around 4-6%", 0.75, "general"),
        ("I'm not sure about this info", 0.5, "general"),
    ]

    print("Testing ConfidenceRouter:")
    print(f"{'Response':<35} {'Conf':<6} {'Action Type':<18} {'Route':<15} {'HITL Model'}")
    print("-" * 100)
    for resp, conf, action in test_scenarios:
        result = router.route(resp, conf, action)
        print(f"{resp:<35} {conf:<6.2f} {action:<18} {result['action']:<15} {result['hitl_model']}")


def test_hitl_points():
    """Display HITL decision points."""
    print("HITL Decision Points:")
    print("=" * 60)
    for dp in hitl_decision_points:
        print(f"\n--- Decision Point #{dp['id']} ---")
        for key, value in dp.items():
            if key != "id":
                print(f"  {key}: {value}")


if __name__ == "__main__":
    test_confidence_router()
    test_hitl_points()
