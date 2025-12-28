resource "google_redis_instance" "cache" {
  name           = "ai-cache"
  memory_size_gb = 1
  region         = var.region
  project        = var.project_id

  authorized_network = var.network_id
  connect_mode       = "DIRECT_PEERING"

  redis_version     = "REDIS_6_X"
  display_name      = "AI Platform Cache"

  auth_enabled            = true
  transit_encryption_mode = "SERVER_AUTHENTICATION"
}
