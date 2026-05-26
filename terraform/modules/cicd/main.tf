resource "google_artifact_registry_repository" "repo" {
  provider      = google-beta
  location      = var.region
  repository_id = "cloud-run-source-deploy"
  description   = "Docker repository for Cloud Run deployments"
  format        = "DOCKER"
  project       = var.project_id
}

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

  service_account = google_service_account.cloudbuild_sa.id

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

  service_account = google_service_account.cloudbuild_sa.id

  depends_on = [google_artifact_registry_repository.repo]
}

resource "google_service_account" "cloudbuild_sa" {
  account_id   = "cloudbuild-sa"
  display_name = "Cloud Build Service Account"
  project      = var.project_id
}

resource "google_project_iam_member" "cloudbuild_logs_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.cloudbuild_sa.email}"
}

resource "google_project_iam_member" "cloudbuild_artifact_writer" {
  project = var.project_id
  role    = "roles/artifactregistry.writer"
  member  = "serviceAccount:${google_service_account.cloudbuild_sa.email}"
}

resource "google_project_iam_member" "cloudbuild_run_developer" {
  project = var.project_id
  role    = "roles/run.developer"
  member  = "serviceAccount:${google_service_account.cloudbuild_sa.email}"
}

resource "google_project_iam_member" "cloudbuild_sa_user" {
  project = var.project_id
  role    = "roles/iam.serviceAccountUser"
  member  = "serviceAccount:${google_service_account.cloudbuild_sa.email}"
}

resource "google_project_iam_member" "cloudbuild_secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.cloudbuild_sa.email}"
}
