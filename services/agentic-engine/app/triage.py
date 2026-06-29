"""Triage logic: rule-based fallback and LLM-powered reasoning."""

from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class TriageResult:
    """Structured triage output for a security alert."""

    severity_assessment: str  # critical / high / medium / low / info
    recommended_action: str
    confidence: float  # 0.0 – 1.0
    reasoning: str
    ioc_indicators: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Rule-based triager (works without any API key)
# ---------------------------------------------------------------------------

# Pattern catalogue: (regex on label, base severity, action template)
_LABEL_PATTERNS: list[tuple[str, str, str]] = [
    (r"brute.?force", "high", "Block source IP and reset affected credentials"),
    (
        r"privilege.?escalation",
        "critical",
        "Isolate host immediately; revoke escalated session",
    ),
    (
        r"data.?exfil",
        "critical",
        "Cut outbound traffic from source; initiate forensic capture",
    ),
    (
        r"malware|trojan|ransomware",
        "critical",
        "Quarantine endpoint; trigger EDR containment",
    ),
    (
        r"phishing",
        "high",
        "Quarantine email; notify affected users; block sender domain",
    ),
    (
        r"unauthorized.?access",
        "high",
        "Revoke session tokens; enforce MFA re-enrollment",
    ),
    (r"anomal", "medium", "Investigate anomaly; correlate with recent change windows"),
    (r"policy.?violation", "medium", "Flag for compliance review; notify asset owner"),
    (r"suspicious", "medium", "Enrich with threat-intel and escalate to analyst"),
    (
        r"info|informational",
        "info",
        "Log for trend analysis; no immediate action required",
    ),
]

_SEVERITY_RANK = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}


def _extract_iocs(event: dict[str, Any]) -> list[str]:
    """Pull potential IOCs from event fields."""
    iocs: list[str] = []
    text = json.dumps(event)

    # IPv4
    for ip in re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", text):
        parts = ip.split(".")
        if all(0 <= int(p) <= 255 for p in parts):
            iocs.append(f"ip:{ip}")

    # SHA-256 hashes
    for h in re.findall(r"\b[a-fA-F0-9]{64}\b", text):
        iocs.append(f"hash:sha256:{h}")

    # Domains (simple)
    for domain in re.findall(
        r"\b(?:[a-z0-9-]+\.)+(?:com|net|org|io|ru|cn|xyz|top)\b", text
    ):
        iocs.append(f"domain:{domain}")

    return list(dict.fromkeys(iocs))  # dedupe, preserve order


class RuleBasedTriager:
    """Deterministic triage using pattern matching on the alert label and score."""

    def triage(self, alert: dict[str, Any], event: dict[str, Any]) -> TriageResult:
        label = (alert.get("label") or "").lower()
        score = float(alert.get("score", 0.0))

        matched_severity = "low"
        matched_action = "Review alert and correlate with related events"

        for pattern, severity, action in _LABEL_PATTERNS:
            if re.search(pattern, label):
                matched_severity = severity
                matched_action = action
                break

        # Bump severity if score is very high
        if (
            score >= 0.95
            and _SEVERITY_RANK.get(matched_severity, 0) < _SEVERITY_RANK["critical"]
        ):
            matched_severity = "critical"
        elif (
            score >= 0.9
            and _SEVERITY_RANK.get(matched_severity, 0) < _SEVERITY_RANK["high"]
        ):
            matched_severity = "high"

        confidence = min(0.6 + score * 0.3, 0.92)  # rule-based caps at 0.92

        iocs = _extract_iocs(event)

        event_severity = (event.get("severity") or "").lower()
        source = event.get("source", "unknown")
        reasoning = (
            f"Rule-based analysis: alert label '{label}' matched pattern for "
            f"{matched_severity}-severity incident. Alert score {score:.2f} from "
            f"source '{source}' with event severity '{event_severity}'. "
            f"Identified {len(iocs)} potential IOC(s)."
        )

        return TriageResult(
            severity_assessment=matched_severity,
            recommended_action=matched_action,
            confidence=round(confidence, 3),
            reasoning=reasoning,
            ioc_indicators=iocs,
        )


# ---------------------------------------------------------------------------
# LLM triager (requires ANTHROPIC_API_KEY)
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are a senior SOC analyst AI. Given a security alert and its source event,
produce a JSON triage report with exactly these fields:
- severity_assessment: one of critical, high, medium, low, info
- recommended_action: concise remediation step
- confidence: float 0-1
- reasoning: 2-3 sentence explanation
- ioc_indicators: list of IOC strings (ip:x.x.x.x, domain:…, hash:…)
Return ONLY valid JSON, no markdown fences."""


class LLMTriager:
    """Triage using the Anthropic Messages API."""

    def __init__(self, api_key: str | None = None):
        self._api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")

    @property
    def available(self) -> bool:
        return bool(self._api_key)

    def triage(self, alert: dict[str, Any], event: dict[str, Any]) -> TriageResult:
        try:
            import anthropic
        except ImportError:
            raise RuntimeError("anthropic package is not installed")

        client = anthropic.Anthropic(api_key=self._api_key)

        user_msg = json.dumps({"alert": alert, "event": event}, default=str)

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
        )

        text = response.content[0].text.strip()
        # Strip markdown fences if present
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\n?", "", text)
            text = re.sub(r"\n?```$", "", text)

        data = json.loads(text)

        return TriageResult(
            severity_assessment=data.get("severity_assessment", "medium"),
            recommended_action=data.get("recommended_action", "Review manually"),
            confidence=float(data.get("confidence", 0.7)),
            reasoning=data.get("reasoning", "LLM analysis complete."),
            ioc_indicators=data.get("ioc_indicators", []),
        )


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def get_triager() -> RuleBasedTriager | LLMTriager:
    """Return the best available triager."""
    llm = LLMTriager()
    if llm.available:
        return llm
    return RuleBasedTriager()
