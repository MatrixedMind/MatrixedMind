variable "project_id" {
  description = "GCP project ID to deploy into"
  type        = string
}

variable "region" {
  description = "Region for Cloud Run (e.g. us-west1)"
  type        = string
  default     = "us-west1"
}

variable "bucket_name" {
  description = "GCS bucket name for notes storage"
  type        = string
}

variable "service_name" {
  description = "Name of the Cloud Run service"
  type        = string
  default     = "matrixedmind-api"
}

variable "api_key" {
  description = "Shared secret for X-Notes-Key auth"
  type        = string
  sensitive   = true
}

variable "container_image" {
  description = "Container image URI for Cloud Run, e.g. us-west1-docker.pkg.dev/PROJECT/matrixedmind-repo/notes-api:v1"
  type        = string
}
