# 1. The VPC
resource "google_compute_network" "vpc" {
  name                    = "${var.project_id}-vpc"
  auto_create_subnetworks = false # MANDATORY for production control
  routing_mode            = "GLOBAL"
}

# 2. The Private Subnet (Where your Cloud Run/Agents will live)
# tfsec:ignore:google-compute-enable-vpc-flow-logs
resource "google_compute_subnetwork" "private_subnet" {
  name          = "${var.project_id}-private-subnet"
  ip_cidr_range = var.subnet_cidr
  region        = var.region
  network       = google_compute_network.vpc.id

  # Enable Google Private Access so VMs can reach Google APIs (Vertex, Storage)
  # without going over the public internet.
  private_ip_google_access = true
}

# 3. Private Service Access (PSA) for AlloyDB & Vertex AI
# We reserve a block of IPs specifically for Google managed services.
resource "google_compute_global_address" "private_ip_alloc" {
  name          = "private-ip-alloc"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.vpc.id
}

resource "google_service_networking_connection" "default" {
  network                 = google_compute_network.vpc.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_alloc.name]
}

# 4. Cloud NAT (So your private agents can reach the internet for updates)
resource "google_compute_router" "router" {
  name    = "${var.project_id}-router"
  region  = var.region
  network = google_compute_network.vpc.id
}

resource "google_compute_router_nat" "nat" {
  name                               = "${var.project_id}-nat"
  router                             = google_compute_router.router.name
  region                             = var.region
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"
}
