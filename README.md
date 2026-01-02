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

# Deployment Guide: A Step-by-Step Walkthrough

## Phase 1: Pre-Terraform Setup (Manual Steps)
These actions prepare your Google Cloud project and grant the necessary permissions for Terraform and Cloud Build to run.

### Step 1: Create a Google Cloud Project via Console
First, create your Google Cloud project through the Google Cloud Console if you haven't already.

### Step 2: Authenticate in Google Cloud via CLI + Set Region and Project
Log in and set up your project configuration.
```bash
# Log in to your Google Cloud account
gcloud auth login

# Set the project you will be working on
gcloud config set project [YOUR_PROJECT_ID]

# Set your preferred region
gcloud config set compute/region [YOUR_REGION]

# Link your project to a billing account (required to use most services)
gcloud beta billing projects link [YOUR_PROJECT_ID] --billing-account [YOUR_BILLING_ACCOUNT_ID]
```

### Step 3: Enable Required Google Cloud APIs
Terraform will require enablement of these resources.
```bash
# Enable all necessary APIs for the platform
gcloud services enable \
  compute.googleapis.com \
  iam.googleapis.com \
  iamcredentials.googleapis.com \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  secretmanager.googleapis.com \
  sqladmin.googleapis.com \
  firestore.googleapis.com \
  serviceusage.googleapis.com \
  servicenetworking.googleapis.com \
  dlp.googleapis.com
```

### Step 4: Grant Permissions
#### Grant Permissions to the Cloud Build Service Account
The `cloudbuild-*.yaml` files build and deploy the applications. The default Cloud Build service account needs permission to do so.
```bash
# Get your project number
PROJECT_NUMBER=$(gcloud projects describe $(gcloud config get-value project) --format="value(projectNumber)")

# Grant Cloud Build permissions to deploy to Cloud Run and manage associated resources
gcloud projects add-iam-policy-binding $(gcloud config get-value project) \
  --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding $(gcloud config get-value project) \
  --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
  --role="roles/iam.serviceAccountAdmin"

# Grant Cloud Build permissions to push images to Artifact Registry
gcloud projects add-iam-policy-binding $(gcloud config get-value project) \
  --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
  --role="roles/artifactregistry.writer"
```

#### Grant Permissions to the Backend Service Account
The backend agent uses Google Cloud DLP for de-identifying PII. The backend service account needs permission to call the DLP API.
```bash
# Grant the Backend service account permission to use DLP
gcloud projects add-iam-policy-binding $(gcloud config get-value project) \
  --member="serviceAccount:ai-backend-sa@$(gcloud config get-value project).iam.gserviceaccount.com" \
  --role="roles/dlp.user"
```

### Step 5: Create Secrets in Secret Manager
To deploy this platform securely, you must configure the following secrets in **Google Secret Manager**.

| Secret Name | Description | Required By |
| :--- | :--- | :--- |
| `PROJECT_ID` | Your Google Cloud Project ID. | Backend |
| `REGION` | GCP region (e.g., `us-central1`). | Backend, Ingest |
| `DB_HOST` | IP of your Cloud SQL instance (or `127.0.0.1` if using the Cloud SQL Auth Proxy). | Backend, Ingest |
| `DB_USER` | Database username (default: `postgres`). | Backend, Ingest |
| `DB_PASSWORD` | Password for the Cloud SQL (Postgres) 'postgres' user. | Backend, Terraform |
| `DB_NAME` | Name of the database (default: `postgres`). | Backend, Ingest |
| `DATABASE_URL` | Full SQLAlchemy connection string (e.g., `postgresql://user:pass@10.x.x.x/postgres`). | Backend |
| `REDIS_HOST` | Hostname/IP of the Redis instance. | Backend |
| `GOOGLE_API_KEY` | (Optional) API Key for Gemini/Vertex AI if not using ADC. | Backend |
| `STRIPE_API_KEY` | Stripe Secret Key `sk_live_...`). | Backend |
| `STRIPE_WEBHOOK_SECRET` | Stripe Webhook Signing Secret `whsec_...`). | Backend |
| `BACKEND_URL` | The internal URL of the backend (e.g. `http://localhost:8080`). Used by the server-side proxy. | Frontend |
| `NEXT_PUBLIC_FIREBASE_API_KEY` | Firebase API Key. | Frontend |
| `NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN` | Firebase Auth Domain. | Frontend |
| `NEXT_PUBLIC_FIREBASE_PROJECT_ID` | Firebase Project ID. | Frontend |
| `NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET` | Firebase Storage Bucket. | Frontend |
| `NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID` | Firebase Messaging Sender ID. | Frontend |
| `NEXT_PUBLIC_FIREBASE_APP_ID` | Firebase App ID. | Frontend |

> **Note on Authentication:** The frontend uses Firebase. For local backend testing, you can use the `Bearer MOCK_TOKEN` header if `DEBUG=true` is set on the backend.
> **Note:** Frontend configuration variables (e.g., `NEXT_PUBLIC_FIREBASE_API_KEY`, `BACKEND_URL`) are not strictly "secrets" but should be managed via Cloud Run Environment Variables or build args.

### Step 6: Create Bucket for Disaster Recovery and Google Cloud Functions
Set up Cloud Storage buckets for disaster recovery and Cloud Functions document ingestion.

### Step 7: Set Up Environment Variables
Configure environment variables for both backend and frontend applications (see Local Development Setup section for details).

### Step 8: Set Up Firebase
**Configure Firebase (Detailed Steps):**
The frontend uses Firebase for User Authentication.
1.  Go to [Firebase Console](https://console.firebase.google.com).
2.  **Create a Project:** Select your existing Google Cloud Project or create a new one.
3.  **Enable Authentication:**
    *   Navigate to **Build** -> **Authentication**.
    *   Click **Get Started**.
    *   Select **Sign-in method** tab.
    *   Enable **Email/Password** and **Google**.
4.  **Get Configuration:**
    *   Click the **Gear icon** (Project Settings) -> **General**.
    *   Scroll down to **Your apps**.
    *   Click the **</> (Web)** icon.
    *   Register the app (e.g., "AI Platform Local").
    *   **Copy the `firebaseConfig` object.**

---

## Local Development Setup
This section guides you through running the entire stack (Database, Backend, Frontend) on your machine.

### Step 9: Test Frontend and Backend Locally

#### Local Infrastructure (Database & Cache)
Instead of connecting to remote Cloud SQL instances (which is slow and insecure for local dev), we will use Docker to spin up a local **PostgreSQL with pgvector** and **Redis**.

1.  Get the file named `docker-compose.yaml` in the root directory:
2.  **Start the Services:**
    Open your terminal in the project root and run:
    ```bash
    docker-compose up -d
    ```
    *   Verify they are running with `docker ps`. You should see two containers (postgres and redis) up and healthy.
    *   **Note:** If you don't have `docker-compose` installed, you might need to use `docker compose up -d` (v2).
3.  **Initialize the Vector Database & Users Table:**
    You need to enable the `vector` extension and ensure the `users` table exists.
    Connect to your local database (using DBeaver, pgAdmin, or command line):
    ```bash
    # Get container ID and connect to the local docker container
    docker ps
    docker exec -it <container_id_of_postgres> psql -U postgres
    ```
    Run the following SQL commands inside the psql prompt:
    ```sql
    CREATE EXTENSION IF NOT EXISTS vector;
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
    CREATE TABLE IF NOT EXISTS users (
        email VARCHAR PRIMARY KEY,
        is_active BOOLEAN DEFAULT FALSE,
        stripe_customer_id VARCHAR,
        subscription_status VARCHAR DEFAULT 'inactive',
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ
    );
    INSERT INTO users (email, is_active, subscription_status)
    VALUES ('test@example.com', true, 'active');
    ```

#### Backend Setup (FastAPI)
The backend `rag_chain.py`) relies on **Google Cloud Firestore** for chat history and **Vertex AI** for embeddings. For local development, we connect to these real cloud services securely.

1.  **GCP Authentication (Required for Firestore & Vertex AI):**
    The backend uses Application Default Credentials (ADC) to connect to GCP.
    ```bash
    gcloud auth application-default login
    ```
    *   This will open a browser window to login. Ensure you select the project defined in your `.env`.
    *   **Firestore Setup:** Ensure you have created a Firestore database (Native Mode) in your Google Cloud Project via the Console.
2.  **Configure Environment Variables:**
    Create a `.env` file in the `backend-agent/` directory:
    ```bash
    PROJECT_ID="your-google-cloud-project-id"
    REGION="us-central1"
    # Database (Matches docker-compose)
    DB_HOST="localhost"
    DB_USER="postgres"
    DB_PASSWORD="password"
    DB_NAME="postgres"
    DATABASE_URL="postgresql+asyncpg://postgres:password@localhost:5432/postgres"
    # Redis
    REDIS_HOST="localhost"
    # Stripe (Get these from Stripe Dashboard -> Developers -> API Keys)
    STRIPE_API_KEY="sk_test_..."
    STRIPE_WEBHOOK_SECRET="whsec_..."
    # Google Cloud
    # GOOGLE_API_KEY is optional if you have run 'gcloud auth application-default login'
    ```
3.  **Install Dependencies & Run:**
    ```bash
    cd backend-agent
    python3 -m venv myenv
    source myenv/bin/activate
    pip install -r requirements.txt
    # Run the server
    uvicorn main:app --reload --host 0.0.0.0 --port 8080
    ```
    The backend is now running at `http://localhost:8080`.
4.  **Ingest Documents (RAG):**
    To test the vector search, you need to ingest some data into your local database.
    *   Place PDF files in `backend-agent/data/`.
    *   Run the ingestion script:
    ```bash
    python ingest.py
    ```

#### Frontend Setup (Next.js)
1.  **Configure Environment Variables:**
    Create a `.env.local` file in the `frontend-nextjs/` directory and populate it with your Firebase keys:
    ```bash
    NEXT_PUBLIC_FIREBASE_API_KEY="AIzaSy..."
    NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN="your-project.firebaseapp.com"
    NEXT_PUBLIC_FIREBASE_PROJECT_ID="your-project"
    NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET="your-project.appspot.com"
    NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID="123..."
    NEXT_PUBLIC_FIREBASE_APP_ID="1:123..."
    # Backend URL (Server-side proxy points here)
    BACKEND_URL="http://localhost:8080"
    ```
2.  **Install & Run:**
    ```bash
    cd frontend-nextjs
    npm install
    npm run dev
    ```
    The frontend is now running at `http://localhost:3000`.

#### Stripe Webhooks (Optional)
To test payments locally:
```bash
stripe listen --forward-to localhost:8080/webhook
```
Copy the webhook signing secret output by this command into your backend `.env` file `STRIPE_WEBHOOK_SECRET`).

---

## CI/CD Implementation

### Step 10: Set Up CI/CD - Create Cloud Build Trigger
This section covers the automated CI/CD pipeline using Cloud Build triggers connected to GitHub.

#### Overview
The CI/CD infrastructure automates the build and deployment process whenever changes are pushed to the repository. It consists of:

**Artifact Registry:** A Docker repository (cloud-run-source-deploy) for storing container images.
**Cloud Build Triggers:** Automated triggers that watch specific paths in the repository and execute the corresponding build configurations.

#### Steps:
1. Connect GitHub to GCP (Prerequisite):
   * Go to the Google Cloud Console > Cloud Build > Triggers (https://console.cloud.google.com/cloud-build/triggers).
   * Click Manage Repositories > Connect Repository.
   * Select GitHub and follow the authorization flow (this installs the Google Cloud Build App on your GitHub account).
   * If you skip this, Terraform will fail to create the triggers even if you provide the correct names.

---

## Phase 2: Deploy via Terraform

### Step 11: Deploy via Terraform
Run Terraform to provision all infrastructure.

```bash
terraform init
terraform plan
terraform apply
```

---

## Phase 3: Post-Terraform Actions & Verification
After `terraform apply` completes successfully, perform these final steps to make the application fully functional.

### Step 12: Enable pgvector in Cloud SQL
The Terraform code correctly provisions the Cloud SQL instance with flags optimized for `pgvector`, but it cannot enable the extension itself.

1.  **Connect to the Cloud SQL instance:** Use your preferred PostgreSQL client (like `psql` or a GUI tool) to connect to the database using the IP address and the password stored in Secret Manager.
2.  **Run the SQL Command:** Execute the following command in your database to enable the vector extension.
    ```sql
    CREATE EXTENSION IF NOT EXISTS vector;
    ```

### Update DNS "A" Record
The Terraform `ingress` module provisioned a static IP for the load balancer. You must point your domain to it.

1.  **Get the Load Balancer IP Address:**
    ```bash
    terraform output public_ip
    ```
2.  **Update Your DNS:**
    *   Go to your domain registrar (e.g., Google Domains, Cloudflare, GoDaddy).
    *   Create or update the **"A" record** for the domain you specified in `terraform.tfvars` (e.g., `ai.your-company.com`).
    *   Point it to the IP address from the Terraform output.

**Note:** The managed SSL certificate and HTTPS routing will not work until your domain correctly resolves to the load balancer's IP address.

### Set the AI Provider API Key
The backend's Terraform configuration references a secret for the AI provider's API key. You must update the placeholder value with your real key.
```bash
# Add the first version of the secret with your actual API key
gcloud secrets versions add ai-provider-api-key --data-file="/path/to/your/api_key.txt"
```

### Trigger Cloud Build to Deploy Your Code
Terraform has set up the infrastructure, but it uses a placeholder "hello world" container. You now need to run your Cloud Build pipelines to deploy your actual frontend and backend applications with the new resiliency features.
```bash
# Deploy the backend agent
gcloud builds submit --config cloudbuild-backend.yaml .

# Deploy the Next.js frontend
gcloud builds submit --config cloudbuild-frontend.yaml .
```

**Final step:** Replaces the placeholder services with your actual Next.js and FastAPI applications, making the platform live.

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