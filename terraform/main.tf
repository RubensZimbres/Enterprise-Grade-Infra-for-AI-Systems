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

module "compute" {
  source = "./modules/compute"

  project_id   = var.project_id
  region       = var.region
  vpc_name     = module.network.vpc_name
  subnet_name  = module.network.private_subnet_name
  alloydb_ip   = module.database.instance_ip
  db_secret_id = module.database.secret_id
  depends_on   = [module.database, module.network]
}

module "ingress" {
  source = "./modules/ingress"

  project_id            = var.project_id
  region                = var.region
  frontend_service_name = module.compute.frontend_name
  domain_name           = var.domain_name
  iap_client_id         = var.iap_client_id
  iap_client_secret     = var.iap_client_secret
  depends_on            = [module.compute]
}

# Output the IP so you know where to point your DNS
output "public_ip" {
  value = module.ingress.load_balancer_ip
}