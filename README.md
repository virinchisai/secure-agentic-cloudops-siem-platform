# 🔐 Secure Agentic CloudOps SIEM Platform

<p align="left">
  <img src="https://github.com/virinchisai/secure-agentic-cloudops-siem-platform/actions/workflows/python-app.yml/badge.svg" alt="Python CI" />
  <img src="https://img.shields.io/github/languages/top/virinchisai/secure-agentic-cloudops-siem-platform" alt="Top Language" />
  <img src="https://img.shields.io/github/repo-size/virinchisai/secure-agentic-cloudops-siem-platform" alt="Repo Size" />
  <img src="https://img.shields.io/badge/python-3.12-blue?logo=python&logoColor=white" alt="Python 3.12" />
  <img src="https://img.shields.io/badge/FastAPI-0.112-009688?logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/Kafka-Redpanda-FF6B35?logo=apachekafka&logoColor=white" alt="Redpanda" />
  <img src="https://img.shields.io/badge/PostgreSQL-16-336791?logo=postgresql&logoColor=white" alt="PostgreSQL" />
  <img src="https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white" alt="Docker" />
  <img src="https://img.shields.io/badge/Code%20Style-Black-000000" alt="Code Style" />
  <img src="https://img.shields.io/badge/Security-Bandit-yellow?logo=python&logoColor=white" alt="Bandit SAST" />
  <img src="https://img.shields.io/github/license/virinchisai/secure-agentic-cloudops-siem-platform" alt="License" />
  <img src="https://img.shields.io/github/last-commit/virinchisai/secure-agentic-cloudops-siem-platform" alt="Last Commit" />
</p>

A cloud-native, event-driven **SIEM-style security and CloudOps platform** that demonstrates **log ingestion, streaming pipelines, detection engineering, and scalable backend system design**.

This project simulates how modern security platforms ingest logs, process them in real time, detect suspicious activity, and persist alerts for investigation — while also outlining a clear roadmap toward **agentic, LLM-powered security automation**.

---

## 📡 Project Status

<table>
<tr>
<td>

### 🟢 Platform Status: **LIVE**

| Component | Status | Details |
|-----------|--------|---------|
| Ingest Service | 🟢 Active | FastAPI on `:8001` — validates, normalizes, publishes to Kafka |
| Detection Engine | 🟢 Active | 5 rules, Kafka consumer, real-time scoring on `:8002` |
| Streaming (Kafka) | 🟢 Active | Redpanda on `:9092` with Console UI on `:8080` |
| PostgreSQL | 🟢 Active | Events + alerts persistence on `:5432` |
| CI/CD Pipeline | 🟢 Active | Lint → Test → SAST → Docker Build |
| MLflow | 🟢 Active | Experiment tracking on `:5001` |

</td>
</tr>
<tr>
<td>

### 📊 Pipeline Metrics

| Metric | Value |
|--------|-------|
| Detection Rules | 5 (severity, brute force, priv escalation, data exfil, suspicious network) |
| Unit Tests | 18 passing (6 ingest + 12 detection) |
| Sample Events | 12 realistic security scenarios |
| Alert Labels | 7 categories |
| API Endpoints | 9 (health, ingest, batch, alerts, events, stats, alert detail, update, query) |
| Docker Services | 6 (ingest, detection, redpanda, console, postgres, mlflow) |

</td>
</tr>
</table>

> CI runs lint (Ruff + Black), unit tests (pytest), SAST (Bandit), secrets scanning, and Docker builds on every push and PR to `main`.

---

## 🎯 Project Objectives

- **Ingest logs:** Accept raw security logs through a REST API.
- **Stream events:** Stream logs using Kafka-compatible infrastructure (Redpanda).
- **Detect in real time:** Apply detection logic and scoring as events flow through the system.
- **Persist signals:** Store normalized events and alerts in PostgreSQL for investigation.
- **Support investigation:** Enable query-driven validation and basic investigation workflows.
- **Show system design:** Demonstrate production-grade, decoupled microservice architecture.
- **Enable a roadmap:** Provide a clear path to agentic security automation.

---

## 🚧 Implementation Status

This repository intentionally includes **both implemented components and a forward-looking architecture**.

### ✅ Implemented (fully working)

- Ingest service (FastAPI) with validation and batch ingestion
- Kafka-compatible streaming (Redpanda)
- Detection service with multi-rule engine (brute force, privilege escalation, data exfiltration, suspicious network, severity-based)
- PostgreSQL persistence for events and alerts with indexed queries
- Investigation API (query alerts, events, stats, update alert status)
- End-to-end data flow validation with 12 realistic sample events
- One-command local execution (`scripts/run_all.sh`)
- Fully Dockerized infrastructure and services
- CI/CD pipeline with linting (Ruff, Black), unit tests, SAST (Bandit), secrets scanning, and Docker builds
- 18 unit tests across both services

### 🧭 Planned / roadmap

- Agentic LLM reasoning engine
- Vector knowledge base for contextual retrieval
- Automated remediation workflows
- API gateway with authentication (JWT / OAuth / RBAC)
- SIEM dashboards and visualizations
- Cloud deployment (AWS / GCP)

> ⚠️ **Scope note**  
> Advanced components described later in this README represent **architectural intent and future roadmap**.  
> The current implementation focuses on a production-grade ingestion, streaming, detection, and persistence pipeline.

---

## 🧭 Table of Contents

- High-level architecture (current)
- Architecture explanation (step-by-step)
- Future-state architecture roadmap
- Technology stack
- Ports and services
- Repository structure
- Quick start (one command)
- Verify after running
- Stop and reset
- Service breakdown
- Developer experience (local development)
- CI/CD workflows (planned)
- Deployment (current and planned)
- Production hardening (planned)
- Observability (planned)
- Future enhancements
- License

---

## 🏗️ High-level architecture (current implementation)

```mermaid
flowchart TD
    Client([📡 Clients<br/>VPN • Firewall • Auth • Cloud])
    Ingest[Ingest Service<br/>FastAPI :8000]
    Kafka[(Kafka / Redpanda<br/>topic: logs.raw)]
    Detect[Detection Service<br/>Kafka Consumer]
    Events[(PostgreSQL<br/>events table)]
    Alerts[(PostgreSQL<br/>alerts table)]

    Client -->|HTTP JSON| Ingest
    Ingest -->|normalize + publish| Kafka
    Kafka -->|stream consume| Detect
    Detect -->|store normalized| Events
    Detect -->|store scored detections| Alerts

    classDef client fill:#FF6B35,stroke:#7c2d12,color:#fff
    classDef svc fill:#009688,stroke:#0d4f47,color:#fff
    classDef bus fill:#8b5cf6,stroke:#5b21b6,color:#fff
    classDef store fill:#336791,stroke:#1e3a5f,color:#fff
    class Client client
    class Ingest,Detect svc
    class Kafka bus
    class Events,Alerts store
```

<details>
<summary><b>📝 ASCII fallback (in case Mermaid doesn't render)</b></summary>

```text
Client (curl / scripts / agents)
        |
        v
Ingest Service (FastAPI)
        |
        v
Kafka / Redpanda (topic: logs.raw)
        |
        v
Detection Service (Kafka Consumer)
        |
        v
PostgreSQL
   ├── events   (normalized logs)
   └── alerts   (scored detections)
```

</details>

---

## 🧠 Architecture explanation (step-by-step)

### 1️⃣ Client
- Represents VPN gateways, authentication servers, firewalls, cloud services, applications
- Sends logs as JSON payloads over HTTP

### 2️⃣ Ingest service (FastAPI)
- Validates incoming payloads
- Normalizes logs into a consistent event model
- Assigns a unique `event_id`
- Publishes events to Kafka topic `logs.raw`

**Why it matters**
- Decouples producers from consumers
- Enables independent scaling
- Kafka buffers spikes and protects downstream services

### 3️⃣ Kafka / Redpanda
- Event streaming backbone
- Reliable buffering and replay
- Fan-out to one or more consumers

### 4️⃣ Detection service
- Consumes from `logs.raw`
- Applies detection rules and scoring
- Writes alerts to PostgreSQL
- Optionally emits derived topics (`alerts.scored`)

### 5️⃣ PostgreSQL
- Stores normalized events and derived alerts
- Enables investigation and historical analysis

---

## 🧭 Future-state architecture roadmap (vision)

```mermaid
flowchart LR
  subgraph Client
    UI(Web UI / CLI)
  end
  subgraph API["API Layer"]
    GW(API Gateway)
    BE(FastAPI Backend)
  end
  subgraph Data["Data Layer"]
    VDB[(Vector DB)]
    DB[(PostgreSQL)]
    MQ[(Message Queue)]
    OBJ[(Object Storage)]
  end
  subgraph Processing["Processing Layer"]
    ING(Ingestion)
    DET(Detection)
    AG(Agentic Reasoning)
    WF(Workflow Orchestrator)
  end
  UI --> GW --> BE
  BE --> ING --> MQ
  MQ --> DET --> MQ
  MQ --> AG --> MQ
  MQ --> WF --> API
```

---

## 🔐 Technology stack

### Backend & streaming
- Python 3.12
- FastAPI
- Redpanda (Kafka-compatible)
- PostgreSQL

### Tooling & infrastructure
- Docker & Docker Compose
- Poetry
- VS Code

---

## 🔌 Ports and services

| Service | Port | Purpose |
|------|----:|------|
| Ingest Service | 8001 | Log ingestion API |
| Detection Service | 8002 | Detection + Kafka consumer |
| Redpanda (Kafka) | 9092 | Streaming broker |
| Redpanda Console | 8080 | Kafka UI |
| Redpanda HTTP API | 8082 | Broker admin |
| PostgreSQL | 5432 | Events & alerts DB |
| MLflow | 5001 | Experiment tracking |

---

## 📂 Repository structure

```text
secure-agentic-cloudops-siem-platform/
├── docker-compose.yml
├── README.md
├── LICENSE
├── .gitignore
├── pyproject.toml
├── .github/workflows/
│   └── python-app.yml          # CI/CD pipeline
├── services/
│   ├── ingest-service/
│   │   ├── Dockerfile
│   │   ├── pyproject.toml
│   │   ├── app/
│   │   │   └── main.py         # FastAPI ingest endpoints
│   │   └── tests/
│   │       └── test_ingest.py
│   └── detection-service/
│       ├── Dockerfile
│       ├── pyproject.toml
│       ├── app/
│       │   ├── main.py          # FastAPI detection + query endpoints
│       │   └── rules.py         # Detection rules engine
│       └── tests/
│           └── test_rules.py
├── scripts/
│   ├── run_all.sh               # One-command startup
│   ├── stop_all.sh              # Graceful shutdown
│   ├── reset_all.sh             # Full reset (volumes + images)
│   ├── init_db.sql              # PostgreSQL schema
│   └── seed_sample_events.py    # Sample security events
└── docs/
```

---

## ⚡ Quick start (one command)

```bash
bash scripts/run_all.sh
```

This will:
- Start Docker infrastructure
- Create database tables
- Start ingest and detection services
- Send sample events
- Verify Kafka and PostgreSQL

---

## 🔎 Verify after running

```bash
curl http://127.0.0.1:8001/health
curl http://127.0.0.1:8002/health
```

```bash
docker exec -it secure-agentic-cloudops-siem-platform-postgres-1 \
psql -U app -d cloudops -c "SELECT COUNT(*) FROM alerts;"
```

---

## 🛑 Stop and reset

```bash
bash scripts/stop_all.sh
```

```bash
bash scripts/reset_all.sh
```

---

## 🧩 Service breakdown

> Sections below marked **(Planned)** describe future roadmap components.

<details>
<summary><strong>🧠 Agentic Reasoning Engine (Planned)</strong></summary>
LLM-powered reasoning, enrichment, and triage.
</details>

<details>
<summary><strong>⚙️ Workflow Orchestrator (Planned)</strong></summary>
Automated remediation workflows.
</details>

---

## 🧑‍💻 Developer experience (local development)

- Python virtual environments managed via Poetry
- Services run independently for local iteration
- Hot reload enabled via `uvicorn --reload`
- Docker used only for shared infrastructure

---

## 🔄 CI/CD workflows

Implemented via GitHub Actions (`.github/workflows/python-app.yml`):

- **Lint** — Ruff and Black format checks
- **Test** — pytest suites for ingest-service and detection-service (run in parallel)
- **Security** — Bandit SAST scan + grep-based secrets detection
- **Docker build** — Validates both service images build successfully

---

## 🚀 Deployment (current and planned)

### Current
- Local Docker Compose deployment

### Planned
- AWS (ECS / EKS)
- GCP (GKE)
- Terraform-based IaC

---

## 🔐 Production hardening (planned)

- TLS everywhere
- Secrets management
- Kafka partitioning
- Database indexing
- Rate limiting
- RBAC

---

## 📊 Observability (planned)

- Structured logging
- Prometheus metrics
- Grafana dashboards
- OpenTelemetry tracing

---

## 🚧 Future enhancements

- Agentic remediation
- Cross-event correlation
- Threat intelligence enrichment
- Multi-tenant support

---

## 📜 License

This project is licensed under the **MIT License**.
