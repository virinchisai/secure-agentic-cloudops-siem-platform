from dataclasses import dataclass


@dataclass
class DetectionResult:
    score: float
    label: str
    rule_name: str


def rule_severity_check(event: dict) -> DetectionResult | None:
    sev = (event.get("severity") or "").lower()
    if sev in {"high", "critical"}:
        return DetectionResult(
            score=0.95 if sev == "critical" else 0.85,
            label="high_severity_event",
            rule_name="severity_check",
        )
    return None


def rule_brute_force(event: dict) -> DetectionResult | None:
    msg = (event.get("message") or "").lower()
    log_type = (event.get("log_type") or "").lower()
    if log_type == "authentication" and any(
        kw in msg
        for kw in ["failed login", "invalid password", "brute force", "account locked"]
    ):
        return DetectionResult(
            score=0.90, label="brute_force_attempt", rule_name="brute_force"
        )
    return None


def rule_privilege_escalation(event: dict) -> DetectionResult | None:
    msg = (event.get("message") or "").lower()
    fields = event.get("fields", {})
    if any(
        kw in msg
        for kw in ["privilege escalation", "sudo", "role changed to admin", "elevated"]
    ):
        return DetectionResult(
            score=0.92, label="privilege_escalation", rule_name="privilege_escalation"
        )
    action = str(fields.get("action", "")).lower()
    if action in {"role_change", "permission_grant"} and "admin" in msg:
        return DetectionResult(
            score=0.88, label="privilege_escalation", rule_name="privilege_escalation"
        )
    return None


def rule_data_exfiltration(event: dict) -> DetectionResult | None:
    msg = (event.get("message") or "").lower()
    fields = event.get("fields", {})
    bytes_out = fields.get("bytes_transferred", 0)
    if any(kw in msg for kw in ["large download", "data export", "bulk extract"]):
        return DetectionResult(
            score=0.87, label="data_exfiltration_risk", rule_name="data_exfiltration"
        )
    if isinstance(bytes_out, (int, float)) and bytes_out > 100_000_000:
        return DetectionResult(
            score=0.80, label="data_exfiltration_risk", rule_name="data_exfiltration"
        )
    return None


def rule_suspicious_network(event: dict) -> DetectionResult | None:
    fields = event.get("fields", {})
    log_type = (event.get("log_type") or "").lower()
    if log_type != "network":
        return None
    dst = str(fields.get("destination", ""))
    port = fields.get("port", 0)
    if port in {4444, 5555, 1337, 31337}:
        return DetectionResult(
            score=0.93, label="suspicious_network_activity", rule_name="suspicious_port"
        )
    if any(kw in dst for kw in ["tor", "onion", "proxy"]):
        return DetectionResult(
            score=0.91,
            label="suspicious_network_activity",
            rule_name="suspicious_destination",
        )
    return None


ALL_RULES = [
    rule_severity_check,
    rule_brute_force,
    rule_privilege_escalation,
    rule_data_exfiltration,
    rule_suspicious_network,
]


def evaluate(event: dict) -> DetectionResult:
    best = DetectionResult(score=0.30, label="informational", rule_name="default")
    for rule_fn in ALL_RULES:
        result = rule_fn(event)
        if result and result.score > best.score:
            best = result
    return best
