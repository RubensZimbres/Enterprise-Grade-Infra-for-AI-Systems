# modules/compute/main.tf

data "google_project" "project" {}

# --- 1. Identity: Service Accounts (The ID Cards) ---

resource "google_service_account" "frontend_sa" {
  account_id   = "ai-frontend-sa"
  display_name = "Frontend Agent Service Account"
}

resource "google_service_account" "backend_sa" {
  account_id   = "ai-backend-sa"
  display_name = "Backend Agent Service Account"
}

# --- 2. IAM: Giving the Backend "Keys" ---

# Allow Backend to read the DB Password from Secret Manager
resource "google_secret_manager_secret_iam_member" "backend_secret_access" {
  secret_id = var.db_secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.backend_sa.email}"
}

# Allow Backend to connect to Cloud SQL
resource "google_project_iam_member" "backend_cloudsql_client" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.backend_sa.email}"
}

# Allow Backend to use Cloud Trace
resource "google_project_iam_member" "backend_trace_agent" {
  project = var.project_id
  role    = "roles/cloudtrace.agent"
  member  = "serviceAccount:${google_service_account.backend_sa.email}"
}

# Allow Backend to use Vertex AI (Vector Search)
resource "google_project_iam_member" "backend_vertex_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.backend_sa.email}"
}

# Allow Backend to read/write Firestore
resource "google_project_iam_member" "backend_firestore_user" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.backend_sa.email}"
}

# Allow Backend to use DLP (PII Masking)
resource "google_project_iam_member" "backend_dlp_user" {
  project = var.project_id
  role    = "roles/dlp.user"
  member  = "serviceAccount:${google_service_account.backend_sa.email}"
}

# --- 3. The Backend Service (The Brain) ---

resource "google_cloud_run_v2_service" "backend" {
  name     = "backend-agent"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_INTERNAL_ONLY"

  template {
    service_account = google_service_account.backend_sa.email
    timeout         = "300s"

    scaling {
      min_instance_count = 0
      max_instance_count = 20
    }

    vpc_access{
      network_interfaces {
        network    = var.vpc_name
        subnetwork = var.subnet_name
      }
      egress = "ALL_TRAFFIC"
    }

    containers {
      image = "us-docker.pkg.dev/cloudrun/container/hello"

      # ADDED: Auto-healing configuration
      startup_probe {
        initial_delay_seconds = 10
        timeout_seconds       = 3
        period_seconds        = 10
        failure_threshold     = 3
        http_get {
          path = "/health"
          port = 8080
        }
      }

      liveness_probe {
        initial_delay_seconds = 30 # Give startup probe time to finish
        timeout_seconds       = 3
        period_seconds        = 15
        failure_threshold     = 3
        http_get {
          path = "/health"
          port = 8080
        }
      }

      resources {
        limits = {
          cpu    = "2"
          memory = "4Gi"
        }
      }

      env {
        name  = "PROJECT_ID"
        value = var.project_id
      }
      env {
        name  = "REGION"
        value = var.region
      }
      env {
          name  = "DB_USER"
          value = "postgres"
        }
      env {
        name  = "DB_NAME"
        value = "postgres"
      }
      env {
        name  = "DB_HOST"
        value = var.db_host
      }
      env {
        name = "DB_PASSWORD"
        value_source {
          secret_key_ref {
            secret  = var.db_secret_id
            version = "latest"
          }
        }
      }
      env {
        name  = "REDIS_HOST"
        value = var.redis_host
      }
      env {
        name = "REDIS_PASSWORD"
        value_source {
          secret_key_ref {
            secret  = var.redis_password_id
            version = "latest"
          }
        }
      }
      env {
        name = "STRIPE_API_KEY"
        value_source {
          secret_key_ref {
            secret  = var.stripe_secret_key_id
            version = "latest"
          }
        }
      }
      # FRONTEND_URL removed to avoid circular dependency (Cycle: backend -> frontend -> backend)
      # If needed for CORS, consider using a wildcard or updating after creation.
    }
  }
}

# --- 4. The Frontend Service (The Face) ---

resource "google_cloud_run_v2_service" "frontend" {
  name     = "frontend-agent"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.frontend_sa.email
    timeout         = "300s"

    scaling {
      min_instance_count = 0
      max_instance_count = 20
    }

    vpc_access{
      network_interfaces {
        network    = var.vpc_name
        subnetwork = var.subnet_name
      }
      egress = "ALL_TRAFFIC"
    }

    containers {
      image = "us-docker.pkg.dev/cloudrun/container/hello"

      resources {
        limits = {
          cpu    = "1"
          memory = "2Gi"
        }
      }

      env {
        name  = "BACKEND_URL"
        value = google_cloud_run_v2_service.backend.uri
      }
    }
  }
}

# --- 5. Security: Allow Frontend to invoke Backend ---

resource "google_cloud_run_v2_service_iam_member" "frontend_invokes_backend" {
  location = google_cloud_run_v2_service.backend.location
  name     = google_cloud_run_v2_service.backend.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.frontend_sa.email}"
}

# --- 6. Security: Allow Public Access to Frontend (No IAP) ---

# Allow unauthenticated users (public internet) to invoke the Frontend
resource "google_cloud_run_v2_service_iam_member" "public_invokes_frontend" {
  location = google_cloud_run_v2_service.frontend.location
  name     = google_cloud_run_v2_service.frontend.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# --- 7. Ingestion Job (The Knowledge Loader) ---

resource "google_cloud_run_v2_job" "ingest_job" {
  name     = "ingest-job"
  location = var.region

  template {
    template {
      service_account = google_service_account.backend_sa.email
      timeout = "600s"

      vpc_access{
        network_interfaces {
          network    = var.vpc_name
          subnetwork = var.subnet_name
        }
        egress = "ALL_TRAFFIC"
      }

      containers {
        image = "us-docker.pkg.dev/cloudrun/container/hello"

        command = ["python", "ingest.py"]

        resources {
          limits = {
            cpu    = "2"
            memory = "4Gi"
          }
        }

        env {
          name  = "PROJECT_ID"
          value = var.project_id
        }
        env {
          name  = "REGION"
          value = var.region
        }
        env {
            name  = "DB_USER"
            value = "postgres"
          }
        env {
          name  = "DB_NAME"
          value = "postgres"
        }
        env {
          name  = "DB_HOST"
          value = var.db_host
        }
        env {
          name = "DB_PASSWORD"
          value_source {
            secret_key_ref {
              secret  = var.db_secret_id
              version = "latest"
            }
          }
        }
        env {
          name  = "REDIS_HOST"
          value = var.redis_host
        }
      }
    }
  }
}

# --- 8. Security: Allow Frontend to Access Secrets ---

# REMOVED: Excessive permission (roles/secretmanager.secretAccessor on Project)
# The frontend now has scoped access to specific secrets (Stripe) defined in the root main.tf
