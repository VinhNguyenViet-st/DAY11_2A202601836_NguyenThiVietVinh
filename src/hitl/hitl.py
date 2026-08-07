"""
Lab 11 — Part 4: Human-in-the-Loop Design
  TODO 11: Confidence Router
  TODO 12: Design 3 HITL decision points
"""
from dataclasses import dataclass


# ============================================================
# TODO 11: Implement ConfidenceRouter
#
# Route agent responses based on confidence scores:
#   - HIGH (>= 0.9): Auto-send to user
#   - MEDIUM (0.7 - 0.9): Queue for human review
#   - LOW (< 0.7): Escalate to human immediately
#
# Special case: if the action is HIGH_RISK (e.g., money transfer,
# account deletion), ALWAYS escalate regardless of confidence.
#
# Implement the route() method.
# ============================================================

HIGH_RISK_ACTIONS = [
    "transfer_money",
    "close_account",
    "change_password",
    "delete_data",
    "update_personal_info",
]


@dataclass
class RoutingDecision:
    """Result of the confidence router."""
    action: str          # "auto_send", "queue_review", "escalate"
    confidence: float
    reason: str
    priority: str        # "low", "normal", "high"
    requires_human: bool


class ConfidenceRouter:
    """Route agent responses based on confidence and risk level.

    Thresholds:
        HIGH:   confidence >= 0.9 -> auto-send
        MEDIUM: 0.7 <= confidence < 0.9 -> queue for review
        LOW:    confidence < 0.7 -> escalate to human

    High-risk actions always escalate regardless of confidence.
    """

    HIGH_THRESHOLD = 0.9
    MEDIUM_THRESHOLD = 0.7

    def route(self, response: str, confidence: float,
              action_type: str = "general") -> RoutingDecision:
        """Route a response based on confidence score and action type.

        Args:
            response: The agent's response text
            confidence: Confidence score between 0.0 and 1.0
            action_type: Type of action (e.g., "general", "transfer_money")

        Returns:
            RoutingDecision with routing action and metadata
        """
        # 1. High-risk actions always escalate regardless of confidence
        if action_type in HIGH_RISK_ACTIONS:
            return RoutingDecision(
                action="escalate",
                confidence=confidence,
                reason=f"High-risk action: {action_type}",
                priority="high",
                requires_human=True,
            )

        # 2. Check confidence thresholds for ordinary actions
        if confidence >= self.HIGH_THRESHOLD:
            return RoutingDecision(
                action="auto_send",
                confidence=confidence,
                reason="High confidence",
                priority="low",
                requires_human=False,
            )
        elif confidence >= self.MEDIUM_THRESHOLD:
            return RoutingDecision(
                action="queue_review",
                confidence=confidence,
                reason="Medium confidence — needs review",
                priority="normal",
                requires_human=True,
            )
        else:
            return RoutingDecision(
                action="escalate",
                confidence=confidence,
                reason="Low confidence — escalating",
                priority="high",
                requires_human=True,
            )


# ============================================================
# TODO 12: Design 3 HITL decision points + a review lifecycle
# ============================================================

hitl_decision_points = [
    {
        "id": 1,
        "name": "Chuyển tiền sang tài khoản thụ hưởng mới hoặc hạn mức cao",
        "trigger": "Hành động `transfer_money` khi số tiền vượt mức 50,000,000 VND hoặc chuyển tới người thụ hưởng chưa từng giao dịch trong 30 ngày.",
        "hitl_model": "human-in-the-loop (bắt buộc người duyệt xác nhận trước khi thực thi lệnh egress API)",
        "context_needed": "Diff thông tin thụ hưởng (STK cũ vs STK mới, tên chủ tài khoản), số tiền giao dịch, mã OTP/Xác thực sinh trắc học, tín hiệu bất thường (địa chỉ IP lạ, thiết bị mới).",
        "example": "Khách hàng yêu cầu chuyển 100,000,000 VND từ tài khoản tiết kiệm tới STK 999888777 tại ngân hàng khác.",
        "approval_path": "Approve: Ký mã HITL-XXXX và gọi API egress chuyển tiền. Reject: Hủy giao dịch, gửi thông báo cảnh báo bảo mật. Timeout (quá 5 phút): Tự động REJECT/HOLD giao dịch, tuyệt đối không tự động gửi tiền.",
        "audit_fields": "request_id (UUID), intent ('transfer_money'), proposed_action_diff (from_account, to_account, amount), reviewer_id, reviewer_decision ('APPROVE'/'REJECT'/'TIMEOUT_HOLD'), audit_layer ('HITLGateway'), timestamp (ISO8601).",
    },
    {
        "id": 2,
        "name": "Đóng tài khoản hoặc thay đổi mật khẩu/thông tin định danh",
        "trigger": "Hành động nguy cơ cao (`close_account`, `change_password`, `update_personal_info`) phát sinh qua chatbot.",
        "hitl_model": "human-in-the-loop (bắt buộc nhân viên kiểm tra hồ sơ và xác thực người dùng)",
        "context_needed": "Yêu cầu gốc của khách hàng, bản diff thông tin thay đổi (ví dụ: SĐT/Email cũ vs mới, mật khẩu mới), hình ảnh CCCD/định danh đính kèm, trạng thái xác thực 2FA.",
        "example": "Khách hàng gửi yêu cầu qua bot: 'Tôi muốn đóng tài khoản và chuyển toàn bộ số dư còn lại sang ngân hàng khác'.",
        "approval_path": "Approve: Cấp mã xác nhận HITL để tiếp tục workflow đóng tài khoản/đổi pass. Reject: Từ chối và yêu cầu khách hàng ra chi nhánh gần nhất. Timeout (quá 10 phút): Tự động REJECT và tạm khóa tính năng thay đổi qua bot.",
        "audit_fields": "request_id (UUID), intent ('close_account'/'change_password'), customer_id, proposed_diff, reviewer_id, reviewer_decision ('APPROVE'/'REJECT'/'TIMEOUT'), audit_layer ('HITLGateway'), timestamp (ISO8601).",
    },
    {
        "id": 3,
        "name": "Kiểm duyệt phản hồi trả lời khách hàng có độ tin cậy trung bình (Medium Confidence)",
        "trigger": "ConfidenceRouter xếp loại `queue_review` khi 0.70 <= confidence < 0.90 hoặc khi truy vấn RAG/Email ngoài chứa nội dung phức tạp.",
        "hitl_model": "human-on-the-loop (người duyệt kiểm tra phản hồi trước khi gửi tới người dùng)",
        "context_needed": "Câu hỏi của khách hàng, dự thảo phản hồi từ LLM, nguồn RAG/Email trích dẫn, điểm confidence score, danh sách từ khóa nguy cơ.",
        "example": "Khách hàng hỏi: 'Điều khoản phạt trả nợ trước hạn gói vay thế chấp của tôi quy định như thế nào?'. LLM đạt confidence 0.82.",
        "approval_path": "Approve: Cho phép phát hành phản hồi. Edit & Approve: Reviewer chỉnh sửa trực tiếp rồi gửi. Reject: Hủy phản hồi và chuyển câu hỏi cho tư vấn viên. Timeout (quá 3 phút): Chuyển sang hàng chờ tư vấn viên trực tiếp (Human Escalation), KHÔNG gửi phản hồi nghi ngờ cho khách.",
        "audit_fields": "request_id (UUID), intent ('general_inquiry'), llm_response_draft, confidence_score, reviewer_id, reviewer_decision ('APPROVE'/'EDITED'/'REJECT'/'TIMEOUT_ESCALATE'), audit_layer ('ConfidenceRouter'), timestamp (ISO8601).",
    },
]


# ============================================================
# Quick tests
# ============================================================

def test_confidence_router():
    """Test ConfidenceRouter with sample scenarios."""
    router = ConfidenceRouter()

    test_cases = [
        ("Balance inquiry", 0.95, "general"),
        ("Interest rate question", 0.82, "general"),
        ("Ambiguous request", 0.55, "general"),
        ("Transfer $50,000", 0.98, "transfer_money"),
        ("Close my account", 0.91, "close_account"),
    ]

    print("Testing ConfidenceRouter:")
    print("=" * 80)
    print(f"{'Scenario':<25} {'Conf':<6} {'Action Type':<18} {'Decision':<15} {'Priority':<10} {'Human?'}")
    print("-" * 80)

    for scenario, conf, action_type in test_cases:
        decision = router.route(scenario, conf, action_type)
        print(
            f"{scenario:<25} {conf:<6.2f} {action_type:<18} "
            f"{decision.action:<15} {decision.priority:<10} "
            f"{'Yes' if decision.requires_human else 'No'}"
        )

    print("=" * 80)


def test_hitl_points():
    """Display HITL decision points."""
    print("\nHITL Decision Points:")
    print("=" * 60)
    for point in hitl_decision_points:
        print(f"\n  Decision Point #{point['id']}: {point['name']}")
        print(f"    Trigger:  {point['trigger']}")
        print(f"    Model:    {point['hitl_model']}")
        print(f"    Context:  {point['context_needed']}")
        print(f"    Example:  {point['example']}")
    print("\n" + "=" * 60)


if __name__ == "__main__":
    test_confidence_router()
    test_hitl_points()
