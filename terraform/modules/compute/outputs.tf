output "frontend_url" {
  value = google_cloud_run_v2_service.frontend.uri
}

output "backend_url" {
  value = google_cloud_run_v2_service.backend.uri
}

output "frontend_name" {
  value = google_cloud_run_v2_service.frontend.name
}

output "frontend_sa_email" {
  value = google_service_account.frontend_sa.email
}