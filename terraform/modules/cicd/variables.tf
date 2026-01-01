variable "project_id" {
  description = "The GCP Project ID"
  type        = string
}

variable "region" {
  description = "The GCP region"
  type        = string
}

variable "github_owner" {
  description = "The GitHub repository owner (username or organization)"
  type        = string
}

variable "github_repo_name" {
  description = "The GitHub repository name"
  type        = string
}
