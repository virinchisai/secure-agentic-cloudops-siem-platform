"""Tests for the rule-based triager."""

from app.triage import RuleBasedTriager, TriageResult


def _make_alert(label: str, score: float) -> dict:
    return {"alert_id": "test-001", "label": label, "score": score, "status": "new"}


def _make_event(severity: str = "high", source: str = "aws-guardduty", message: str = "", **extra) -> dict:
    return {
        "event_id": "evt-001",
        "severity": severity,
        "source": source,
        "message": message or f"Test event from {source}",
        "fields": extra,
    }


class TestRuleBasedTriager:
    def setup_method(self):
        self.triager = RuleBasedTriager()

    def test_brute_force_detection(self):
        alert = _make_alert("brute-force-login", 0.85)
        event = _make_event(message="Multiple failed SSH logins from 10.0.0.5")
        result = self.triager.triage(alert, event)

        assert isinstance(result, TriageResult)
        assert result.severity_assessment == "high"
        assert "Block source IP" in result.recommended_action
        assert 0.0 < result.confidence <= 1.0
        assert any("ip:10.0.0.5" in ioc for ioc in result.ioc_indicators)

    def test_privilege_escalation_is_critical(self):
        alert = _make_alert("privilege-escalation-attempt", 0.92)
        event = _make_event(severity="critical", source="osquery")
        result = self.triager.triage(alert, event)

        assert result.severity_assessment == "critical"
        assert "Isolate" in result.recommended_action

    def test_low_score_unknown_label(self):
        alert = _make_alert("misc-event", 0.2)
        event = _make_event(severity="info", source="cloudtrail")
        result = self.triager.triage(alert, event)

        assert result.severity_assessment == "low"
        assert result.confidence < 0.75

    def test_high_score_bumps_severity(self):
        alert = _make_alert("policy-violation", 0.95)
        event = _make_event(severity="medium", source="config-audit")
        result = self.triager.triage(alert, event)

        # policy-violation normally medium, but 0.95 score bumps to critical
        assert result.severity_assessment == "critical"

    def test_ioc_extraction_hashes(self):
        alert = _make_alert("malware-detected", 0.88)
        sha = "a" * 64
        event = _make_event(
            message=f"Malware hash detected: {sha}",
            file_hash=sha,
        )
        result = self.triager.triage(alert, event)

        assert any(sha in ioc for ioc in result.ioc_indicators)

    def test_to_dict(self):
        alert = _make_alert("suspicious-activity", 0.6)
        event = _make_event()
        result = self.triager.triage(alert, event)
        d = result.to_dict()

        assert isinstance(d, dict)
        assert set(d.keys()) == {
            "severity_assessment",
            "recommended_action",
            "confidence",
            "reasoning",
            "ioc_indicators",
        }
