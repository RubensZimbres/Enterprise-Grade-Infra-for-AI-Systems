# modules/compute/main.tf

data "google_project" "project" {}

# --- 1. Identity: Service Accounts (The ID Cards) ---

resource "google_service_account" "frontend_sa" {
  account_id   = "ai-frontend-sa" # REMOVED: "${var.project_id}-"
  display_name = "Frontend Agent Service Account"
}

resource "google_service_account" "backend_sa" {
  account_id   = "ai-backend-sa" # REMOVED: "${var.project_id}-"
  display_name = "Backend Agent Service Account"
}

# --- 2. IAM: Giving the Backend "Keys" ---

# Allow Backend to read the DB Password from Secret Manager
resource "google_secret_manager_secret_iam_member" "backend_secret_access" {
  secret_id = var.db_secret_id # Passed from Database module
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

# --- 3. The Backend Service (The Brain) ---

resource "google_cloud_run_v2_service" "backend" {
  name     = "backend-agent"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_INTERNAL_ONLY" # Locked down. Only reachable via VPC/Internal.

  template {
    service_account = google_service_account.backend_sa.email
    timeout         = "300s"
    
    # SCALABILITY: Define autoscaling limits
    scaling {
      min_instance_count = 1 
      max_instance_count = 20 
    }

    # DIRECT VPC EGRESS: Connects container to the Private Subnet
    vpc_access{
      network_interfaces {
        network    = var.vpc_name
        subnetwork = var.subnet_name
      }
      # Route all traffic through VPC (so it uses Cloud NAT for internet)
      egress = "ALL_TRAFFIC" 
    }

    containers {
      # Placeholder image. You MUST replace this with your actual Artifact Registry image later.
      image = "us-docker.pkg.dev/cloudrun/container/hello" 

      resources {
        limits = {
          cpu    = "4"
          memory = "8Gi"
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
        value = "postgres" # Reverted to default DB to ensure connection success
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

# --- 4. The Frontend Service (The Face) ---

resource "google_cloud_run_v2_service" "frontend" {
  name     = "frontend-agent"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL" # Accepts traffic from ALB (or public for now)

  template {
    service_account = google_service_account.frontend_sa.email
    timeout         = "300s"
    
    # SCALABILITY: Define autoscaling limits
    scaling {
      min_instance_count = 1 
      max_instance_count = 20 
    }

    # Frontend also needs VPC access if it needs to talk to the Backend via internal DNS
    vpc_access{
      network_interfaces {
        network    = var.vpc_name
        subnetwork = var.subnet_name
      }
      egress = "ALL_TRAFFIC"
    }

    containers {
      # Placeholder image. You MUST replace this with your actual Artifact Registry image later.
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

# Allow IAP Service Agent to invoke Frontend (Used by Load Balancer)
resource "google_cloud_run_v2_service_iam_member" "lb_invokes_frontend" {
  location = google_cloud_run_v2_service.frontend.location
  name     = google_cloud_run_v2_service.frontend.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:service-${data.google_project.project.number}@gcp-sa-iap.iam.gserviceaccount.com"
}

# --- 6. Ingestion Job (The Knowledge Loader) ---

resource "google_cloud_run_v2_job" "ingest_job" {
  name     = "ingest-job"
  location = var.region

  template {
    template {
      service_account = google_service_account.backend_sa.email # Re-use backend SA as it has DB permissions
      timeout = "600s" # Jobs can run longer

      vpc_access{
        network_interfaces {
          network    = var.vpc_name
          subnetwork = var.subnet_name
        }
        egress = "ALL_TRAFFIC"
      }

      containers {
        # Reuse the backend image, but run a different command
        image = "us-docker.pkg.dev/cloudrun/container/hello" 
        
        # OVERRIDE COMMAND to run the ingestion script
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
        # Ingestion doesn't strictly need Redis, but config might import it.
        env {
          name  = "REDIS_HOST"
          value = var.redis_host
        }
      }
    }
  }
}
