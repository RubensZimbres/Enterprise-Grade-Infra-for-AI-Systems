# modules/database/main.tf

terraform {
  required_providers {
    google = {
      source = "hashicorp/google"
    }
    random = {
      source = "hashicorp/random"
    }
  }
}

# --- 1. Security First: Generate & Store Password ---

resource "random_password" "db_password" {
  length  = 16
  special = true
  upper   = true
}

resource "google_secret_manager_secret" "db_pass_secret" {
  secret_id = "${var.project_id}-cloudsql-password"
  replication {
    user_managed {
      replicas {
        location = var.region
      }
    }
  }
}

resource "google_secret_manager_secret_version" "db_pass_version" {
  secret      = google_secret_manager_secret.db_pass_secret.id
  secret_data = random_password.db_password.result
}

# --- 2. The Cloud SQL Instance (PostgreSQL) ---

resource "google_sql_database_instance" "postgres" {
  name             = "${var.project_id}-db"
  region           = var.region
  database_version = "POSTGRES_15"

  settings {
    tier = "db-custom-2-7680" # Cost-efficient tier. Adjust based on load.

    ip_configuration {
      ipv4_enabled    = false # No public IP for security
      private_network = var.network_id
    }

    backup_configuration {
      enabled    = true
      start_time = "02:00"
    }
  }

  deletion_protection = false # Set to true for production
}

resource "google_sql_user" "users" {
  name     = "postgres"
  instance = google_sql_database_instance.postgres.name
  password = random_password.db_password.result
}

# --- 4. Firestore (Short-Term Memory) ---

resource "google_firestore_database" "firestore" {
  project     = var.project_id
  name        = "(default)"
  location_id = var.region
  type        = "FIRESTORE_NATIVE"

  concurrency_mode = "OPTIMISTIC"

  delete_protection_state = "DELETE_PROTECTION_DISABLED"
}