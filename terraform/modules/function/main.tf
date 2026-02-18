# Compress source code
data "archive_file" "source" {
  type        = "zip"
  source_dir  = "${path.root}/../functions/pdf-ingest"
  output_path = "/tmp/function-source.zip"
}

# Upload source code
resource "google_storage_bucket_object" "zip" {
  source       = data.archive_file.source.output_path
  content_type = "application/zip"

  # Append MD5 to force update on change
  name   = "src-${data.archive_file.source.output_md5}.zip"
  bucket = var.source_bucket_name
}

# Service Account for the Function
resource "google_service_account" "function_sa" {
  account_id   = "pdf-ingest-sa"
  display_name = "PDF Ingest Function SA"
}

# Grant permissions to SA
resource "google_project_iam_member" "vertex_ai_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.function_sa.email}"
}

resource "google_project_iam_member" "storage_viewer" {
  project = var.project_id
  role    = "roles/storage.objectViewer"
  member  = "serviceAccount:${google_service_account.function_sa.email}"
}

resource "google_secret_manager_secret_iam_member" "secret_access" {
  secret_id = var.db_password_secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.function_sa.email}"
}

# VPC Connector for Cloud Function to reach Private Cloud SQL
resource "google_vpc_access_connector" "connector" {
  name          = "pdf-ingest-conn"
  region        = var.region
  network       = var.vpc_name
  ip_cidr_range = "10.8.0.0/28"
}

# Cloud Function (Gen 2)
resource "google_cloudfunctions2_function" "function" {
  name        = "pdf-ingest-function"
  location    = var.region
  description = "Ingests PDFs into Vector DB on upload"

  build_config {
    runtime     = "python311"
    entry_point = "ingest_pdf" # Matches main.py
    source {
      storage_source {
        bucket = var.source_bucket_name
        object = google_storage_bucket_object.zip.name
      }
    }
  }

  service_config {
    max_instance_count    = 10
    available_memory      = "512M"
    timeout_seconds       = 300
    service_account_email = google_service_account.function_sa.email

    # VPC Access
    vpc_connector                 = google_vpc_access_connector.connector.id
    vpc_connector_egress_settings = "PRIVATE_RANGES_ONLY"

    environment_variables = {
      PROJECT_ID = var.project_id
      REGION     = var.region
      DB_HOST    = var.db_host
      DB_USER    = var.db_user
      DB_NAME    = var.db_name
    }

    secret_environment_variables {
      key        = "DB_PASSWORD"
      project_id = var.project_id
      secret     = var.db_password_secret_id
      version    = "latest"
    }
  }

  event_trigger {
    trigger_region        = var.region
    event_type            = "google.cloud.storage.object.v1.finalized"
    retry_policy          = "RETRY_POLICY_RETRY"
    service_account_email = google_service_account.function_sa.email
    event_filters {
      attribute = "bucket"
      value     = var.bucket_name
    }
  }
}
