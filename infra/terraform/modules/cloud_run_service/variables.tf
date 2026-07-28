variable "project_id" {
  description = "GCP project that owns the Cloud Run service."
  type        = string
}

variable "name" {
  description = "Cloud Run service name."
  type        = string
}

variable "location" {
  description = "Cloud Run service location."
  type        = string
}

variable "container_image" {
  description = "Initial container image URI. Later image revisions are deployed by CI."
  type        = string
}

variable "service_account_email" {
  description = "Runtime service account email."
  type        = string
}

variable "environment_variables" {
  description = "Non-secret environment variables."
  type        = map(string)
}

variable "secret_environment_variables" {
  description = "Secret Manager environment variables with explicit versions."
  type = map(object({
    secret_id = string
    version   = string
  }))
}

variable "allow_unauthenticated" {
  description = "Grant allUsers the Cloud Run invoker role."
  type        = bool
  default     = false
}

variable "invoker_members" {
  description = "IAM members allowed to invoke the service while it is private."
  type        = set(string)
  default     = []
}

variable "ingress" {
  description = "Cloud Run ingress setting."
  type        = string
  default     = "INGRESS_TRAFFIC_ALL"
}

variable "deletion_protection" {
  description = "Protect the Cloud Run service from deletion."
  type        = bool
  default     = true
}

variable "min_instance_count" {
  description = "Minimum Cloud Run instance count."
  type        = number
  default     = 0
}

variable "max_instance_count" {
  description = "Maximum Cloud Run instance count."
  type        = number
  default     = 2
}
