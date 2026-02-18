# From PoC to Production: Enterprise-Grade AI Platform for Multi-Agent Systems

This repository contains a full-stack, secure AI platform deployed on Google Cloud via Terraform. It enables secure, RAG-based chat with enterprise-grade security and automated PII protection, accessible to public users via Firebase Authentication.

## Architecture Overview

![Google Cloud Architecture](images/Google_Cloud_Architecture.jpg)
_Figure 1: Google Cloud Platform Architecture_

![AWS Architecture](images/AWS_Architecture.jpg)
_Figure 2: Correspondent AWS Architecture_

---

## Component Details

### Frontend (Next.js Agent)

- **Location:** `/frontend-nextjs`
- **Tech:** React 18, Tailwind CSS, Lucide Icons, Firebase.
- **Resilience:** **Circuit Breaker** `opossum` for fail-fast backend communication.
- **Security:** Acts as a secure proxy to the Backend; Authentication handled via Firebase.
- **Scalability:** Configured with `min_instances = 1` for zero-latency response.
- **Reliability:** Implements circuit breakers (opossum) for external API calls.
- **Testing:** Comprehensive coverage with Jest (Unit) and Playwright (E2E).

#### Frontend Architecture Details

The frontend is a modern Next.js application using the App Router with the following structure:

**Core Components:**

- **`AuthProvider.tsx`**: The cornerstone of the application's authentication system. Uses Firebase Authentication to manage user authentication state and protect routes from unauthorized access.
- **`ChatInterface.tsx`**: The main chat interface providing a real-time, streaming chat experience. Tightly integrated with the backend API, it handles authentication and payment-related errors gracefully, redirecting users to the appropriate page when necessary.
- **`PaymentClient.tsx`**: Provides a seamless and secure payment experience using Stripe's Embedded Checkout. Guides users through the payment process with graceful error handling.

**Routing Structure:**

| Route              | Description                                               |
| ------------------ | --------------------------------------------------------- |
| `/`                | Landing page - main entry point, funnels users to payment |
| `/chat`            | Main chat interface                                       |
| `/login`           | Login page                                                |
| `/payment`         | Payment page                                              |
| `/payment-success` | Displayed after successful payment                        |

**API Routes (Server-Side):**

- **`/api/chat`**: Acts as a secure and resilient proxy to the backend chat service. Uses a circuit breaker to prevent cascading failures and OIDC tokens for secure service-to-service authentication. Streams responses from the backend to the client for real-time chat.
- **`/api/check-payment-status`**: Checks the status of a Stripe Checkout session and sets a cookie to persist payment status client-side.
- **`/api/create-checkout-session`**: Creates a Stripe Checkout session and returns the `client_secret` for displaying the Stripe payment form.

**Security Features:**

- Secure handling of API keys and secrets
- OIDC tokens for service-to-service authentication
- User authentication tokens forwarded to backend for authorization

### Backend (FastAPI Agent)

- **Location:** `/backend-agent`
- **Neural Core:** Orchestrates RAG using LangChain and Vertex AI.
- **Resilience:** **Retries** (`tenacity`) for transient errors & **OpenTelemetry** tracing.
- **Vector DB:** Cloud SQL for PostgreSQL 16 with `pgvector` and `asyncpg`.
- **Networking:** Set to `INGRESS_TRAFFIC_INTERNAL_ONLY` to ensure it is unreachable from the public internet.
- **Observability:** Full OpenTelemetry instrumentation (Traces exported to Google Cloud Trace).
- **Security:** Rate limiting (slowapi) and integration with Google Cloud DLP (Data Loss Prevention) suggests a focus on enterprise compliance.

#### Backend Architecture Details

The backend is a robust FastAPI application with a strong focus on security, observability, and scalability.

**API Endpoints:**

| Endpoint   | Description                                                    |
| ---------- | -------------------------------------------------------------- |
| `/health`  | Standard health check endpoint                                 |
| `/webhook` | Stripe webhook handler for managing user subscriptions         |
| `/chat`    | Primary, non-streaming chat endpoint                           |
| `/stream`  | Streaming version of chat endpoint for real-time communication |

**Security Implementation:**

- **Rate Limiting:** API is rate-limited to 10 requests per minute per IP address to prevent abuse.
- **Input Validation:** Message size validation to prevent Denial-of-Service (DoS) attacks.
- **Authentication:** The `get_current_user` dependency ensures all chat requests are authenticated.
- **IDOR Prevention:** Session IDs are scoped to authenticated users, preventing cross-user session access.

**Observability:**

- **Structured Logging:** Provides clear and actionable log data.
- **Distributed Tracing:** OpenTelemetry integration for monitoring and debugging in microservices architecture.

**Data Layer:**

- **Data Model:** PostgreSQL database stores user information including subscription status and Stripe customer ID. The `User` model is defined using SQLAlchemy.
- **CRUD Operations:** All database operations (Create, Read, Update, Delete) are encapsulated in `crud.py` for maintainability and testability.
- **Subscription Management:** Tight integration with Stripe; the `/webhook` endpoint listens for Stripe events and updates user subscription status.
- **Secure Database Connection:** Database URL fetched from Google Secret Manager.

**Knowledge Base (RAG Pipeline):**

The `ingest.py` script builds and maintains the knowledge base:

1. **Document Ingestion:** Ingests PDF documents from the `./data` directory using `DirectoryLoader` and `PyPDFLoader` from LangChain.
2. **Text Chunking:** Uses `RecursiveCharacterTextSplitter` to break documents into manageable chunks for efficient RAG retrieval.
3. **Vector Embeddings:** Uses `textembedding-gecko@003` model from Vertex AI to generate semantic vector embeddings.
4. **Vector Store:** Uses `PGVector` to store document chunks and embeddings in PostgreSQL (AlloyDB) for scalable similarity searches.
5. **Data Upsert:** The `add_documents` function upserts data to keep the knowledge base up-to-date.

**Core AI Capabilities:**

- **Intelligent Query Routing:** Distinguishes between general conversation and knowledge-base queries
- **Retrieval-Augmented Generation (RAG):** Retrieves relevant information from PDF documents for accurate answers
- **Conversational Memory:** Remembers previous turns for context-aware responses
- **Multi-Layered Security:** Protection against common web vulnerabilities
- **Data Loss Prevention (DLP):** Prevents leakage of sensitive information
- **Resilient Design:** Handles transient errors and network failures

### Infrastructure (Terraform Modules)

- **`cicd`**: CI/CD pipeline.
- **`network`**: VPC, Subnets, Cloud NAT, and PSA.
- **`compute`**: Cloud Run services and granular IAM policies.
- **`database`**: Cloud SQL (PostgreSQL) and Firestore (Chat History).
- **`redis`**: Memorystore for semantic caching.
- **`ingress`**: Global Load Balancer, Cloud Armor, and SSL.
- **`billing_monitoring`**: Budgets, Alert Policies, and Notification Channels.
- **`function`**: Google Cloud Functions for PDF Ingestion.
- **`storage`**: Buckets and lifecycle policies.

The infrastructure is defined as code (IaC) using modular Terraform, adhering to Google Cloud best practices:

- **Compute:** Decoupled frontend and backend services (likely Cloud Run) and event-driven Cloud Functions for async processing.
- **Data Layer:**
  **Primary DB:** Cloud SQL (PostgreSQL) with pgvector for vector similarity search.
  **Caching:** Cloud Memorystore (Redis) for session/cache management.
  **Storage:** Cloud Storage for raw assets (PDFs).
- **Networking:** Custom VPC with private subnets and specific ingress controls.
- **Security:** IAM roles are granularly assigned (e.g., specific service accounts accessing specific secrets).

#### Terraform Architecture Assessment

The Terraform configuration adheres to Google Cloud best practices for security, scalability, and maintainability with modular design, explicit dependency management, and a security-first approach.

**Key Strengths:**

**Security-First Design:**

- **Network:** Private VPC, private subnets, and Cloud NAT gateway ensure services are not exposed to the public internet.
- **Database:** Cloud SQL instance has no public IP and uses IAM authentication.
- **Secrets Management:** Google Secret Manager stores all sensitive information.
- **Ingress:** Cloud Armor with pre-configured OWASP Top 10 rules and rate limiting provides strong first-line defense.

**Scalability and Resilience:**

- **Serverless:** Cloud Run for frontend and backend enables automatic traffic-based scaling.
- **Load Balancing:** Global external HTTPS load balancer distributes traffic efficiently with a single entry point.
- **CDN:** Cloud CDN improves performance by caching static assets closer to users.
- **Health Checks:** Startup and liveness probes for the backend service improve reliability.

**Automation:**

- The CI/CD pipeline in the `cicd` module automates build and deployment processes.

**Frontend-Backend Flow Alignment:**

- **Service Communication:** The `compute` module correctly configures Cloud Run services communication with secure environment variables and secrets.
- **Data Flow:** The `database`, `redis`, and `storage` modules provision necessary data stores; the `function` module sets up the RAG data ingestion pipeline.
- **Ingress and Egress:** The `ingress` module routes traffic to the frontend; the `network` module ensures outbound internet access through Cloud NAT.

## Architecture Decisions & Rationale

1. **Authentication: Firebase Authentication vs. Google Identity (IAP)**
   I explicitly chose **Firebase Authentication** over Identity-Aware Proxy (IAP) for this architecture.
   - **Seamless Frontend Integration:** Firebase provides a rich, client-side SDK that integrates natively with the Next.js application, offering a smoother, customizable user experience (login pages, social providers) compared to IAP's rigid, infrastructure-level interception.
   - **Public-Facing Scalability:** Unlike IAP, which is optimized for internal enterprise tools (Google Workspace identities), Firebase Authentication is designed for consumer-scale applications (B2C), supporting millions of users with a generous free tier and ease of external sign-ups.
   - **Developer Experience:** It allows for rapid prototyping and deployment without complex load balancer configurations, while still maintaining high security standards through JWT verification on the backend using the Firebase Admin SDK.
2. **Communication: Asyncio vs. Pub/Sub**
   While Pub/Sub is excellent for decoupled, asynchronous background tasks, I utilize **Python's asyncio** within FastAPI for the chat interface.
   - **Real-Time Requirement:** Chat users expect immediate, streaming responses. Pub/Sub is a "fire-and-forget" mechanism designed for background processing, not for maintaining the open, bidirectional HTTP connections required for streaming LLM tokens to a user in real-time.
   - **Concurrency:** `asyncio` allows a single Cloud Run instance to handle thousands of concurrent waiting connections (e.g., waiting for Vertex AI to reply) without blocking, providing high throughput for chat without the architectural complexity of a message queue.
3. **Event-Driven Ingestion: Cloud Functions**
   I moved the document ingestion logic from a manual script to a **Google Cloud Function** triggered by Cloud Storage events.
   - **Automation:** Uploading a PDF to the `data_bucket` automatically triggers the function to parse, chunk, embed, and upsert the document into the vector database.
   - **Efficiency:** This is a serverless, event-driven approach. Resources are only consumed when a file is uploaded, rather than having a long-running service waiting for input.
   - **Scalability:** Each file upload triggers a separate function instance, allowing parallel processing of mass uploads without blocking the main chat application.

## AI Engine & Knowledge Core: Memory & RAG Implementation

The Backend Agent is designed as a stateful, retrieval-augmented system that balances high-performance search with secure session management.

### 1. Short-Term Memory (Session Context)

- **Storage:** Utilizes **Google Cloud Firestore (Native Mode)** for low-latency persistence of chat history.
- **Implementation:** Leverages `FirestoreChatMessageHistory` within the LangChain framework.
- **Security & Isolation:** Every session is cryptographically scoped to the authenticated user's email (`user_email:session_id`). This ensures strict multi-tenancy where users can never access or "leak" into another's conversation history (IDOR protection).
- **Context Injection:** The system automatically retrieves the last $N$ messages and injects them into the history placeholder of the RAG prompt, enabling multi-turn, context-aware dialogue.

### 2. Long-Term Memory (Knowledge Base)

- **Vector Database:** Powered by **PostgreSQL 16 (Cloud SQL)** with the vector extension (`pgvector`).
- **Retrieval Logic:** Employs semantic similarity search using `VertexAIEmbeddings` (`textembedding-gecko@003`). For every query, the engine retrieves the top 5 most relevant chunks ($k=5$) to provide grounded context to the LLM.
- **Semantic Caching:** Integrated with **Redis (Memorystore)** using a `RedisSemanticCache`. If a user asks a question semantically similar to a previously cached query (threshold: 0.05), the system returns the cached response instantly, bypassing the LLM to save cost and reduce latency.

### 3. RAG Specifications & Document Ingestion

- **Ingestion Pipeline:** A specialized `ingest.py` script handles the transformation of raw data into "AI-ready" vectors.
- **Smart Chunking:** Uses the `RecursiveCharacterTextSplitter` to maintain semantic integrity:
  - **Chunk Size:** 1000 characters/tokens.
  - **Chunk Overlap:** 200 characters (ensures no loss of context at the edges of chunks).
  - **Separators:** Prioritizes splitting by double newlines (paragraphs), then single newlines, then spaces.
- **Document Support:** Includes a `DirectoryLoader` with `PyPDFLoader` to automatically parse and index complex PDF structures.

### 4. Cache Implementation

- **Cost Savings:** You pay for the system instruction tokens once per hour (cache creation) instead of every single request.
- **Latency:** The model doesn't need to re-process the large system prompt for every user query, leading to faster Time to First Token (TTFT).
- **Implicit vs. Explicit:** I relied on Implicit Caching for the short-term chat history (managed automatically by Gemini) and implemented Explicit Caching for the static, heavy system prompt.

## Security & Resilience: A Multi-Layered Defense

This platform implements a robust, multi-layered security strategy. The codebase and infrastructure have been hardened against the following threats:

### 1. Web & Application Security (OWASP Top 10)

- **SQL Injection (SQLi) Protection:**
  - **Infrastructure Level:** Google Cloud Armor is configured with pre-configured WAF rules (`sqli-v33-stable`) to filter malicious SQL patterns at the edge.
  - **Application Level:** The backend uses `asyncpg` (via LangChain's PGVector), which strictly employs parameterized queries, ensuring user input is never executed as raw SQL.
- **Cross-Site Scripting (XSS) Protection:**
  - **Infrastructure Level:** Cloud Armor WAF rules (`xss-v33-stable`) detect and block malicious script injection attempts.
  - **Framework Level:** Next.js (Frontend) automatically sanitizes and escapes content by default, and the backend returns structured JSON to prevent direct script rendering.
- **Broken Access Control & IDOR (Insecure Direct Object Reference):**
  - **Verified Identity (Firebase):** The frontend acts as a Secure Proxy. It captures the user's identity from Firebase Authentication tokens (`X-Firebase-Token` header) and propagates it to the backend for verification.
  - **Session Isolation:** Chat histories are cryptographically scoped to the authenticated user's identity (`user_email:session_id`), preventing IDOR attacks where one user could access another's private history.

### 2. DDoS & Resource Abuse Protection

- **Edge Protection:** Cloud Armor implements a global rate-limiting policy (500 requests/min per IP) and a "rate-based ban" to mitigate large-scale volumetric DDoS and brute-force attacks.
- **Application Resilience:** The backend core utilizes `slowapi` to enforce granular rate limiting (5 requests/min per user) specifically for expensive LLM operations, protecting against cost-based denial-of-service and resource exhaustion.
- **Input Validation:** Pydantic models in the backend enforce a strict 10,000-character limit on user messages to prevent memory-exhaustion attacks.

### 3. AI & LLM Specific Security (OWASP Top 10 for LLM)

- **Prompt Injection Mitigation:** The RAG prompt template uses strict structural delimiters (`----------`) and prioritized system instructions to ensure the model adheres to its enterprise role and ignores adversarial overrides contained within documents or user queries.
- **Sensitive Data Leakage (PII):** Google Cloud DLP (Data Loss Prevention) is integrated into the core pipeline with a Regex Fast-Path and Asynchronous Threading. This automatically detects and masks PII in real-time without blocking the main event loop, ensuring high performance while minimizing API costs.
- **Knowledge Base Security:** Data is stored in a private Cloud SQL (PostgreSQL) instance reachable only via a Serverless VPC Access connector, ensuring the "Brain" of the AI is never exposed to the public internet.

### 4. MAESTRO Framework

- **Preventing Wallet Exhaustion (Rate Limiting & Input Validation)**

  - **Action:** Reduced API rate limit: 10/minute for authenticated users.
  - **Action:** Added a `validate_token_count` function (using a lightweight 4-char/token heuristic) to strictly enforce input size limits before processing, rejecting requests that exceed the limit (2000 tokens) with a 400 error.

- **RAG Hardening (Prompt Injection Defense)**

  - **Action:** Prompt Templates with Cache Hit and Cache Miss scenarios.
  - **Action:** "Sandwich Defense" using XML tagging (`<trusted_knowledge_base>`) and explicit instructions to ignore external commands found within the retrieved context.

- **Guardrail Layer (Improved Security Judge)**

  - **Action:** Regex `SecurityBlocker` for low-latency filtering of obvious attacks.
  - **Action:** The `security_judge_llm` uses a more specific system prompt acting as a specialized classifier ("SAFE" vs "BLOCKED").
  - **Action:** Google's Native Content Safety Settings (`HarmBlockThreshold.BLOCK_LOW_AND_ABOVE`) on the Judge model to leverage Vertex AI's built-in safety classifiers for Hate Speech, Dangerous Content, etc.

- **Model Safety (Generation Hardening)**
  - **Action:** Strict `SAFETY_SETTINGS` (blocking low and above harm probability) to the main RAG generation models (`ChatVertexAI`). This acts as a final line of defense against generating harmful content, even if prompt injection succeeds.

**Note on Streaming DLP:**
The current `protected_chain_stream` sanitizes the input but streams the output directly from the LLM to the client to maintain responsiveness. By enforcing the strict `SAFETY_SETTINGS` on the generation model itself, we have mitigated the risk of the model generating harmful content, serving as an effective output guardrail for the streaming endpoint.

## Enhanced Enterprise Architecture (Optimized)

This platform has been upgraded for production-scale performance, cost efficiency, and sub-second perceived latency:

### 1. Global Scalability & High Availability

- **Horizontal Autoscaling:** Both Frontend and Backend services are configured for automatic horizontal scaling in Cloud Run. They can scale from zero to hundreds of concurrent instances to handle massive traffic spikes.
- **Cold-Start Mitigation:** The Frontend service maintains a minimum of 1 warm instance `min_instance_count = 1`), ensuring immediate responsiveness and eliminating "cold start" latency for users.
- **Cloud SQL Read Pool:** While currently using a single instance for cost efficiency, the architecture is ready for a dedicated Read Replica in Cloud SQL. This horizontally scales read capacity for the vector database, ensuring that heavy document retrieval and search operations do not bottleneck the primary write instance.

### 2. Latency & Performance Optimization

- **Asynchronous I/O (Neural Core):** The backend is built on FastAPI and uses `asyncpg` for non-blocking database connections. This allows a single instance to handle thousands of concurrent requests with minimal resource usage.
- **Server-Sent Events (SSE):** Real-time token streaming from the LLM (Gemini 2.5 Flash) directly to the Next.js UI provides sub-second "Time-To-First-Token," creating a highly responsive user experience.
- **Asynchronous Thread Pooling:** Expensive operations like PII de-identification via Google Cloud DLP are offloaded to asynchronous background threads, preventing them from blocking the main request-response cycle.

### 3. Cost Control & Efficiency

- **Gemini 2.5 Flash Integration:** Utilizes the high-efficiency Flash model (`gemini-2.5-flash-preview-05-20`) for a 10x reduction in token costs and significantly lower latency compared to larger models.
- **DLP Fast-Path Guardrails:** Implemented a high-performance regex-based "pre-check" for PII. This intelligently bypasses expensive Google Cloud DLP API calls for clean content, invoking the API only when potential PII patterns are detected.
- **Global CDN Caching:** Google Cloud CDN is enabled at the Load Balancer level to cache static assets and common frontend resources globally, reducing origin server load and improving page load times.
- **Smart Storage Versioning:** Implemented Object Lifecycle Management on Cloud Storage buckets. Files are automatically transitioned to **Nearline** storage after 7 days, **Archive** storage after 30 days, and **deleted** after 90 days. This ensures disaster recovery capabilities (versioning is enabled) without indefinite storage costs.

## Performance & Scaling Roadmap

The current infrastructure is designed for high efficiency and is benchmarked to handle approximately 2,500 users per hour with the standard provisioned resources.

### How to Actually Reach 1,000,000 Users per Hour

To handle this load, you must change the architecture:
**Solution A: Offload Vector Search (Recommended)**
Use a specialized engine designed for high-throughput vector search.

- **Use:** Google Vertex AI Vector Search (formerly Matching Engine).
- **Why:** It is fully managed and designed to handle billions of vectors and thousands of QPS with <10ms latency.
- **Architecture Change:**
  - **Postgres:** Only stores Chat History and User Metadata (cheap writes).
  - **Vertex AI:** Handles the 2,800 QPS vector load.

## Payment & Subscription System

The platform now enforces a strict **"Login -> Pay -> Chat"** workflow using Stripe and Cloud SQL.

### 1. Payment Architecture

- **Source of Truth:** The Cloud SQL (PostgreSQL) database is the single source of truth for user subscription status.
- **Stripe Integration:**
  - **Webhooks:** A secure `/webhook` endpoint listens for `checkout.session.completed` and `invoice.payment_succeeded` events from Stripe.
  - **Automatic Activation:** When a payment succeeds, the webhook updates the user's `is_active` status in the `users` table.
- **Security Enforcement:**
  - **Backend Middleware:** The `get_current_user` dependency checks the database for every request. If `is_active` is false, it raises a `403 Forbidden` error.
  - **Frontend Redirect:** The frontend intercepts these 403 errors and automatically redirects the user to the `/payment` page.

### 2. Database Schema

The new `users` table tracks subscription state:

- `email` (Primary Key): Linked to Firebase Identity.
- `is_active` (Boolean): Grants access to the chat.
- `stripe_customer_id`: Links to the Stripe Customer.
- `subscription_status`: Status string (e.g., 'active', 'past_due').

---

## Prerequisites

Before running the project locally or deploying to the cloud, ensure you have the following installed:

- **Docker Desktop:** Required for running the local database (Postgres/Vector) and Redis.
- **Node.js (v18+):** For the Frontend.
- **Python (3.10+):** For the Backend.
- **Google Cloud CLI `gcloud`:** For authenticated access to GCP services (Vertex AI, Firestore, etc.).
- **Stripe CLI:** For testing payments locally.

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

- **Docker Desktop** (for running the database and cache locally).
- **Python 3.10+** (for the Backend).
- **Node.js 18+** (for the Frontend).
- **Google Cloud Project** with Firebase Authentication enabled.
- **Stripe Account** (for testing payments).

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
    - Go to **Project Settings > Service accounts**.
    - Click "Generate new private key".
    - Save this JSON file as `service-account-key.json` in the root of the `backend-agent` directory. **DO NOT COMMIT THIS FILE.**

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

- `roles/aiplatform.user`
- `roles/datastore.user`

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
    - Connect to local Postgres:
      ```bash
      psql postgres://postgres:password@localhost:5432/postgres
      ```
    - Find your user (created after login attempt) and update status:
      ```sql
      UPDATE users SET is_active = true WHERE email = 'your-email@example.com';
      ```
3.  **Chat:** You should now be able to access the chat interface. Messages will be:
    - Embedded via Vertex AI (Cloud).
    - Stored in Firestore (Cloud).
    - Vector-searched in Postgres (Local).

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
pytest
```

### Directory Structure

- `tests/conftest.py`: Contains test fixtures (e.g., `client` for API requests, mocks).
- `tests/test_main.py`: Contains API endpoint tests.

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

```bash
npx playwright install
npx playwright test                                                                                                            │
```

## Cloud Functions Testing

```bash
cd functions/pdf-ingest
pytest
```

### Directory Structure

- `__tests__/`: Contains the test files (e.g., `LandingPage.test.tsx`).
- `jest.config.ts`: Jest configuration.
- `jest.setup.ts`: Global test setup (e.g., loading `jest-dom` matchers).

---

# Deployment Guide: From Zero to Production

This guide outlines the step-by-step process to deploy your AI Platform to Google Cloud.

**Core Concept:** Your infrastructure (Terraform) creates the "shell" services first (using a placeholder image). Then, your CI/CD pipelines (Cloud Build) build the actual code and "fill" those shells with your application.

## Prerequisites

Before starting, ensure you have the following CLI tools installed: `gcloud`, `terraform`, `docker`, `npm`, `python`.

### 1. Google Cloud Project

Ensure you have a GCP project with billing enabled.

```bash
gcloud auth login
gcloud config set project [YOUR_PROJECT_ID]
gcloud config set compute/region us-central1
```

### 2. Firebase Project

1. Go to the [Firebase Console](https://console.firebase.google.com/).
2. Add a new project and select your _existing_ Google Cloud Project.
3. Enable **Authentication** (Google Provider, Email/Password, etc.).
4. Enable **Firestore** (Create Database → Native Mode → Select same region as your GCP resources, e.g., `us-central1`).
5. Go to **Project Settings** → **General** → **Your apps** → **Add app** (Web).
6. **Copy the Firebase Config SDK values** (apiKey, authDomain, projectId, storageBucket, messagingSenderId, appId). You will need these later.

### 3. Enable APIs

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

### 4. GitHub Connection (Critical)

Terraform creates Cloud Build triggers that watch your repo. You **must** connect your repository to Google Cloud Build manually before running Terraform.

1. Go to the [Cloud Build Triggers page](https://console.cloud.google.com/cloud-build/triggers).
2. Click **Manage Repositories** → **Connect Repository**.
3. Select **GitHub** and follow the authorization flow.
4. Select the repository containing this code.

### 5. Grant IAM Permissions

Terraform needs permission to manage IAM policies, and Cloud Build needs permission to deploy.

```bash
PROJECT_NUMBER=$(gcloud projects describe $(gcloud config get-value project) --format="value(projectNumber)")

gcloud projects add-iam-policy-binding $(gcloud config get-value project) \
  --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding $(gcloud config get-value project) \
  --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
  --role="roles/iam.serviceAccountAdmin"

gcloud projects add-iam-policy-binding $(gcloud config get-value project) \
  --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
  --role="roles/artifactregistry.writer"

gcloud projects add-iam-policy-binding $(gcloud config get-value project) \
  --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
  --role="roles/run.developer"

gcloud projects add-iam-policy-binding $(gcloud config get-value project) \
  --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"
```

## 6. Database Migration Guide

Your Cloud SQL instance is protected by a private IP configuration, which means you cannot connect to it directly from your local machine unless you are connected to the VPC (e.g., via VPN) or use a proxy.

The `init-db.sql` script MUST be executed to enable the `vector` extension, otherwise the RAG functionality will fail.

## Option 1: Using Cloud Shell (Easiest)

1.  Upload `init-db.sql` to your Cloud Shell.
2.  Connect to the database using the private IP (if Cloud Shell is configured for VPC access) or use the Auth Proxy.

### Using Cloud SQL Auth Proxy in Cloud Shell

1.  Enable the API:

    ```bash
    gcloud services enable sqladmin.googleapis.com
    ```

2.  Start the proxy (background):

    ```bash
    ./cloud_sql_proxy -instances=<PROJECT_ID>:<REGION>:<INSTANCE_NAME>=tcp:5432 &
    ```

3.  Run the script:
    ```bash
    psql "host=127.0.0.1 port=5432 sslmode=disable user=postgres dbname=postgres" -f init-db.sql
    ```
    _(You will need the password generated by Terraform. Check Secret Manager: `projects/<PROJECT_ID>/secrets/<PROJECT_ID>-cloudsql-password`)_

## Option 2: Using a Temporary VM (Bastion Host)

1.  Create a small VM in the same VPC (`<project-id>-vpc`) and Subnet as the database.
2.  SSH into the VM.
3.  Install the postgres client:
    ```bash
    sudo apt-get update && sudo apt-get install -y postgresql-client
    ```
4.  Upload or copy-paste `init-db.sql`.
5.  Connect and run:
    ```bash
    psql -h <DB_PRIVATE_IP> -U postgres -d postgres -f init-db.sql
    ```

## Verification

To verify the extension is installed, log into the database and run:

```sql
SELECT * FROM pg_extension WHERE extname = 'vector';
```

---

## Phase 1: Infrastructure Deployment (Terraform)

This step sets up the VPC, Database, Artifact Registry, Cloud Build Triggers, and the initial "Hello World" Cloud Run services.

### Step 1: Create `terraform.tfvars`

Navigate to the terraform directory and create a `terraform.tfvars` file:

```bash
cd terraform
```

```hcl
project_id         = "your-project-id"
region             = "us-central1"
domain_name        = "ai.your-domain.com"
github_owner       = "your-github-username"
github_repo_name   = "your-repo-name"
billing_account    = "000000-000000-000000"
notification_email = "admin@example.com"
```

### Step 2: Run Terraform

```bash
terraform init
terraform validate
terraform plan -out=after_review.tfplan
terraform apply after_review.tfplan
```

Type `yes` when prompted. This process will take 15-20 minutes.

In case of error:

```bash
terraform state list #see what Terraform thinks it successfully created

## IF state saved

# Fix errors

terraform plan
terraform apply

# ELSE

terraform import <resource_type>.<name> <existing_id>
terraform apply
```

**What gets created:**

- VPC Network & Serverless Access
- Cloud SQL (PostgreSQL) & Redis
- Cloud Run Services (Frontend & Backend) with placeholder images
- Cloud Function (PDF Ingest)
- Cloud Build Triggers
- Secret Manager placeholders

---

## Phase 2: Configure CI/CD Triggers

The Frontend build requires your Firebase keys to be "baked" into the Docker image at build time.

### Frontend Trigger Configuration

1. Go to **Google Cloud Console** → **Cloud Build** → **Triggers**.
2. Locate the `frontend-nextjs-trigger` and click **Edit**.
3. Scroll down to **Substitution variables**.
4. Add the following variables using the Firebase values from Prerequisites:

| Variable Name                               | Description                                                 |
| :------------------------------------------ | :---------------------------------------------------------- |
| `_NEXT_PUBLIC_FIREBASE_API_KEY`             | Your Firebase API Key                                       |
| `_NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN`         | Your Firebase Auth Domain (e.g., `project.firebaseapp.com`) |
| `_NEXT_PUBLIC_FIREBASE_PROJECT_ID`          | Your Firebase Project ID                                    |
| `_NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET`      | Your Firebase Storage Bucket (e.g., `project.appspot.com`)  |
| `_NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID` | Your Firebase Messaging Sender ID                           |
| `_NEXT_PUBLIC_FIREBASE_APP_ID`              | Your Firebase App ID                                        |

5. Click **Save**.

**Security Note:** Since these variables are prefixed with `NEXT_PUBLIC_`, Next.js will bundle them into the client-side JavaScript code. They are safe to be exposed to the browser (as they are required for the Firebase client SDK to work), but ensure your Firebase Security Rules are configured correctly.

### Backend Trigger Configuration

The backend deployment is simpler because environment variables are injected at **runtime** via Cloud Run, not build time.

1. Go to **Cloud Build** → **Triggers**.
2. Click **Create Trigger** (or edit the existing `backend-agent-trigger`).
3. Configure with:
   - **Name**: `backend-deploy`
   - **Event**: Push to a branch
   - **Source**: Your repository and branch (e.g., `^main$`)
   - **Configuration**: Cloud Build configuration file
   - **Location**: `cloudbuild-backend.yaml`
   - **Ignored Files** (Optional): `frontend-nextjs/**`
4. Click **Save/Create**.

It will: **1. Test** (Run pytest/npm test) -> **2. Build** -> **3. Deploy**

---

## Phase 3: Configure Secrets

Terraform created the _containers_ for your secrets, but you need to add the _values_.

### Stripe Keys

1. Find the secret `STRIPE_SECRET_KEY` in Secret Manager and add a new version with your Stripe **Secret Key**.
2. Find the secret `STRIPE_PUBLISHABLE_KEY` and add your Stripe **Publishable Key**.

### Additional Required Secrets

Create these secrets manually:

```bash
# Stripe Webhook Secret (from Stripe Dashboard)
gcloud secrets create STRIPE_WEBHOOK_SECRET --replication-policy="automatic"
echo -n "whsec_..." | gcloud secrets versions add STRIPE_WEBHOOK_SECRET --data-file=-

# Google API Key (Optional, if not using ADC)
gcloud secrets create GOOGLE_API_KEY --replication-policy="automatic"
echo -n "AIzaSy..." | gcloud secrets versions add GOOGLE_API_KEY --data-file=-

# DB_HOST (use the IP address output by Terraform)
gcloud secrets create DB_HOST --replication-policy="automatic"
echo -n "10.x.x.x" | gcloud secrets versions add DB_HOST --data-file=-
```

---

## Phase 4: Build and Deploy Applications

Now that the infrastructure and triggers are configured, you can build the actual applications.

### Option A: Manual Trigger

In the Cloud Build Triggers page:

1. Click **Run** on `backend-agent-trigger`.
2. Click **Run** on `frontend-nextjs-trigger`.

### Option B: Git Push

Push a commit to your `main` branch to automatically fire both triggers:

```bash
git add .
git commit -m "Deploy applications"
git push origin main
```

**What happens:** Cloud Build builds the Docker images, pushes them to Artifact Registry, and updates the Cloud Run services with your actual application code.

### Manual Build Commands

If needed, you can also run builds directly:

```bash
gcloud builds submit --config cloudbuild-backend.yaml .
gcloud builds submit --config cloudbuild-frontend.yaml .
```

---

## Phase 5: Database Initialization

Your Cloud SQL database is running but empty.

### Step 1: Connect to Cloud SQL

The easiest way is to use the Cloud SQL Auth Proxy from Cloud Shell:

```bash
# Download proxy
curl -o cloud-sql-proxy https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.8.0/cloud-sql-proxy.linux.amd64
chmod +x cloud-sql-proxy

# Start proxy (replace INSTANCE_CONNECTION_NAME from SQL Console)
./cloud-sql-proxy --address 0.0.0.0 --port 5432 INSTANCE_CONNECTION_NAME &
```

### Step 2: Get the Password

Go to **Secret Manager** → `[project-id]-cloudsql-password` → **View Secret Value**.

### Step 3: Enable pgvector and Run Init Script

```bash
psql "host=127.0.0.1 port=5432 sslmode=disable user=postgres dbname=postgres" -f init-db.sql
```

Within the database, enable the vector extension:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

---

## Phase 6: Configure Backend Runtime

Unlike the frontend, backend secrets are set on the Cloud Run service itself:

1. Go to **Cloud Run**.
2. Select the `backend-agent` service.
3. Click **Edit & Deploy New Revision**.
4. Go to the **Variables & Secrets** tab.
5. Add the required environment variables (see `backend-agent/config.py` for the list, e.g., `DB_HOST`, `DB_PASSWORD`, `STRIPE_API_KEY`).
6. Click **Deploy**.

---

## Phase 7: DNS Setup

1. Get the Load Balancer IP:

```bash
cd terraform && terraform output public_ip
```

2. Update your DNS provider (e.g., GoDaddy, Cloudflare) to point your domain (e.g., `ai.your-domain.com`) to this IP.

3. Wait 15-30 minutes for the managed SSL certificate to provision.

---

## Verification

1. Go to **Cloud Run** in the Console.
2. Click on the `frontend-agent` service.
3. Click the **URL** provided at the top.
4. You should see your Next.js application (not the Hello World page).

---

# Detailed Cost Breakdown by Module

## 1. Module: `billing_monitoring`

- **What is deployed:**

  - **Budget:** A budget alert for $100 (alerts you at 50%, 90%, 100%).
  - **Monitoring:** Custom metric for error counts and an alert policy for high error rates.
  - **Notification:** Email channel.

- **Cost:** **~$0.00 / month**.
  - Google Cloud Budgets and standard Alerting are generally free.
  - Custom metrics can incur costs if you send millions of data points, but for this scale, it's negligible.

## 2. Module: `cicd`

- **What is deployed:**

  - **Artifact Registry:** A Docker repository (`cloud-run-source-deploy`).
  - **Cloud Build:** 2 Triggers (Frontend & Backend) connected to GitHub.

- **Cost:** **Pay-as-you-go (Low)**.
  - **Builds:** You get 120 free build-minutes/day. Unless you commit code constantly, this is likely free.
  - **Storage:** Artifact Registry charges ~$0.020 per GB/month for storing your Docker images.

## 3. Module: `compute` (Variable Cost)

- **What is deployed:**

  - **Cloud Run Job:** `ingest-job` (Runs only when triggered).
  - **Cloud Run Service:** `backend-agent` (2 vCPU, 4GB RAM).
  - **Cloud Run Service:** `frontend-agent` (1 vCPU, 2GB RAM).

- **Cost:** **$0.00 / month (If Idle)**.
  - **Configuration:** Both services currently have `min_instance_count = 0`. This means they scale to zero when not in use.
  - **Active Cost:** You only pay when requests are processed.
    - **Backend:** ~$0.000048 per vCPU-second.
    - **Frontend:** ~$0.000024 per vCPU-second.

## 4. Module: `database` (Significant Cost)

- **What is deployed:**

  - **Cloud SQL (PostgreSQL):**
    - Tier: `db-g1-small` (Shared core).
    - Edition: Enterprise.
    - Disk: SSD (Autoscaling).
    - Backups: Enabled (7 days retention).
  - **Firestore:** Native mode database.

- **Cost:** **~$34 - $45 / month**.
  - The SQL instance charges an hourly rate 24/7 (~$0.041/hour) plus storage costs (~$0.17/GB/month).
  - Firestore is pay-as-you-go (reads/writes) and has a generous free tier.

## 5. Module: `function`

- **What is deployed:**

  - **Cloud Function:** `pdf-ingest-function` (Python 3.11).
  - **Trigger:** Eventarc trigger watching a Storage Bucket for new files.

- **Cost:** **Pay-as-you-go (Low)**.
  - You only pay when a file is uploaded and the function runs. The first 2 million invocations per month are usually free.

## 6. Module: `ingress` (Moderate Cost)

- **What is deployed:**

  - **Load Balancer:** Global External Application Load Balancer.
  - **SSL:** Managed Google Certificate for `app.yourdomain.com`.
  - **Cloud Armor:** Security Policy with WAF rules (SQLi, XSS, etc.) and Rate Limiting.

- **Cost:** **~$33 - $40 / month**.
  - **Forwarding Rule:** The Load Balancer charges ~$0.025/hour (~$18/month).
  - **Cloud Armor:** ~$5/month per policy + $1/month per rule.
  - **Warning:** The plan enables `layer_7_ddos_defense_config`. We have confirmed `google_compute_project_cloud_armor_tier` is NOT used, avoiding the $3,000/mo Enterprise subscription.

## 7. Module: `network` (Moderate Cost)

- **What is deployed:**

  - **VPC Network:** Custom subnets.
  - **Cloud NAT:** A NAT Gateway (`your-actual-project-id-12345-nat`).

- **Cost:** **~$33 / month** + Data Fees.
  - The NAT Gateway charges ~$0.045/hour (~$33/month) just to exist, regardless of traffic.
  - You also pay $0.045 per GB for data processing through the NAT.

## 8. Module: `redis` (Significant Cost)

- **What is deployed:**

  - **Memorystore for Redis:** Basic Tier, 1 GB capacity.

- **Cost:** **~$36 / month**.
  - This is a fixed instance charged hourly (~$0.049/hour).

## 9. Module: `storage`

- **What is deployed:**

  - **Buckets:** `data_bucket` (with lifecycle rules) and `source_bucket`.

- **Cost:** **Pay-as-you-go (Low)**.
  - Standard storage is ~$0.02 per GB. Unless you store Terabytes, this is negligible.

---

### Summary Table of Estimated Monthly "Fixed" Costs

| Module       | Resource                    | Est. Monthly Cost (Idle) |
| ------------ | --------------------------- | ------------------------ |
| **Compute**  | Cloud Run (Min 0 Instances) | ~$0.00                   |
| **Database** | Cloud SQL (db-g1-small)     | ~$34.00                  |
| **Redis**    | Memorystore (1GB Basic)     | ~$36.00                  |
| **Network**  | Cloud NAT Gateway           | ~$33.00                  |
| **Ingress**  | Load Balancer Rule          | ~$18.00                  |
| **Ingress**  | Cloud Armor Policy          | ~$15.00                  |
| **TOTAL**    | **Baseline "Rent"**         | **~$136.00 / month**     |

**Recommendation:**
To reduce costs to <$50/mo:

1.  **Delete the Redis module** and use a local container or smaller service if possible (~$36 savings).
2.  **Delete the NAT Gateway** if your Cloud Run services don't strictly _need_ a static outgoing IP (~$33 savings). _Note: This would require changing the Cloud Run VPC egress settings._
3.  **Downgrade Cloud SQL** to `db-f1-micro` (if available in your region/project type) or use **Firestore** only (~$34 savings).

---

# Disaster Recovery Plan

This section outlines the procedures for recovering critical data stores.

## Cloud SQL (PostgreSQL) Recovery

Our Cloud SQL instance is configured with:

- **Automated Backups:** Retained for 7 days.
- **Point-in-Time Recovery (PITR):** Allows restoration to any second within the retention window.
- **Deletion Protection:** Prevents accidental deletion of the instance.

### Scenario A: Accidental Data Corruption (PITR)

Restore the database to a state before the corruption occurred:

1. **Identify the Timestamp:** Determine the exact UTC time just before the error occurred.

2. **Perform Restore (Clone):**

```bash
gcloud sql instances clone <SOURCE_INSTANCE_ID> restored-db-instance \
    --point-in-time "2023-10-27T13:00:00Z"
```

3. **Verify Data:** Connect to `restored-db-instance` and verify the data integrity.

4. **Switch Traffic:** Update the application secrets to point to the new instance IP/Host.

### Scenario B: Full Instance Loss (Backup Restore)

Restore from the last successful nightly backup:

1. **List Backups:**

```bash
gcloud sql backups list --instance=<INSTANCE_ID>
```

2. **Restore:**

```bash
gcloud sql backups restore <BACKUP_ID> --restore-instance=<TARGET_INSTANCE_ID>
```

---

## Firestore Recovery

Our Firestore database is configured with a **Daily Backup Schedule** retained for 7 days.

### Restore Procedure

1. **List Available Backups:**

```bash
gcloud firestore backups list --location=<REGION>
```

Note the `resource name` of the backup you wish to restore.

2. **Restore to a New Database:**

Firestore does not support in-place restores. You must restore to a new database ID.

```bash
gcloud firestore databases restore \
    --source-backup=projects/<PROJECT_ID>/locations/<REGION>/backups/<BACKUP_ID> \
    --destination-database=restored-firestore-db
```

3. **Update Application:** Update the backend configuration (`FIRESTORE_DATABASE_ID`) to point to `restored-firestore-db`.

---

## Post-Recovery Checklist

- [ ] **Verify Connectivity:** Ensure backend services can connect to the restored databases.
- [ ] **Data Integrity Check:** Run application-level smoke tests.
- [ ] **Re-enable Backups:** Ensure the new/restored instances have backup schedules re-applied (Terraform apply might be needed).

---

## Pre-Commit

```bash
pre-commit install
pre-commit run --all-files
git status && git diff
git add ... ... && git commit -m "...."
```

**Acknowledgements**
✨ Google ML Developer Programs and Google Developers Program supported this work by providing Google Cloud Credits (and awesome tutorials for the Google Developer Experts)✨
