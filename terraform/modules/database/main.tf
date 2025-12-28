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
  secret_id = "${var.project_id}-alloydb-password"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "db_pass_version" {
  secret = google_secret_manager_secret.db_pass_secret.id
  secret_data = random_password.db_password.result
}

# --- 2. The AlloyDB Cluster ---

resource "google_alloydb_cluster" "default" {
  cluster_id = "${var.project_id}-alloydb-cluster"
  location   = var.region
  network    = var.network_id # Must come from the Network Module

  initial_user {
    user     = "postgres"
    password = random_password.db_password.result
  }

  # AUTOMATED BACKUP POLICY (As per your diagram's "Storage Backup" note)
  automated_backup_policy {
    location      = var.region
    backup_window = "1800s"
    enabled       = true
    weekly_schedule {
      days_of_week = ["MONDAY", "THURSDAY"]
      
      start_times {
        hours   = 2
        minutes = 0
        seconds = 0
        nanos   = 0
      }
    }
    quantity_based_retention {
      count = 7
    }
  }
}

# --- 3. The AlloyDB Instance (Primary) ---

resource "google_alloydb_instance" "primary" {
  cluster       = google_alloydb_cluster.default.name
  instance_id   = "${var.project_id}-alloydb-primary"
  instance_type = "PRIMARY"

  # Scalability settings
  machine_config {
    cpu_count = 2 # Minimum for AlloyDB. Increase for production load.
  }

  # Flags to optimize for Vector Search (pgvector)
  database_flags = {
    "work_mem" = "64MB" 
    # Note: pgvector extension must be enabled via SQL ("CREATE EXTENSION vector;")
    # Terraform builds the house; it doesn't furnish the rooms.
  }
}

# --- 3.1 The AlloyDB Instance (Read Pool) ---

resource "google_alloydb_instance" "read_pool" {
  cluster       = google_alloydb_cluster.default.name
  instance_id   = "${var.project_id}-alloydb-read-pool"
  instance_type = "READ_POOL"

  read_pool_config {
    node_count = 2 # Scaling read capacity horizontally
  }

  machine_config {
    cpu_count = 2 
  }

  depends_on = [google_alloydb_instance.primary]
}

# --- 4. Firestore (Short-Term Memory) ---

resource "google_firestore_database" "firestore" {
  project     = var.project_id
  name        = "(default)"
  # Firestore locations are sticky. Once set, they cannot be changed.
  # We match the region used for the rest of the stack.
  location_id = var.region 
  type        = "FIRESTORE_NATIVE"

  # concurrency_mode: OPTIMISTIC is standard for modern apps to handle
  # race conditions without aggressive locking.
  concurrency_mode = "OPTIMISTIC" 
  
  # Delete protection prevents accidental wiping of your user history.
  # Set to false only if you are in a sandbox/dev environment.
  delete_protection_state = "DELETE_PROTECTION_DISABLED"
}