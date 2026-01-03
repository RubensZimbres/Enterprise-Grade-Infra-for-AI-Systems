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

  depends_on = [google_artifact_registry_repository.repo]
}

# data "google_project" "project" {
#   project_id = var.project_id
# }

# # Grant Cloud Build Service Account permissions to deploy to Cloud Run
# resource "google_project_iam_member" "cloudbuild_run_developer" {
#   project = var.project_id
#   role    = "roles/run.developer"
#   member  = "serviceAccount:${data.google_project.project.number}@cloudbuild.gserviceaccount.com"
# }

# # Grant Cloud Build Service Account permission to act as other service accounts (required for Cloud Run deploy)
# resource "google_project_iam_member" "cloudbuild_sa_user" {
#   project = var.project_id
#   role    = "roles/iam.serviceAccountUser"
#   member  = "serviceAccount:${data.google_project.project.number}@cloudbuild.gserviceaccount.com"
# }

