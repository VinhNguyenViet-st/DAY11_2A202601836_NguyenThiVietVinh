"""
Assignment 11 — Monitoring & Alerts starter (TODO).

Tracks block rate, rate-limit hits, judge fail rate.
Fires alerts when thresholds are exceeded.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Alert:
    metric: str
    value: float
    threshold: float
    message: str


@dataclass
class MonitoringAlert:
    """Aggregate counters from pipeline plugins and emit alerts."""

    block_rate_threshold: float = 0.5
    rate_limit_hit_threshold: int = 5
    judge_fail_rate_threshold: float = 0.3
    alerts: list[Alert] = field(default_factory=list)

    # Counters — update these from your pipeline after each request
    total_requests: int = 0
    blocked_requests: int = 0
    rate_limit_hits: int = 0
    judge_checks: int = 0
    judge_fails: int = 0

    def check_metrics(self) -> list[Alert]:
        """Compute rates, append Alert objects when thresholds exceeded."""
        self.alerts.clear()

        # 1. Block rate check
        if self.total_requests > 0:
            block_rate = self.blocked_requests / self.total_requests
            if block_rate >= self.block_rate_threshold:
                self.alerts.append(
                    Alert(
                        metric="block_rate",
                        value=round(block_rate, 4),
                        threshold=self.block_rate_threshold,
                        message=f"High block rate detected: {block_rate:.2%} (threshold: {self.block_rate_threshold:.2%})",
                    )
                )

        # 2. Rate limit hits check
        if self.rate_limit_hits >= self.rate_limit_hit_threshold:
            self.alerts.append(
                Alert(
                    metric="rate_limit_hits",
                    value=float(self.rate_limit_hits),
                    threshold=float(self.rate_limit_hit_threshold),
                    message=f"Rate limit hit threshold exceeded: {self.rate_limit_hits} hits (threshold: {self.rate_limit_hit_threshold})",
                )
            )

        # 3. Judge fail rate check
        if self.judge_checks > 0:
            judge_fail_rate = self.judge_fails / self.judge_checks
            if judge_fail_rate >= self.judge_fail_rate_threshold:
                self.alerts.append(
                    Alert(
                        metric="judge_fail_rate",
                        value=round(judge_fail_rate, 4),
                        threshold=self.judge_fail_rate_threshold,
                        message=f"LLM-as-Judge fail rate exceeded: {judge_fail_rate:.2%} (threshold: {self.judge_fail_rate_threshold:.2%})",
                    )
                )

        return self.alerts

    def export_json(self, filepath: str = "outputs/metrics.json"):
        """Write metrics + alerts to JSON."""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = self.snapshot()
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def snapshot(self) -> dict:
        block_rate = (
            self.blocked_requests / self.total_requests
            if self.total_requests
            else 0.0
        )
        judge_fail_rate = (
            self.judge_fails / self.judge_checks if self.judge_checks else 0.0
        )
        return {
            "total_requests": self.total_requests,
            "blocked_requests": self.blocked_requests,
            "block_rate": block_rate,
            "rate_limit_hits": self.rate_limit_hits,
            "judge_checks": self.judge_checks,
            "judge_fails": self.judge_fails,
            "judge_fail_rate": judge_fail_rate,
            "alerts": [
                {
                    "metric": a.metric,
                    "value": a.value,
                    "threshold": a.threshold,
                    "message": a.message,
                }
                for a in self.alerts
            ],
        }


def test_monitoring_simulation():
    """Simulate a traffic spike and verify alerts."""
    mon = MonitoringAlert(
        block_rate_threshold=0.30,
        rate_limit_hit_threshold=5,
        judge_fail_rate_threshold=0.20,
    )

    # Simulate 10 requests: 5 blocked, 6 rate limit hits, 4 judge checks with 2 fails
    mon.total_requests = 10
    mon.blocked_requests = 5
    mon.rate_limit_hits = 6
    mon.judge_checks = 4
    mon.judge_fails = 2

    alerts = mon.check_metrics()
    snap = mon.snapshot()

    print("Simulated Incident Metrics Snapshot:")
    print(json.dumps(snap, indent=2))
    assert len(alerts) == 3, f"Expected 3 alerts, got {len(alerts)}"
    print(f"\nAll 3 alerts successfully triggered: {[a.metric for a in alerts]}")


if __name__ == "__main__":
    import json
    test_monitoring_simulation()
