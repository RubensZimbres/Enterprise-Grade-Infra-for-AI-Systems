resource "random_id" "bucket_suffix" {
  byte_length = 4
}

resource "google_storage_bucket" "data_bucket" {
  name          = "${var.bucket_name_prefix}-${random_id.bucket_suffix.hex}"
  location      = var.region
  force_destroy = true

  uniform_bucket_level_access = true
}

# Bucket for Cloud Function Source Code
resource "google_storage_bucket" "source_bucket" {
  name          = "${var.project_id}-gcf-source-${random_id.bucket_suffix.hex}"
  location      = var.region
  force_destroy = true
  uniform_bucket_level_access = true
}