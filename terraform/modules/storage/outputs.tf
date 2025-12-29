output "data_bucket_name" {
  value = google_storage_bucket.data_bucket.name
}

output "source_bucket_name" {
  value = google_storage_bucket.source_bucket.name
}