# /terraform/main.tf

# /terraform/main.tf

module "network" {
  source = "./modules/network"

  project_id  = var.project_id  # CHANGED from local.project_id
  region      = var.region      # CHANGED from local.region
  subnet_cidr = "10.0.0.0/24"
}

module "database" {
  source = "./modules/database"

  project_id = var.project_id
  region     = var.region
  network_id = module.network.network_id
  depends_on = [module.network]
}

module "redis" {
  source = "./modules/redis"

  project_id = var.project_id
  region     = var.region
  network_id = module.network.network_id
  depends_on = [module.network]
}

module "compute" {
  source = "./modules/compute"

  project_id   = var.project_id
  region       = var.region
  vpc_name     = module.network.vpc_name
  subnet_name  = module.network.private_subnet_name
  db_host      = module.database.instance_ip
  db_secret_id = module.database.secret_id
  redis_host   = module.redis.host
  depends_on   = [module.database, module.network, module.redis]
}

module "billing_monitoring" {
  source = "./modules/billing_monitoring"

  project_id         = var.project_id
  billing_account    = var.billing_account
  notification_email = var.notification_email
}

module "ingress" {
  source = "./modules/ingress"

  project_id            = var.project_id
  region                = var.region
  frontend_service_name = module.compute.frontend_name
  domain_name           = var.domain_name
  depends_on            = [module.compute]
}

# Output the IP so you know where to point your DNS
output "public_ip" {
  value = module.ingress.load_balancer_ip
}

module "storage" {
  source = "./modules/storage"

  project_id = var.project_id
  region     = var.region
}

module "function" {
  source = "./modules/function"

  project_id            = var.project_id
  region                = var.region
  bucket_name           = module.storage.data_bucket_name
  source_bucket_name    = module.storage.source_bucket_name
  db_host               = module.database.instance_ip
  db_name               = "postgres" # Default
  db_user               = "postgres" # Default
  db_password_secret_id = module.database.secret_id
  depends_on            = [module.database, module.storage]
}

# Secrets for Stripe
resource "google_secret_manager_secret" "stripe_publishable_key" {
  secret_id = "STRIPE_PUBLISHABLE_KEY"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret" "stripe_secret_key" {
  secret_id = "STRIPE_SECRET_KEY"
  replication {
    auto {}
  }
}

# Allow Frontend to access Stripe Secrets ONLY
resource "google_secret_manager_secret_iam_member" "frontend_stripe_publishable_key_access" {
  secret_id = google_secret_manager_secret.stripe_publishable_key.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${module.compute.frontend_sa_email}"
}

# Redis Password Secret
resource "google_secret_manager_secret" "redis_password" {
  secret_id = "REDIS_PASSWORD"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "redis_password_version" {
  secret      = google_secret_manager_secret.redis_password.id
  secret_data = module.redis.auth_string
}

resource "google_secret_manager_secret_iam_member" "backend_redis_password_access" {
  secret_id = google_secret_manager_secret.redis_password.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${module.compute.backend_sa_email}"
}

module "cicd" {
  source = "./modules/cicd"

  project_id       = var.project_id
  region           = var.region
  github_owner     = var.github_owner
  github_repo_name = var.github_repo_name
}

