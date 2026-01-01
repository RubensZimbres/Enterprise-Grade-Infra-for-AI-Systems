output "host" {
  value = google_redis_instance.cache.host
}

output "auth_string" {
  value     = google_redis_instance.cache.auth_string
  sensitive = true
}