resource "random_id" "bucket_suffix" {
  byte_length = 4
}

resource "google_storage_bucket" "data_bucket" {
  name          = "${var.bucket_name_prefix}-${random_id.bucket_suffix.hex}"
  location      = var.region
  force_destroy = true

  uniform_bucket_level_access = true

  # 1. Enable Versioning for Disaster Recovery
  versioning {
    enabled = true
  }

  # 2. Cost Optimization: Move old versions to cheaper storage
  lifecycle_rule {
    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }
    condition {
      num_newer_versions = 1  # Only move if it's not the latest version
      days_since_noncurrent_time = 7
    }
  }

  lifecycle_rule {
    action {
      type          = "SetStorageClass"
      storage_class = "ARCHIVE"
    }
    condition {
      num_newer_versions = 1
      days_since_noncurrent_time = 30
    }
  }

  # 3. Cleanup: Delete versions older than 90 days
  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      num_newer_versions = 1
      days_since_noncurrent_time = 90
    }
  }
}

# Bucket for Cloud Function Source Code
resource "google_storage_bucket" "source_bucket" {
  name          = "${var.project_id}-gcf-source-${random_id.bucket_suffix.hex}"
  location      = var.region
  force_destroy = true
  uniform_bucket_level_access = true
  # Source code buckets generally don't need complex versioning rules 
  # as they are re-built from Git, but keeping recent versions is safe.
  versioning {
    enabled = true
  }
}