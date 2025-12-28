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
  default     = ""
}

variable "iap_client_id" {
  description = "OAuth2 Client ID for IAP"
  type        = string
}

variable "iap_client_secret" {
  description = "OAuth2 Client Secret for IAP"
  type        = string
  sensitive   = true
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