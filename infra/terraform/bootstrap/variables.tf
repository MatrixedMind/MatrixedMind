variable "project_id" {
  description = "GCP project ID that owns the Terraform state bucket."
  type        = string
}

variable "region" {
  description = "Default provider region for bootstrap resources."
  type        = string
  default     = "us-central1"
}

variable "tf_state_bucket_name" {
  description = "Globally unique GCS bucket name for Terraform state."
  type        = string
}

variable "tf_state_bucket_location" {
  description = "GCS location for Terraform state."
  type        = string
  default     = "US"
}
