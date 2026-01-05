# From PoC to Production: Enterprise AI Platform with RAG and Guardrails
This repository contains a full-stack, secure AI platform deployed on Google Cloud via Terraform. It enables secure, RAG-based chat with enterprise-grade security and automated PII protection, accessible to public users via Firebase Authentication.

## Architecture Overview
![Google Cloud Architecture](images/Google_Cloud_Architecture.jpg)
*Figure 1: Google Cloud Platform Architecture*

![AWS Architecture](images/AWS_Architecture.jpg)
*Figure 2: Correspondent AWS Architecture*

---

## Component Details
### Frontend (Next.js Agent)
-   **Location:** `/frontend-nextjs`
-   **Tech:** React 18, Tailwind CSS, Lucide Icons, Firebase.
-   **Resilience:** **Circuit Breaker** `opossum`) for fail-fast backend communication.
-   **Security:** Acts as a secure proxy to the Backend; Authentication handled via Firebase.
-   **Scalability:** Configured with `min_instances = 1` for zero-latency response.

### Backend (FastAPI Agent)
-   **Location:** `/backend-agent`
-   **Neural Core:** Orchestrates RAG using LangChain and Vertex AI.
-   **Resilience:** **Retries** `tenacity`) for transient errors & **OpenTelemetry** tracing.
-   **Vector DB:** Cloud SQL for PostgreSQL 15 with `pgvector` and `asyncpg`.
-   **Networking:** Set to `INGRESS_TRAFFIC_INTERNAL_ONLY` to ensure it is unreachable from the public internet.

### Infrastructure (Terraform Modules)
-   *`network`**: VPC, Subnets, Cloud NAT, and PSA.
-   *`compute`**: Cloud Run services and granular IAM policies.
-   *`database`**: Cloud SQL (PostgreSQL) and Firestore (Chat History).
-   *`redis`**: Memorystore for semantic caching.
-   *`ingress`**: Global Load Balancer, Cloud Armor, and SSL.
-   *`billing_monitoring`**: Budgets, Alert Policies, and Notification Channels.

## Architecture Decisions & Rationale
1. **Authentication: Google Identity (IAP) vs. Firebase**
   I explicitly chose **Identity-Aware Proxy (IAP)** over Firebase Authentication for this enterprise architecture.
   *   **Zero-Code Auth:** IAP handles the entire login flow (OIDC, 2FA, session management) at the infrastructure level (Load Balancer) before the request ever reaches the container. This eliminates the need for complex auth logic in the application code.
   *   **Zero Trust:** It enforces a "Zero Trust" model where access is granted based on identity and context at the edge, rather than just at the application level.
   *   **Enterprise Integration:** It integrates seamlessly with Google Workspace identities, making it ideal for internal enterprise tools.
2. **Communication: Asyncio vs. Pub/Sub**
   While Pub/Sub is excellent for decoupled, asynchronous background tasks, I utilize **Python's asyncio** within FastAPI for the chat interface.
   *   **Real-Time Requirement:** Chat users expect immediate, streaming responses. Pub/Sub is a "fire-and-forget" mechanism designed for background processing, not for maintaining the open, bidirectional HTTP connections required for streaming LLM tokens to a user in real-time.
   *   **Concurrency:** `asyncio` allows a single Cloud Run instance to handle thousands of concurrent waiting connections (e.g., waiting for Vertex AI to reply) without blocking, providing high throughput for chat without the architectural complexity of a message queue.
3. **Event-Driven Ingestion: Cloud Functions**
   I moved the document ingestion logic from a manual script to a **Google Cloud Function** triggered by Cloud Storage events.
   *   **Automation:** Uploading a PDF to the `data_bucket` automatically triggers the function to parse, chunk, embed, and upsert the document into the vector database.
   *   **Efficiency:** This is a serverless, event-driven approach. Resources are only consumed when a file is uploaded, rather than having a long-running service waiting for input.
   *   **Scalability:** Each file upload triggers a separate function instance, allowing parallel processing of mass uploads without blocking the main chat application.

## AI Engine & Knowledge Core: Memory & RAG Implementation
The Backend Agent is designed as a stateful, retrieval-augmented system that balances high-performance search with secure session management.
### 1. Short-Term Memory (Session Context)
*   **Storage:** Utilizes **Google Cloud Firestore (Native Mode)** for low-latency persistence of chat history.
*   **Implementation:** Leverages `FirestoreChatMessageHistory` within the LangChain framework.
*   **Security & Isolation:** Every session is cryptographically scoped to the authenticated user's email `user_email:session_id`). This ensures strict multi-tenancy where users can never access or "leak" into another's conversation history (IDOR protection).
*   **Context Injection:** The system automatically retrieves the last $N$ messages and injects them into the history placeholder of the RAG prompt, enabling multi-turn, context-aware dialogue.
### 2. Long-Term Memory (Knowledge Base)
*   **Vector Database:** Powered by **PostgreSQL 15 (Cloud SQL)** with the vector extension `pgvector`).
*   **Retrieval Logic:** Employs semantic similarity search using `VertexAIEmbeddings` `textembedding-gecko@003`). For every query, the engine retrieves the top 5 most relevant chunks ($k=5$) to provide grounded context to the LLM.
*   **Semantic Caching:** Integrated with **Redis (Memorystore)** using a `RedisSemanticCache`. If a user asks a question semantically similar to a previously cached query (threshold: 0.05), the system returns the cached response instantly, bypassing the LLM to save cost and reduce latency.
### 3. RAG Specifications & Document Ingestion
*   **Ingestion Pipeline:** A specialized `ingest.py` script handles the transformation of raw data into "AI-ready" vectors.
*   **Smart Chunking:** Uses the `RecursiveCharacterTextSplitter` to maintain semantic integrity:
    *   **Chunk Size:** 1000 characters/tokens.
    *   **Chunk Overlap:** 200 characters (ensures no loss of context at the edges of chunks).
    *   **Separators:** Prioritizes splitting by double newlines (paragraphs), then single newlines, then spaces.
*   **Document Support:** Includes a `DirectoryLoader` with `PyPDFLoader` to automatically parse and index complex PDF structures.
### 4. Cache Implementation
*   **Cost Savings:** You pay for the system instruction tokens once per hour (cache creation) instead of every single request.
*   **Latency:** The model doesn't need to re-process the large system prompt for every user query, leading to faster Time to First Token (TTFT).
*   **Implicit vs. Explicit:** I relied on Implicit Caching for the short-term chat history (managed automatically by Gemini) and implemented Explicit Caching for the static, heavy system prompt.

## Security & Resilience: A Multi-Layered Defense
This platform implements a robust, multi-layered security strategy. The codebase and infrastructure have been hardened against the following threats:
### 1. Web & Application Security (OWASP Top 10)
*   **SQL Injection (SQLi) Protection:**
    *   **Infrastructure Level:** Google Cloud Armor is configured with pre-configured WAF rules `sqli-v33-stable`) to filter malicious SQL patterns at the edge.
    *   **Application Level:** The backend uses `asyncpg` (via LangChain's PGVector), which strictly employs parameterized queries, ensuring user input is never executed as raw SQL.
*   **Cross-Site Scripting (XSS) Protection:**
    *   **Infrastructure Level:** Cloud Armor WAF rules `xss-v33-stable`) detect and block malicious script injection attempts.
    *   **Framework Level:** Next.js (Frontend) automatically sanitizes and escapes content by default, and the backend returns structured JSON to prevent direct script rendering.
*   **Broken Access Control & IDOR (Insecure Direct Object Reference):**
    *   **Verified Identity (IAP):** The frontend acts as a Secure Proxy. It captures the user's identity from the Identity-Aware Proxy (IAP) headers `X-Goog-Authenticated-User-Email`) and propagates it to the backend.
    *   **Session Isolation:** Chat histories are cryptographically scoped to the authenticated user's identity `user_email:session_id`), preventing IDOR attacks where one user could access another's private history.
### 2. DDoS & Resource Abuse Protection
*   **Edge Protection:** Cloud Armor implements a global rate-limiting policy (500 requests/min per IP) and a "rate-based ban" to mitigate large-scale volumetric DDoS and brute-force attacks.
*   **Application Resilience:** The backend core utilizes `slowapi` to enforce granular rate limiting (5 requests/min per user) specifically for expensive LLM operations, protecting against cost-based denial-of-service and resource exhaustion.
*   **Input Validation:** Pydantic models in the backend enforce a strict 10,000-character limit on user messages to prevent memory-exhaustion attacks.
### 3. AI & LLM Specific Security (OWASP Top 10 for LLM)
*   **Prompt Injection Mitigation:** The RAG prompt template uses strict structural delimiters `----------`) and prioritized system instructions to ensure the model adheres to its enterprise role and ignores adversarial overrides contained within documents or user queries.
*   **Sensitive Data Leakage (PII):** Google Cloud DLP (Data Loss Prevention) is integrated into the core pipeline with a Regex Fast-Path and Asynchronous Threading. This automatically detects and masks PII in real-time without blocking the main event loop, ensuring high performance while minimizing API costs.
*   **Knowledge Base Security:** Data is stored in a private Cloud SQL (PostgreSQL) instance reachable only via a Serverless VPC Access connector, ensuring the "Brain" of the AI is never exposed to the public internet.
### 4. MAESTRO Framework

* **Preventing Wallet Exhaustion (Rate Limiting & Input Validation)**
   - **Action:** Reduced API rate limit: 10/minute for authenticated users.
   - **Action:** Added a `validate_token_count` function (using a lightweight 4-char/token heuristic) to strictly enforce input size limits before processing, rejecting requests that exceed the limit (2000 tokens) with a 400 error.

* **RAG Hardening (Prompt Injection Defense)**
   - **Action:** Prompt Templates with Cache Hit and Cache Miss scenarios.
   - **Action:** "Sandwich Defense" using XML tagging (`<trusted_knowledge_base>`) and explicit instructions to ignore external commands found within the retrieved context.

* **Guardrail Layer (Improved Security Judge)**
   - **Action:** Regex `SecurityBlocker` for low-latency filtering of obvious attacks.
   - **Action:** The `security_judge_llm` uses a more specific system prompt acting as a specialized classifier ("SAFE" vs "BLOCKED").
   - **Action:** Google's Native Content Safety Settings (`HarmBlockThreshold.BLOCK_LOW_AND_ABOVE`) on the Judge model to leverage Vertex AI's built-in safety classifiers for Hate Speech, Dangerous Content, etc.

* **Model Safety (Generation Hardening)**
   - **Action:** Strict `SAFETY_SETTINGS` (blocking low and above harm probability) to the main RAG generation models (`ChatVertexAI`). This acts as a final line of defense against generating harmful content, even if prompt injection succeeds.

**Note on Streaming DLP:**
The current `protected_chain_stream` sanitizes the input but streams the output directly from the LLM to the client to maintain responsiveness. By enforcing the strict `SAFETY_SETTINGS` on the generation model itself, we have mitigated the risk of the model generating harmful content, serving as an effective output guardrail for the streaming endpoint.

## Enhanced Enterprise Architecture (Optimized)
This platform has been upgraded for production-scale performance, cost efficiency, and sub-second perceived latency:
### 1. Global Scalability & High Availability
*   **Horizontal Autoscaling:** Both Frontend and Backend services are configured for automatic horizontal scaling in Cloud Run. They can scale from zero to hundreds of concurrent instances to handle massive traffic spikes.
*   **Cold-Start Mitigation:** The Frontend service maintains a minimum of 1 warm instance `min_instance_count = 1`), ensuring immediate responsiveness and eliminating "cold start" latency for users.
*   **Cloud SQL Read Pool:** While currently using a single instance for cost efficiency, the architecture is ready for a dedicated Read Replica in Cloud SQL. This horizontally scales read capacity for the vector database, ensuring that heavy document retrieval and search operations do not bottleneck the primary write instance.
### 2. Latency & Performance Optimization
*   **Asynchronous I/O (Neural Core):** The backend is built on FastAPI and uses `asyncpg` for non-blocking database connections. This allows a single instance to handle thousands of concurrent requests with minimal resource usage.
*   **Server-Sent Events (SSE):** Real-time token streaming from the LLM (Gemini 3 Flash) directly to the Next.js UI provides sub-second "Time-To-First-Token," creating a highly responsive user experience.
*   **Asynchronous Thread Pooling:** Expensive operations like PII de-identification via Google Cloud DLP are offloaded to asynchronous background threads, preventing them from blocking the main request-response cycle.
### 3. Cost Control & Efficiency
-   **Gemini 3 Flash Integration:** Utilizes the high-efficiency Flash model `gemini-3-flash-preview`) for a 10x reduction in token costs and significantly lower latency compared to larger models.
-   **DLP Fast-Path Guardrails:** Implemented a high-performance regex-based "pre-check" for PII. This intelligently bypasses expensive Google Cloud DLP API calls for clean content, invoking the API only when potential PII patterns are detected.
-   **Global CDN Caching:** Google Cloud CDN is enabled at the Load Balancer level to cache static assets and common frontend resources globally, reducing origin server load and improving page load times.
-   **Smart Storage Versioning:** Implemented Object Lifecycle Management on Cloud Storage buckets. Files are automatically transitioned to **Nearline** storage after 7 days, **Archive** storage after 30 days, and **deleted** after 90 days. This ensures disaster recovery capabilities (versioning is enabled) without indefinite storage costs.

## Performance & Scaling Roadmap
The current infrastructure is designed for high efficiency and is benchmarked to handle approximately 2,500 users per hour with the standard provisioned resources.
### How to Actually Reach 1,000,000 Users per Hour
To handle this load, you must change the architecture:
**Solution A: Offload Vector Search (Recommended)**
Use a specialized engine designed for high-throughput vector search.
*   **Use:** Google Vertex AI Vector Search (formerly Matching Engine).
*   **Why:** It is fully managed and designed to handle billions of vectors and thousands of QPS with <10ms latency.
*   **Architecture Change:**
    *   **Postgres:** Only stores Chat History and User Metadata (cheap writes).
    *   **Vertex AI:** Handles the 2,800 QPS vector load.

## Payment & Subscription System
The platform now enforces a strict **"Login -> Pay -> Chat"** workflow using Stripe and Cloud SQL.
### 1. Payment Architecture
*   **Source of Truth:** The Cloud SQL (PostgreSQL) database is the single source of truth for user subscription status.
*   **Stripe Integration:**
    *   **Webhooks:** A secure `/webhook` endpoint listens for `checkout.session.completed` and `invoice.payment_succeeded` events from Stripe.
    *   **Automatic Activation:** When a payment succeeds, the webhook updates the user's `is_active` status in the `users` table.
*   **Security Enforcement:**
    *   **Backend Middleware:** The `get_current_user` dependency checks the database for every request. If `is_active` is false, it raises a `403 Forbidden` error.
    *   **Frontend Redirect:** The frontend intercepts these 403 errors and automatically redirects the user to the `/payment` page.
### 2. Database Schema
The new `users` table tracks subscription state:
*   `email` (Primary Key): Linked to Firebase Identity.
*   `is_active` (Boolean): Grants access to the chat.
*   `stripe_customer_id`: Links to the Stripe Customer.
*   `subscription_status`: Status string (e.g., 'active', 'past_due').

---

## Prerequisites
Before running the project locally or deploying to the cloud, ensure you have the following installed:
*   **Docker Desktop:** Required for running the local database (Postgres/Vector) and Redis.
*   **Node.js (v18+):** For the Frontend.
*   **Python (3.10+):** For the Backend.
*   **Google Cloud CLI `gcloud`):** For authenticated access to GCP services (Vertex AI, Firestore, etc.).
*   **Stripe CLI:** For testing payments locally.

#### IAM Connectivity Matrix
The following table details the Zero-Trust permission model enforced by the infrastructure:
| Source | Target | Role | Status |
| :--- | :--- | :--- | :--- |
| Frontend SA | Backend Service | `roles/run.invoker` | ✅ Present |
| Backend SA | Vertex AI | `roles/aiplatform.user` | ✅ Present |
| Backend SA | Cloud SQL | `roles/cloudsql.client` | ✅ Present |
| Backend SA | Secret Manager | `roles/secretmanager.secretAccessor` | ✅ Present |
| Backend SA | Firestore | `roles/datastore.user` | ✅ Present |
| Backend SA | Cloud DLP | `roles/dlp.user` | ✅ Present |
| Function SA | Storage | `roles/storage.objectViewer` | ✅ Present |
| Cloud Build SA | CI/CD | `roles/run.admin` | ✅ Present |
| Cloud Build SA | CI/CD | `roles/iam.serviceAccountAdmin` | ✅ Present |
| Cloud Build SA | CI/CD | `roles/artifactregistry.writer` | ✅ Present |

---

# Local Development Guide

This guide details how to run the Enterprise AI Platform locally for development and testing.

## Prerequisites

*   **Docker Desktop** (for running the database and cache locally).
*   **Python 3.10+** (for the Backend).
*   **Node.js 18+** (for the Frontend).
*   **Google Cloud Project** with Firebase Authentication enabled.
*   **Stripe Account** (for testing payments).

---

## 1. External Services Setup

Since this is a cloud-native application, you need to connect to a few real external services even for local development.

### A. Firebase (Authentication)
1.  Go to the [Firebase Console](https://console.firebase.google.com/).
2.  Create a project (or use an existing one).
3.  Enable **Authentication** and set up the **Email/Password** provider.
4.  Go to **Project Settings > General** and scroll to "Your apps".
5.  Select "Web app", register it, and copy the `firebaseConfig` object. You will need these values for the Frontend.
6.  **Service Account Key (for Backend):**
    *   Go to **Project Settings > Service accounts**.
    *   Click "Generate new private key".
    *   Save this JSON file as `service-account-key.json` in the root of the `backend-agent` directory. **DO NOT COMMIT THIS FILE.**

### B. Stripe (Payments)
1.  Go to the [Stripe Dashboard](https://dashboard.stripe.com/).
2.  Enable "Test Mode".
3.  Get your **Publishable Key** and **Secret Key**.
4.  Create a **Webhook** endpoint pointing to `http://localhost:8080/webhook` (you may need a tool like `ngrok` or Stripe CLI to forward local events, or just mock the payment flow in the DB manually).

---

## 2. Local Infrastructure (Database & Cache)

We will use Docker Compose to run PostgreSQL (with `pgvector`) and Redis locally.

Use the `docker-compose.yml` file in the root of the project:

Start the infrastructure:
```bash
docker-compose up -d
```

---

## 3. Backend Setup

### Configuration
Create a `.env` file in `backend-agent/`:

```env
# Disable Secret Manager loading
PROJECT_ID=""

# Debug Mode
DEBUG=true

# Database (Matches docker-compose.yml)
DB_HOST=localhost
DB_USER=postgres
DB_PASSWORD=password
DB_NAME=postgres

# Redis
REDIS_HOST=localhost
REDIS_PASSWORD=""

# Stripe (From Step 1B)
STRIPE_API_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Google Cloud (Required for Vertex AI & Firestore)
# Ensure you are authenticated via 'gcloud auth application-default login'
# OR set GOOGLE_APPLICATION_CREDENTIALS to your key file path
GOOGLE_APPLICATION_CREDENTIALS=service-account-key.json

# Vertex AI Region
REGION=us-central1
```

### Installation & Run

1.  Navigate to the backend directory:
    ```bash
    cd backend-agent
    ```
2.  Create a virtual environment:
    ```bash
    python -m venv venv
    source venv/bin/activate  # Windows: venv\Scripts\activate
    ```
3.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
4.  Run the server:
    ```bash
    uvicorn main:app --reload --host 0.0.0.0 --port 8080
    ```

**Note:** The backend will attempt to connect to Google Cloud services (Vertex AI for embeddings, Firestore for chat history). Ensure your `service-account-key.json` has permissions for:
*   `roles/aiplatform.user`
*   `roles/datastore.user`

---

## 4. Frontend Setup

### Configuration
Create a `.env.local` file in `frontend-nextjs/`:

```env
# Backend URL (Proxy or Direct)
BACKEND_URL=http://localhost:8080

# Firebase Config (From Step 1A)
NEXT_PUBLIC_FIREBASE_API_KEY=AIzaSy...
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
NEXT_PUBLIC_FIREBASE_PROJECT_ID=your-project-id
NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET=your-project.appspot.com
NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=...
NEXT_PUBLIC_FIREBASE_APP_ID=...

# Stripe Config (From Step 1B)
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_...
```

### Installation & Run

1.  Navigate to the frontend directory:
    ```bash
    cd frontend-nextjs
    ```
2.  Install dependencies:
    ```bash
    npm install
    ```
3.  Run the development server:
    ```bash
    npm run dev
    ```
4.  Open [http://localhost:3000](http://localhost:3000).

---

## 5. Testing the Flow

1.  **Sign Up:** Open the frontend and create an account via Firebase Auth.
2.  **Payment (Manual Activation):** Since local Stripe webhooks might be tricky without `ngrok`, you can manually activate your user in the local database:
    *   Connect to local Postgres:
        ```bash
        psql postgres://postgres:password@localhost:5432/postgres
        ```
    *   Find your user (created after login attempt) and update status:
        ```sql
        UPDATE users SET is_active = true WHERE email = 'your-email@example.com';
        ```
3.  **Chat:** You should now be able to access the chat interface. Messages will be:
    *   Embedded via Vertex AI (Cloud).
    *   Stored in Firestore (Cloud).
    *   Vector-searched in Postgres (Local).

---
# Testing Guide

This project contains automated tests for both the backend (FastAPI) and frontend (Next.js) applications. Follow the instructions below to run the tests.

## Backend (FastAPI)

The backend uses `pytest` for testing.

### Prerequisites
Ensure you have the Python dependencies installed:

```bash
cd backend-agent
pip install -r requirements.txt
```

### Running Tests
To run all tests:

```bash
# From the backend-agent directory
pytest ./tests/test_main.py
```

### Directory Structure
*   `tests/conftest.py`: Contains test fixtures (e.g., `client` for API requests, mocks).
*   `tests/test_main.py`: Contains API endpoint tests.

## Frontend (Next.js)

The frontend uses `Jest` and `React Testing Library`.

### Prerequisites
Ensure you have the Node.js dependencies installed:

```bash
cd frontend-nextjs
npm install
```

### Running Tests
To run the test suite:

```bash
# From the frontend-nextjs directory
npm test
```

To run tests in watch mode (re-runs on file changes):

```bash
npm run test:watch
```

### Directory Structure
*   `__tests__/`: Contains the test files (e.g., `LandingPage.test.tsx`).
*   `jest.config.ts`: Jest configuration.
*   `jest.setup.ts`: Global test setup (e.g., loading `jest-dom` matchers).

---

# Deployment Guide: From Zero to Production

This guide assumes you have a Google Cloud Project and the necessary CLI tools installed (`gcloud`, `terraform`, `docker`, `npm`, `python`).

## Phase 1: Pre-Terraform Setup (Manual Actions)

### Step 1: Google Cloud Project Setup
1.  **Create/Select a Project:**
    ```bash
    gcloud auth login
    gcloud config set project [YOUR_PROJECT_ID]
    gcloud config set compute/region us-central1
    ```
2.  **Link Billing:** Ensure your project is linked to a Billing Account.
3.  **Enable APIs:**
    ```bash
    gcloud services enable \
      compute.googleapis.com \
      iam.googleapis.com \
      run.googleapis.com \
      artifactregistry.googleapis.com \
      cloudbuild.googleapis.com \
      secretmanager.googleapis.com \
      sqladmin.googleapis.com \
      firestore.googleapis.com \
      dlp.googleapis.com \
      aiplatform.googleapis.com \
      redis.googleapis.com \
      cloudfunctions.googleapis.com \
      storage.googleapis.com
    ```

### Step 2: GitHub Connection (Critical)
Terraform creates Cloud Build triggers that watch your repo. You **must** connect your repository to Google Cloud Build manually before running Terraform.

1.  Go to the [Cloud Build Triggers page](https://console.cloud.google.com/cloud-build/triggers).
2.  Click **Manage Repositories** -> **Connect Repository**.
3.  Select **GitHub** and follow the authorization flow.
4.  Select the repository containing this code.

### Step 3: Grant IAM Permissions
Terraform needs permission to manage IAM policies, and Cloud Build needs permission to deploy.

```bash
PROJECT_NUMBER=$(gcloud projects describe $(gcloud config get-value project) --format="value(projectNumber)")

# Grant Cloud Build permissions
gcloud projects add-iam-policy-binding $(gcloud config get-value project) \
  --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding $(gcloud config get-value project) \
  --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
  --role="roles/iam.serviceAccountAdmin"

gcloud projects add-iam-policy-binding $(gcloud config get-value project) \
  --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
  --role="roles/artifactregistry.writer"

# Grant Cloud Build Service Account permissions to deploy to Cloud Run
gcloud projects add-iam-policy-binding $(gcloud config get-value project) \
  --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
  --role="roles/run.developer"

# Grant Cloud Build Service Account permission to act as other service accounts (required for Cloud Run deploy)
gcloud projects add-iam-policy-binding $(gcloud config get-value project) \
  --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"
```
To deploy manually, run:

```bash
gcloud builds submit --config cloudbuild-backend.yaml .
gcloud builds submit --config cloudbuild-frontend.yaml .
```

## Phase 2: Terraform Configuration

### Step 4: Create `terraform.tfvars`
Create a file named `terraform/terraform.tfvars` and populate it with your specific configuration.

```hcl
project_id         = "your-project-id"
region             = "us-central1"
domain_name        = "ai.your-domain.com"  # The domain you will use for the frontend
github_owner       = "your-github-username"
github_repo_name   = "your-repo-name"
billing_account    = "000000-000000-000000" # Your Billing Account ID
notification_email = "admin@example.com"    # For budget alerts
```

## Phase 3: Infrastructure Deployment

### Step 5: Run Terraform
```bash
cd terraform
terraform init
terraform plan
terraform apply
```
*Type `yes` when prompted.*

This process will take 15-20 minutes. It creates:
*   VPC Network & Serverless Access
*   Cloud SQL (PostgreSQL) & Redis
*   Cloud Run Services (Frontend & Backend)
*   Cloud Function (PDF Ingest)
*   Secret Manager placeholders

### Step 6: Configure Secrets
Terraform created the *containers* for your secrets, but you need to add the *values*.

1.  **Stripe Keys:**
    *   Find the secret `STRIPE_SECRET_KEY` in Secret Manager and add a new version with your Stripe **Secret Key**.
    *   Find the secret `STRIPE_PUBLISHABLE_KEY` and add your Stripe **Publishable Key**.

2.  **Missing Secrets (Manual Creation):**
    Due to backend configuration requirements, you must manually create the following secrets:
    ```bash
    # Create Stripe Webhook Secret (from Stripe Dashboard)
    gcloud secrets create STRIPE_WEBHOOK_SECRET --replication-policy="automatic"
    echo -n "whsec_..." | gcloud secrets versions add STRIPE_WEBHOOK_SECRET --data-file=-

    # Create Google API Key (Optional, if not using ADC)
    gcloud secrets create GOOGLE_API_KEY --replication-policy="automatic"
    echo -n "AIzaSy..." | gcloud secrets versions add GOOGLE_API_KEY --data-file=-

    # Create DB_HOST secret (Required by current backend config)
    # Use the IP address output by Terraform (module.database.instance_ip)
    gcloud secrets create DB_HOST --replication-policy="automatic"
    echo -n "10.x.x.x" | gcloud secrets versions add DB_HOST --data-file=-
    ```

## Phase 4: Application Deployment

### Step 7: Finalize Database Setup
1.  **Enable pgvector:**
    Connect to your new Cloud SQL instance (via Cloud Shell or a Jump Host) and run:
    ```sql
    CREATE EXTENSION IF NOT EXISTS vector;
    ```
    *Note: The password for the `postgres` user is in the Secret Manager under `[project-id]-cloudsql-password`.*

### Step 8: Deploy Code
Terraform deployed "Hello World" placeholders. Now, push your code to deploy the actual apps.

1.  **Trigger Cloud Build:**
    ```bash
    # Deploy Backend
    gcloud builds submit --config cloudbuild-backend.yaml .

    # Deploy Frontend
    gcloud builds submit --config cloudbuild-frontend.yaml .
    ```

### Step 9: DNS Setup
1.  Get the Load Balancer IP:
    ```bash
    cd terraform && terraform output public_ip
    ```
2.  Update your DNS provider (e.g., GoDaddy, Cloudflare) to point your domain (e.g., `ai.your-domain.com`) to this IP.
3.  Wait 15-30 minutes for the managed SSL certificate to provision.

---

# Disaster Recovery Plan
This document outlines the procedures for recovering the platform's critical data stores: **Cloud SQL** (PostgreSQL) and **Firestore**.

## 1. Cloud SQL (PostgreSQL) Recovery
Our Cloud SQL instance is configured with:
- **Automated Backups:** Retained for 7 days.
- **Point-in-Time Recovery (PITR):** Allows restoration to any second within the retention window.
- **Deletion Protection:** Prevents accidental deletion of the instance.

### Scenario A: Accidental Data Corruption (PITR)
*Objective: Restore the database to a state before the corruption occurred (e.g., 10 minutes ago).*

1.  **Identify the Timestamp:** Determine the exact UTC time just before the error occurred.
2.  **Perform Restore (Clone):** Cloud SQL restores are performed by creating a *new* instance from the backup.
    ```bash
    # Example: Restore to a new instance named 'restored-db-instance'
    gcloud sql instances clone <SOURCE_INSTANCE_ID> restored-db-instance \
        --point-in-time "2023-10-27T13:00:00Z"
    ```
3.  **Verify Data:** Connect to `restored-db-instance` and verify the data integrity.
4.  **Switch Traffic:** Update the application secrets to point to the new instance IP/Host, or promote the new instance to be the primary if using a proxy.

### Scenario B: Full Instance Loss (Backup Restore)
*Objective: Restore from the last successful nightly backup.*

1.  **List Backups:**
    ```bash
    gcloud sql backups list --instance=<INSTANCE_ID>
    ```
2.  **Restore:**
    ```bash
    gcloud sql backups restore <BACKUP_ID> --restore-instance=<TARGET_INSTANCE_ID>
    ```

---

## 2. Firestore Recovery
Our Firestore database is configured with a **Daily Backup Schedule** retained for 7 days.

### Restore Procedure
1.  **List Available Backups:**
    ```bash
    gcloud firestore backups list --location=<REGION>
    ```
    *Note the `resource name` of the backup you wish to restore.*
2.  **Restore to a New Database:**
    Firestore does not support in-place restores. You must restore to a new database ID.
    ```bash
    gcloud firestore databases restore \
        --source-backup=projects/<PROJECT_ID>/locations/<REGION>/backups/<BACKUP_ID> \
        --destination-database=restored-firestore-db
    ```
3.  **Update Application:**
    Update the backend configuration `FIRESTORE_DATABASE_ID` or similar config) to point to `restored-firestore-db`.

---

## 3. Post-Recovery Checklist
- [ ] **Verify Connectivity:** Ensure backend services can connect to the restored databases.
- [ ] **Data Integrity Check:** Run application-level smoke tests.
- [ ] **Re-enable Backups:** Ensure the new/restored instances have backup schedules re-applied (Terraform apply might be needed).

---

**Acknowledgements**
✨ Google ML Developer Programs and Google Developers Program supported this work by providing Google Cloud Credits (and awesome tutorials for the Google Developer Experts)✨