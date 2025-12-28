output "network_id" {
  value = google_compute_network.vpc.id
}

output "vpc_name" {
  value = google_compute_network.vpc.name
}

output "private_subnet_name" {
  value = google_compute_subnetwork.private_subnet.name
}

output "private_vpc_connection" {
  # This output ensures other modules wait for the PSA peering to finish
  value = google_service_networking_connection.default.network
}