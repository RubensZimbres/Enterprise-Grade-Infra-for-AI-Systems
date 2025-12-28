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

# Allow Backend to connect to AlloyDB
resource "google_project_iam_member" "backend_alloydb_client" {
  project = var.project_id
  role    = "roles/alloydb.client"
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
    
    # SCALABILITY: Define autoscaling limits
    scaling {
      min_instance_count = 0 
      max_instance_count = 10 # Scalable to 50 concurrent instances
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

      # In the google_cloud_run_v2_service "backend" resource...
      env {
        name = "GOOGLE_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.ai_api_key_secret.secret_id
            version = "latest"
          }
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
        value = var.alloydb_ip
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
    }
  }
}

# --- 3.1 Secret for Vertex AI API Key ---

resource "google_secret_manager_secret" "ai_api_key_secret" {
  secret_id = "ai-provider-api-key"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "ai_api_key_version" {
  secret      = google_secret_manager_secret.ai_api_key_secret.id
  secret_data = "CHANGE_ME_TO_REAL_API_KEY" # Placeholder
  
  lifecycle {
    ignore_changes = [secret_data]
  }
}

resource "google_secret_manager_secret_iam_member" "backend_api_key_access" {
  secret_id = google_secret_manager_secret.ai_api_key_secret.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.backend_sa.email}"
}

# --- 4. The Frontend Service (The Face) ---

resource "google_cloud_run_v2_service" "frontend" {
  name     = "frontend-agent"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL" # Accepts traffic from ALB (or public for now)

  template {
    service_account = google_service_account.frontend_sa.email
    
    # SCALABILITY: Keep 1 instance warm to eliminate cold starts for users
    scaling {
      min_instance_count = 1 
      max_instance_count = 10 # Frontend scales wider to handle global traffic
    }

    # Frontend also needs VPC access if it needs to talk to the Backend via internal DNS
    vpc_access{
      network_interfaces {
        network    = var.vpc_name
        subnetwork = var.subnet_name
      }
      egress = "PRIVATE_RANGES_ONLY"
    }

    containers {
      # Placeholder image. You MUST replace this with your actual Artifact Registry image later.
      image = "us-docker.pkg.dev/cloudrun/container/hello"
      
      env {
        name  = "NEXT_PUBLIC_BACKEND_URL"
        value = google_cloud_run_v2_service.backend.uri
      }
    }
  }
}

# --- 5. Security: Allow Frontend to invoke Backend ---

resource "google_cloud_run_service_iam_member" "frontend_invokes_backend" {
  location = google_cloud_run_v2_service.backend.location
  service  = google_cloud_run_v2_service.backend.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.frontend_sa.email}"
}

# Allow IAP Service Agent to invoke Frontend (Used by Load Balancer)
resource "google_cloud_run_service_iam_member" "lb_invokes_frontend" {
  location = google_cloud_run_v2_service.frontend.location
  service  = google_cloud_run_v2_service.frontend.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:service-${data.google_project.project.number}@gcp-sa-iap.iam.gserviceaccount.com"
}
