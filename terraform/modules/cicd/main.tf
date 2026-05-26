resource "google_artifact_registry_repository" "repo" {
  provider      = google-beta
  location      = var.region
  repository_id = "cloud-run-source-deploy"
  description   = "Docker repository for Cloud Run deployments"
  format        = "DOCKER"
  project       = var.project_id
}

# --- Service Accounts for Pipelines ---

# Backend CI/CD Pipeline SA
resource "google_service_account" "backend_pipeline" {
  account_id   = "backend-pipeline-sa"
  display_name = "Backend Pipeline SA"
  project      = var.project_id
}

resource "google_project_iam_member" "backend_pipeline_roles" {
  for_each = toset([
    "roles/artifactregistry.writer",
    "roles/run.developer",
    "roles/iam.serviceAccountUser",
    "roles/logging.logWriter"
  ])
  project = var.project_id
  role    = each.key
  member  = "serviceAccount:${google_service_account.backend_pipeline.email}"
}

# Frontend CI/CD Pipeline SA
resource "google_service_account" "frontend_pipeline" {
  account_id   = "frontend-pipeline-sa"
  display_name = "Frontend Pipeline SA"
  project      = var.project_id
}

resource "google_project_iam_member" "frontend_pipeline_roles" {
  for_each = toset([
    "roles/artifactregistry.writer",
    "roles/run.developer",
    "roles/iam.serviceAccountUser",
    "roles/secretmanager.secretAccessor",
    "roles/logging.logWriter"
  ])
  project = var.project_id
  role    = each.key
  member  = "serviceAccount:${google_service_account.frontend_pipeline.email}"
}

# Infra CI/CD Pipeline SA
resource "google_service_account" "infra_pipeline" {
  account_id   = "infra-pipeline-sa"
  display_name = "Infra Pipeline SA"
  project      = var.project_id
}

resource "google_project_iam_member" "infra_pipeline_roles" {
  for_each = toset([
    "roles/editor",
    "roles/iam.securityAdmin",
    "roles/secretmanager.admin",
    "roles/resourcemanager.projectIamAdmin",
    "roles/logging.logWriter"
  ])
  project = var.project_id
  role    = each.key
  member  = "serviceAccount:${google_service_account.infra_pipeline.email}"
}

# --- Cloud Build Triggers ---

resource "google_cloudbuild_trigger" "backend" {
  name        = "backend-agent-trigger"
  project     = var.project_id
  description = "Triggers build and deploy for Backend Agent on push to main"

  github {
    owner = var.github_owner
    name  = var.github_repo_name
    push {
      branch = "^main$"
    }
  }

  included_files = ["backend-agent/**", "cloudbuild-backend.yaml"]
  filename       = "cloudbuild-backend.yaml"
  service_account = google_service_account.backend_pipeline.id

  depends_on = [google_artifact_registry_repository.repo]
}

resource "google_cloudbuild_trigger" "frontend" {
  name        = "frontend-nextjs-trigger"
  project     = var.project_id
  description = "Triggers build and deploy for Frontend on push to main"

  github {
    owner = var.github_owner
    name  = var.github_repo_name
    push {
      branch = "^main$"
    }
  }

  included_files = ["frontend-nextjs/**", "cloudbuild-frontend.yaml"]
  filename       = "cloudbuild-frontend.yaml"
  service_account = google_service_account.frontend_pipeline.id

  depends_on = [google_artifact_registry_repository.repo]
}

resource "google_cloudbuild_trigger" "infra" {
  name        = "infra-terraform-trigger"
  project     = var.project_id
  description = "Triggers Terraform apply on push to main"

  github {
    owner = var.github_owner
    name  = var.github_repo_name
    push {
      branch = "^main$"
    }
  }

  included_files = ["terraform/**", "cloudbuild-terraform.yaml", "validate_naming.sh"]
  filename       = "cloudbuild-terraform.yaml"
  service_account = google_service_account.infra_pipeline.id
}

# --- Drift Detection Scheduled Trigger ---

resource "google_pubsub_topic" "drift_topic" {
  name    = "drift-detection-topic"
  project = var.project_id
}

resource "google_cloudbuild_trigger" "drift" {
  name        = "infra-drift-detection"
  project     = var.project_id
  description = "Scheduled drift detection for Terraform"

  pubsub_config {
    topic = google_pubsub_topic.drift_topic.id
  }

  filename       = "cloudbuild-drift.yaml"
  service_account = google_service_account.infra_pipeline.id
}

resource "google_cloud_scheduler_job" "drift_schedule" {
  name        = "drift-detection-schedule"
  description = "Run drift detection every 15 minutes"
  schedule    = "*/15 * * * *"
  project     = var.project_id
  region      = var.region

  pubsub_target {
    topic_name = google_pubsub_topic.drift_topic.id
    data       = base64encode("{}")
  }
}
