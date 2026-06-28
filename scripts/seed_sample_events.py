"""Seed the SIEM platform with realistic sample security events."""

import time

import requests

INGEST_URL = "http://127.0.0.1:8001/ingest"

SAMPLE_EVENTS = [
    {
        "source": "vpn-gateway",
        "log_type": "authentication",
        "severity": "high",
        "message": "Failed login attempt from unknown IP — possible brute force",
        "fields": {"src_ip": "198.51.100.42", "user": "admin", "attempts": 15},
    },
    {
        "source": "vpn-gateway",
        "log_type": "authentication",
        "severity": "critical",
        "message": "Account locked after repeated failed login attempts",
        "fields": {"src_ip": "198.51.100.42", "user": "admin", "lockout_duration": 900},
    },
    {
        "source": "iam-service",
        "log_type": "authorization",
        "severity": "critical",
        "message": "User role changed to admin — privilege escalation detected",
        "fields": {"user": "jdoe", "old_role": "viewer", "new_role": "admin", "action": "role_change"},
    },
    {
        "source": "firewall",
        "log_type": "network",
        "severity": "high",
        "message": "Outbound connection to suspicious destination on port 4444",
        "fields": {"src_ip": "10.0.1.55", "destination": "evil.example.com", "port": 4444, "protocol": "tcp"},
    },
    {
        "source": "dlp-agent",
        "log_type": "data_access",
        "severity": "high",
        "message": "Large download detected — potential data exfiltration",
        "fields": {"user": "contractor_bob", "bytes_transferred": 250_000_000, "file_count": 1420},
    },
    {
        "source": "web-app",
        "log_type": "application",
        "severity": "medium",
        "message": "SQL injection pattern detected in request parameter",
        "fields": {"path": "/api/users", "parameter": "id", "pattern": "' OR 1=1 --"},
    },
    {
        "source": "cloud-trail",
        "log_type": "cloud",
        "severity": "high",
        "message": "S3 bucket policy changed to public access",
        "fields": {"bucket": "prod-backups", "actor": "deploy-bot", "region": "us-east-1"},
    },
    {
        "source": "endpoint-agent",
        "log_type": "endpoint",
        "severity": "critical",
        "message": "Malware signature detected — trojan.generic",
        "fields": {"hostname": "ws-042", "file": "/tmp/.hidden/payload.exe", "hash": "a1b2c3d4e5f6"},
    },
    {
        "source": "dns-proxy",
        "log_type": "network",
        "severity": "medium",
        "message": "DNS query to known tor exit node relay",
        "fields": {"query": "exit-relay.tor.example.com", "destination": "tor-exit", "src_ip": "10.0.2.99"},
    },
    {
        "source": "sso-provider",
        "log_type": "authentication",
        "severity": "info",
        "message": "Successful login from known device",
        "fields": {"user": "alice", "device": "MacBook-Pro-Alice", "mfa": True},
    },
    {
        "source": "load-balancer",
        "log_type": "network",
        "severity": "low",
        "message": "Health check passed for backend pool",
        "fields": {"pool": "api-servers", "healthy": 4, "total": 4},
    },
    {
        "source": "k8s-audit",
        "log_type": "cloud",
        "severity": "high",
        "message": "Pod created with elevated privileges — sudo container detected",
        "fields": {"namespace": "production", "pod": "debug-shell-xz9", "privileged": True},
    },
]


def main():
    print(f"Seeding {len(SAMPLE_EVENTS)} events to {INGEST_URL}")
    print()

    succeeded = 0
    for i, event in enumerate(SAMPLE_EVENTS, 1):
        try:
            r = requests.post(INGEST_URL, json=event, timeout=5)
            data = r.json()
            status = "OK" if r.status_code in (200, 202) else "FAIL"
            print(f"  [{i:>2}/{len(SAMPLE_EVENTS)}] {status} {event['source']:>16} | {event['severity']:<8} | {data.get('event_id', 'n/a')}")
            if r.status_code in (200, 202):
                succeeded += 1
        except Exception as e:
            print(f"  [{i:>2}/{len(SAMPLE_EVENTS)}] ERROR {event['source']:>16} | {e}")

    print()
    print(f"Sent {succeeded}/{len(SAMPLE_EVENTS)} events successfully.")

    print()
    print("Waiting 3s for detection pipeline to process...")
    time.sleep(3)

    for url in ["http://127.0.0.1:8001/health", "http://127.0.0.1:8002/health"]:
        try:
            r = requests.get(url, timeout=3)
            print(f"  {url} => {r.json()}")
        except Exception as e:
            print(f"  {url} => ERROR {e}")

    try:
        r = requests.get("http://127.0.0.1:8002/stats", timeout=5)
        stats = r.json()
        print()
        print(f"Stats: {stats['total_events']} events, {stats['total_alerts']} alerts")
        for item in stats.get("alerts_by_label", []):
            print(f"  {item['label']}: {item['count']}")
    except Exception as e:
        print(f"  Stats unavailable: {e}")


if __name__ == "__main__":
    main()
