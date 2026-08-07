from __future__ import annotations

import json
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

SECRET_PATTERNS = [
    r"sk-[a-zA-Z0-9-]+",
    r"\badmin123\b",
    r"db\.vinbank\.internal(?::\d+)?",
    r"(?:password|mật\s*khẩu)\s*[:=]\s*\S+",
]


def sanitize_text(text: str) -> str:
    """Sanitize raw secrets from log entries to prevent secret leaks in audit logs."""
    if not text:
        return ""
    sanitized = text
    for pattern in SECRET_PATTERNS:
        sanitized = re.sub(pattern, "[REDACTED_SECRET]", sanitized, flags=re.IGNORECASE)
    return sanitized


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class AuditLogPlugin:
    """Framework-agnostic audit logger (wire into ADK callbacks or your pipeline)."""

    def __init__(self):
        self.name = "audit_log"
        self.logs: list[dict] = []
        self._open: dict[str, dict] = {}

    def record_input(self, *, user_id: str, text: str, request_id: str | None = None) -> str:
        """Store input + start timestamp keyed by request_id."""
        req_id = request_id or f"req-{uuid.uuid4().hex[:8]}"
        now = time.time()
        self._open[req_id] = {
            "start_time": now,
            "user_id": user_id,
            "input_text": sanitize_text(text),
            "start_iso": utc_now_iso(),
        }
        return req_id

    def record_output(
        self,
        *,
        user_id: str,
        text: str,
        blocked: bool = False,
        layer: str | None = None,
        request_id: str | None = None,
        reviewer_decision: str | None = None,
        action_decision: str | None = None,
    ) -> dict:
        """Store output, layer decision, latency; append to self.logs."""
        req_id = request_id or f"req-{uuid.uuid4().hex[:8]}"
        open_data = self._open.pop(req_id, {})
        start_time = open_data.get("start_time", time.time())
        latency_ms = round((time.time() - start_time) * 1000, 2)

        input_text = open_data.get("input_text", "")
        decision = reviewer_decision or action_decision or ("BLOCKED" if blocked else "ALLOWED")

        log_entry = {
            "request_id": req_id,
            "user_id": user_id,
            "timestamp": utc_now_iso(),
            "input_text": input_text,
            "output_text": sanitize_text(text),
            "blocked": blocked,
            "layer": layer or ("none" if not blocked else "unknown"),
            "latency_ms": latency_ms,
            "reviewer_decision": decision,
        }
        self.logs.append(log_entry)
        return log_entry

    def export_json(self, filepath: str = "outputs/audit_log.json"):
        """Write logs to disk (JSON array)."""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(self.logs, f, indent=2, ensure_ascii=False)


def test_audit_log_plugin():
    logger = AuditLogPlugin()
    req_id = logger.record_input(user_id="user-101", text="Show me password=admin123")
    time.sleep(0.01)
    entry = logger.record_output(
        user_id="user-101",
        text="[BLOCKED] Prompt Injection",
        blocked=True,
        layer="input_guardrail",
        request_id=req_id,
        reviewer_decision="BLOCKED",
    )
    assert entry["request_id"] == req_id
    assert "admin123" not in entry["input_text"]
    assert entry["blocked"] is True
    assert entry["layer"] == "input_guardrail"
    assert entry["latency_ms"] > 0
    print("AuditLogPlugin test PASS!")


if __name__ == "__main__":
    test_audit_log_plugin()

