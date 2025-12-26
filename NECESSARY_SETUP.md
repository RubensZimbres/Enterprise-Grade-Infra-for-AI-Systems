# What To Do: A Deployment Guide for the AI Platform

This document provides the essential `gcloud` commands and manual steps required to successfully deploy your AI platform in a **brand-new Google Cloud project**.

The steps are divided into two phases:
1.  **Pre-Terraform Setup:** Manual steps you must complete *before* running `terraform apply`.
2.  **Post-Terraform Actions:** Steps to take *after* your infrastructure is successfully provisioned.

---

## Phase 1: Pre-Terraform Setup (Manual Steps)

These actions prepare your Google Cloud project and grant the necessary permissions for Terraform and Cloud Build to run.

### 1.1. Initial Project and Billing Setup

First, log in and set up your project configuration.

```bash
# Log in to your Google Cloud account
gcloud auth login

# Set the project you will be working on
gcloud config set project [YOUR_PROJECT_ID]

# Link your project to a billing account (required to use most services)
gcloud beta billing projects link [YOUR_PROJECT_ID] --billing-account [YOUR_BILLING_ACCOUNT_ID]
```
**Reasoning:** A new project isn't linked to billing by default. Without this, most API and service-related commands will fail.

### 1.2. Enable Required Google Cloud APIs

Terraform will fail if the APIs for the resources it needs to create are not enabled.

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
  alloydb.googleapis.com \
  firestore.googleapis.com \
  serviceusage.googleapis.com \
  servicenetworking.googleapis.com \
  iap.googleapis.com
```
**Reasoning:** In a new project, these APIs are disabled. Attempting to create resources like Cloud Run services, VPCs, or AlloyDB clusters without enabling their respective APIs is the most common cause of initial Terraform failures.

### 1.3. Grant Permissions to the Cloud Build Service Account

Your `cloudbuild-*.yaml` files build and deploy your applications. The default Cloud Build service account needs permission to do so.

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
**Reasoning:** By default, the Cloud Build agent can build images but cannot deploy them to Cloud Run (`roles/run.admin`) or grant IAM permissions, which might be needed during deployment (`roles/iam.serviceAccountAdmin`). It also needs explicit permission to push the container images it builds to Artifact Registry (`roles/artifactregistry.writer`).

### 1.4. Configure IAP OAuth Consent Screen (Manual UI Step)

Your Terraform configuration for the load balancer uses Identity-Aware Proxy (IAP), which requires an OAuth Client ID and Secret. This is a **manual, one-time setup** in the Google Cloud Console.

1.  **Navigate to the OAuth Consent Screen:**
    *   Go to [APIs & Services -> OAuth consent screen](https://console.cloud.google.com/apis/credentials/consent) in the GCP Console.
2.  **Configure the Consent Screen:**
    *   Choose **Internal** for the User Type and click **Create**.
    *   Fill in the required fields:
        *   **App name:** `AI Platform` (or your preferred name).
        *   **User support email:** Your email address.
        *   **Developer contact information:** Your email address.
    *   Click **Save and Continue** through the rest of the sections.
3.  **Create OAuth 2.0 Client ID:**
    *   Go to [APIs & Services -> Credentials](https://console.cloud.google.com/apis/credentials).
    *   Click **+ CREATE CREDENTIALS** and select **OAuth client ID**.
    *   Select **Web application** for the Application type.
    *   Give it a name, like `iap-load-balancer-client`.
    *   Click **Create**.
4.  **Save the Client ID and Secret:**
    *   A dialog will appear with your **Client ID** and **Client Secret**.
    *   Copy these values and place them into your `terraform.tfvars` file for the `iap_client_id` and `iap_client_secret` variables.

**Reasoning:** IAP secures your frontend by requiring Google authentication. This process associates your application with a valid identity in your Google Cloud organization. Terraform cannot perform these actions, as they require interactive consent. This step must be completed before you can run `terraform apply`.

---

## Phase 2: Post-Terraform Actions & Verification

After `terraform apply` completes successfully, perform these final steps to make your application fully functional.

### 2.1. Update DNS "A" Record

Your Terraform `ingress` module provisioned a static IP for the load balancer. You must point your domain to it.

1.  **Get the Load Balancer IP Address:**
    ```bash
    terraform output public_ip
    ```
2.  **Update Your DNS:**
    *   Go to your domain registrar (e.g., Google Domains, Cloudflare, GoDaddy).
    *   Create or update the **"A" record** for the domain you specified in `terraform.tfvars` (e.g., `ai.your-company.com`).
    *   Point it to the IP address from the Terraform output.

**Reasoning:** The managed SSL certificate and HTTPS routing will not work until your domain correctly resolves to the load balancer's IP address.

### 2.2. Enable `pgvector` Extension in AlloyDB

Your Terraform code correctly provisions the AlloyDB instance with flags optimized for `pgvector`, but it cannot enable the extension itself.

1.  **Connect to the AlloyDB instance:** Use your preferred PostgreSQL client (like `psql` or a GUI tool) to connect to the database using the IP address and the password stored in Secret Manager.
2.  **Run the SQL Command:** Execute the following command in your database to enable the vector extension.
    ```sql
    CREATE EXTENSION IF NOT EXISTS vector;
    ```

**Reasoning:** The `pgvector` extension provides the functions and data types necessary for similarity searches. Without it, the RAG backend will fail when trying to query for documents.

### 2.3. Set the AI Provider API Key

Your backend's Terraform configuration references a secret for your AI provider's API key. You must update the placeholder value with your real key.

```bash
# Add the first version of the secret with your actual API key
gcloud secrets versions add ai-provider-api-key --data-file="/path/to/your/api_key.txt"
```
**Reasoning:** Your Terraform code creates the secret `ai-provider-api-key` with a placeholder value. This command updates it with your real, sensitive key without exposing it in your terminal history. The backend Cloud Run service will automatically pick up the new version.

### 2.4. Trigger Cloud Build to Deploy Your Code

Terraform has set up the infrastructure, but it uses a placeholder "hello world" container. You now need to run your Cloud Build pipelines to deploy your actual frontend and backend applications.

```bash
# Deploy the backend agent
gcloud builds submit --config cloudbuild-backend.yaml .

# Deploy the frontend agent (assuming a similar cloudbuild-frontend.yaml exists)
gcloud builds submit --config cloudbuild-frontend.yaml .
```
**Reasoning:** This is the final step that replaces the placeholder services with your actual Streamlit and FastAPI applications, making the platform live.

By following these steps in order, you can systematically address the most common permission and connectivity gaps, leading to a successful and secure deployment.
