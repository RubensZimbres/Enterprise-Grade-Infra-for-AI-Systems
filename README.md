# Enterprise AI Platform: RAG with Guardrails in Google Cloud Deployed via Terraform

This repository contains a full-stack, secure AI platform deployed on Google Cloud. It enables private, internal document chat with enterprise-grade security and automated PII protection, deployed via Terraform and Cloud Build.

## Architecture Overview

![Google Cloud Architecture](images/Google_Cloud_Architecture.jpg)
*Figure 1: Google Cloud Platform Architecture*

![AWS Architecture](images/AWS_Architecture.jpg)
*Figure 2: AWS Architecture*

The platform is composed of three main layers:

1.  **Frontend (UI):** A modern, high-concurrency **Next.js** application providing a real-time streaming chat interface. Protected by a Global Load Balancer with Identity-Aware Proxy (IAP) and Cloud Armor.
2.  **Backend Agent (Neural Core):** An asynchronous **FastAPI** service orchestrating the RAG pipeline, secured by OIDC authentication and internal-only networking.
3.  **Infrastructure (Terraform):** Fully automated deployment using "Infrastructure as Code."

## AI Engine & Knowledge Core: Memory & RAG Implementation

The Backend Agent is designed as a stateful, retrieval-augmented system that balances high-performance search with secure session management.

### 1. Short-Term Memory (Session Context)
*   **Storage:** Utilizes **Google Cloud Firestore** (Native Mode) for low-latency persistence of chat history.
*   **Security & Isolation:** Every session is cryptographically scoped to the authenticated user's email (`user_email:session_id`). This ensures strict multi-tenancy where users can never access or "leak" into another's conversation history (IDOR protection).

### 2. Long-Term Memory (Knowledge Base)
*   **Vector Database:** Powered by **PostgreSQL 15** (Cloud SQL) with the `vector` extension (`pgvector`).
*   **Semantic Caching:** Integrated with **Redis (Memorystore)** using a `RedisSemanticCache`. If a query is semantically similar to a cached one, the system returns the result instantly, reducing latency and cost.

## Security & Resilience: A Multi-Layered Defense

This platform implements a robust, multi-layered security strategy, hardening the application against modern threats.

### 1. Web & Application Security (Edge Defense)
-   **Cloud Armor WAF (Enterprise Grade):** The Global Load Balancer is equipped with a comprehensive **Google Cloud Armor** security policy:
    -   **OWASP Top 10 Protection:** Active blocking of SQL Injection (`sqli`), Cross-Site Scripting (`xss`), Local File Inclusion (`lfi`), and Remote Command Execution (`rce`).
    -   **Scanner Detection:** Automatically detects and blocks IPs associated with malicious security scanners.
    -   **Protocol Attack Mitigation:** Filters malformed HTTP requests and smuggling attempts.
-   **Adaptive Protection:** Employs machine learning to autonomously detect and mitigate Layer 7 DDoS attacks by analyzing traffic patterns in real-time.
-   **Rate Limiting:** Global policy (500 req/min per IP) protects against volumetric DDoS and brute-force attempts.

### 2. AI & LLM Specific Security: The Security Judge
The platform implements an advanced **Two-Stage Defense** for all AI prompts:
-   **Stage 1: Fast Regex Blocker:** A high-performance regex engine scans for over 200+ dangerous patterns (SQLi, XSS, `rm -rf`, `sudo`). This provides instant, cost-free protection against common payloads.
-   **Stage 2: LLM Security Judge:** A context-aware **Gemini 1.5 Flash** agent evaluates the *intent* of the input. It is specifically prompted to detect "Prompt Injection," "Social Engineering," and obfuscated attacks that regex might miss. 
-   **PII De-identification (DLP):** Integrated with **Google Cloud DLP**. The system de-identifies sensitive data (Emails, SSNs, Credit Cards) in both user input and LLM output using an asynchronous pipeline for zero latency.

### 3. Identity & Access Control
-   **Identity-Aware Proxy (IAP):** Provides a central authentication layer. Only authorized enterprise users can reach the frontend UI.
-   **Zero-Trust Networking:** The backend core is deployed with `INGRESS_TRAFFIC_INTERNAL_ONLY`. It is unreachable from the public internet and only accepts traffic from the internal VPC connector.
-   **Service-to-Service OIDC:** The Frontend authenticates to the Backend using short-lived OIDC ID tokens, ensuring that even internal traffic is strictly verified.

## Validation: Red-Teaming & Testing

The platform includes a dedicated security validation suite to ensure the guardrails are functioning correctly.

### Running Security Tests
You can execute the automated Red-Teaming script to test the backend's resilience against various attack vectors:

```bash
cd backend-agent
python red_team_test.py
```

**Tested Attack Vectors:**
*   **SQL Injection:** Obfuscated and stacked queries.
*   **Command Injection:** Shell commands and pipe chaining.
*   **Path Traversal:** Accessing `/etc/passwd` or system directories.
*   **Prompt Injection:** Adversarial "Ignore instructions" payloads.
*   **Social Engineering:** Attempts to extract system secrets via dialogue.

## Local Development & Configuration

### 1. Configuration (Environment Variables)

**Backend (`backend-agent`):**
| Variable | Description |
| :--- | :--- |
| `PROJECT_ID` | Your Google Cloud Project ID. |
| `REGION` | GCP region (e.g., `us-central1`). |
| `DB_HOST` | IP of your Cloud SQL instance. |
| `DB_USER` | Database username (default: `postgres`). |
| `DB_PASSWORD` | Database password. |

### 2. Running Locally

```bash
# Start Backend
cd backend-agent
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8080

# Start Frontend
cd frontend-nextjs
npm install
npm run dev
```

## Deployment & Data Ingestion

### 1. Deploy Infrastructure
You must provide a valid domain name (e.g., `ai.your-company.com`) for the managed SSL certificate to be provisioned.

```bash
cd terraform
terraform init
terraform apply -var="domain_name=ai.your-company.com" -var="project_id=YOUR_PROJECT_ID"
```
*After deployment, point your domain's DNS A-record to the output `public_ip`.*

### 2. Ingest Knowledge Base
The platform includes a serverless Cloud Run Job for hydrating the vector database. Once your infrastructure is up, run:

```bash
gcloud run jobs execute ingest-job --region=us-central1
```
This will parse documents from the `backend-agent/data` directory (baked into the container) and index them into Cloud SQL.

## Infrastructure (Terraform)
Deployment is fully automated via the following modules:
-   **`network`**: VPC, Cloud NAT, and Private Service Access.
-   **`compute`**: Cloud Run agents with Least-Privilege IAM.
-   **`database`**: Cloud SQL (PostgreSQL) and Firestore.
-   **`ingress`**: Load Balancer, SSL, and the **Cloud Armor Security Policy**.
-   **`billing_monitoring`**: Budgets and real-time anomaly alerts.

---
*Enterprise AI Platform: Built for security, scaled for performance.*
