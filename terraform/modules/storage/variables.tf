variable "project_id" {
  description = "The project ID"
  type        = string
}

variable "region" {
  description = "The region"
  type        = string
}

variable "bucket_name_prefix" {
  description = "Prefix for the bucket name"
  type        = string
  default     = "pdf-ingest-data"
}