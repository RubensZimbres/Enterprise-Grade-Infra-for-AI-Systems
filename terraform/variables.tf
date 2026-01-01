variable "project_id" {
  description = "Google Cloud Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "us-central1"
}

variable "domain_name" {
  description = "Domain name for the frontend (e.g., ai.example.com)"
  type        = string
}

variable "billing_account" {
  description = "The billing account ID"
  type        = string
  default     = "11111111111111111"
}

variable "notification_email" {
  description = "Email for budget and anomaly alerts"
  type        = string
  default     = "user@gmail.com"
}

variable "github_owner" {
  description = "The GitHub repository owner"
  type        = string
}

variable "github_repo_name" {
  description = "The GitHub repository name"
  type        = string
}
