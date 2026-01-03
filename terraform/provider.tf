terraform {
  required_version = ">= 1.5"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 5.0"
    }
  }

  # STOP: You must create this bucket manually in the console first.
  # Terraform cannot create the bucket it uses to store its own memory.
  backend "gcs" {
    bucket = "terraform-state-prod-rubens-ai-platform" # CHANGE THIS
    prefix = "terraform/state"
  }
}

provider "google" {
  project = var.project_id # CHANGE THIS
  region  = var.region            # Using the variable
}

provider "google-beta" {
  project = var.project_id # CHANGE THIS
  region  = var.region            # Using the variable
}

# --- APIs to Enable ---
resource "google_project_service" "apis" {
  for_each = toset([
    "compute.googleapis.com",
    "run.googleapis.com",
    "sqladmin.googleapis.com",
    "secretmanager.googleapis.com",
    "aiplatform.googleapis.com",
    "dlp.googleapis.com",
    "firestore.googleapis.com",
    "redis.googleapis.com",
    "cloudbilling.googleapis.com",
    "monitoring.googleapis.com",
    "logging.googleapis.com",
    "cloudtrace.googleapis.com",
    "servicenetworking.googleapis.com",
    "cloudbuild.googleapis.com",
    "artifactregistry.googleapis.com"
  ])

  project            = var.project_id
  service            = each.key
  disable_on_destroy = false
}