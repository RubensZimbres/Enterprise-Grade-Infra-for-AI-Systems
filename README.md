# Enterprise AI Platform: RAG with Guardrails

This repository contains a full-stack, secure AI platform deployed on Google Cloud. It enables private, internal document chat with enterprise-grade security and automated PII protection.

## 🏗️ Architecture Overview

The platform is composed of three main layers:

1.  **Frontend Agent (UI):** A Streamlit application providing a chat interface. It is protected by a Global Load Balancer with Identity-Aware Proxy (IAP) for user authentication.
2.  **Backend Agent (Neural Core):** A FastAPI service that orchestrates the RAG pipeline. It handles document retrieval, LLM interaction (Gemini Pro), and persistent memory.
3.  **Infrastructure (Terraform):** Fully automated deployment using "Infrastructure as Code," including private networking and serverless scaling.

## 🚀 Key Features

-   **RAG Pipeline:** Uses Vertex AI Embeddings and AlloyDB (with `pgvector`) for high-speed semantic search.
-   **Automated Guardrails:** Integrates Google Cloud DLP to sanitize user input and model output, masking PII (emails, credit cards, phones) in real-time.
-   **Conversation Memory:** Uses Cloud Firestore to maintain persistent chat history across sessions.
-   **Service-to-Service Security:** The Frontend authenticates to the Backend using OIDC Identity Tokens, ensuring the Backend remains private (Internal Only).
-   **Enterprise Security:** Secured by IAP, Cloud IAM, and VPC Service Controls.

## 🛠️ Component Details

### Frontend (Streamlit)
-   **Location:** `/frontend-agent`
-   **Auth:** Generates OIDC tokens using `google-auth` to call the backend securely.
-   **State:** Manages session-based chat history locally and syncs with the backend.

### Backend (FastAPI)
-   **Location:** `/backend-agent`
-   **LLM:** Google Vertex AI `gemini-pro`.
-   **Vector DB:** AlloyDB for PostgreSQL with the `vector` extension.
-   **Guardrails:** DLP-based de-identification logic in `backend-agent/chains/guardrails.py`.

### Infrastructure (Terraform)
-   **Network:** Custom VPC with a Serverless VPC Access connector to allow Cloud Run to access the private AlloyDB instance.
-   **Database:** High-availability AlloyDB cluster.
-   **Compute:** Cloud Run services with custom Service Accounts and Least-Privilege IAM roles.
-   **Ingress:** Global Load Balancer + IAP + Managed SSL Certificates.

## 🚜 Deployment

For detailed deployment instructions, including required APIs and IAM permissions, see [NECESSARY_SETUP.md](./NECESSARY_SETUP.md).