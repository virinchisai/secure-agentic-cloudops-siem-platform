from app.rules import (
    evaluate,
    rule_brute_force,
    rule_data_exfiltration,
    rule_privilege_escalation,
    rule_severity_check,
    rule_suspicious_network,
)


def test_severity_critical():
    event = {"severity": "critical", "message": "test"}
    result = rule_severity_check(event)
    assert result is not None
    assert result.score == 0.95
    assert result.label == "high_severity_event"


def test_severity_high():
    result = rule_severity_check({"severity": "high"})
    assert result is not None
    assert result.score == 0.85


def test_severity_low_returns_none():
    assert rule_severity_check({"severity": "low"}) is None


def test_brute_force_detection():
    event = {
        "log_type": "authentication",
        "message": "Failed login from 198.51.100.42",
        "severity": "high",
    }
    result = rule_brute_force(event)
    assert result is not None
    assert result.label == "brute_force_attempt"


def test_brute_force_wrong_log_type():
    event = {
        "log_type": "network",
        "message": "Failed login from 198.51.100.42",
        "severity": "high",
    }
    assert rule_brute_force(event) is None


def test_privilege_escalation():
    event = {
        "message": "User role changed to admin",
        "severity": "critical",
        "fields": {"action": "role_change"},
    }
    result = rule_privilege_escalation(event)
    assert result is not None
    assert result.label == "privilege_escalation"


def test_data_exfiltration_by_keyword():
    event = {
        "message": "Large download detected",
        "severity": "high",
        "fields": {},
    }
    result = rule_data_exfiltration(event)
    assert result is not None
    assert result.label == "data_exfiltration_risk"


def test_data_exfiltration_by_bytes():
    event = {
        "message": "File transfer complete",
        "severity": "medium",
        "fields": {"bytes_transferred": 200_000_000},
    }
    result = rule_data_exfiltration(event)
    assert result is not None
    assert result.score == 0.80


def test_suspicious_port():
    event = {
        "log_type": "network",
        "message": "Outbound connection",
        "fields": {"destination": "1.2.3.4", "port": 4444},
    }
    result = rule_suspicious_network(event)
    assert result is not None
    assert result.label == "suspicious_network_activity"


def test_suspicious_tor_destination():
    event = {
        "log_type": "network",
        "message": "DNS query",
        "fields": {"destination": "tor-exit-node"},
    }
    result = rule_suspicious_network(event)
    assert result is not None


def test_evaluate_picks_highest_score():
    event = {
        "severity": "critical",
        "log_type": "authentication",
        "message": "Failed login brute force",
        "fields": {},
    }
    result = evaluate(event)
    assert result.score == 0.95


def test_evaluate_low_severity_info():
    event = {
        "severity": "info",
        "log_type": "application",
        "message": "Health check passed",
        "fields": {},
    }
    result = evaluate(event)
    assert result.label == "informational"
    assert result.score == 0.30
