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

variable "invoker_members" {
  description = "IAM members allowed to invoke the service while it is private."
  type        = set(string)
  default     = []
}

variable "invocation_mode" {
  description = "Exclusive Cloud Run invocation mode: private, direct public, or application-project backend for an external load balancer."
  type        = string
  default     = "private"

  validation {
    condition = contains(
      ["private", "direct", "external_load_balancer"],
      var.invocation_mode,
    )
    error_message = "invocation_mode must be private, direct, or external_load_balancer."
  }
}

variable "load_balancer_backend_service_name" {
  description = "Optional name for the MatrixedMind backend service created beside the Cloud Run service and serverless NEG."
  type        = string
  default     = null
}

variable "external_load_balancer_scheme" {
  description = "Scheme for the application-project backend service. Cross-project attachment requires EXTERNAL_MANAGED."
  type        = string
  default     = "EXTERNAL_MANAGED"

  validation {
    condition = contains(
      ["EXTERNAL", "EXTERNAL_MANAGED"],
      var.external_load_balancer_scheme,
    )
    error_message = "external_load_balancer_scheme must be EXTERNAL or EXTERNAL_MANAGED."
  }
}

variable "load_balancer_service_user_members" {
  description = "IAM members allowed to reference the backend service from a separate load-balancer project."
  type        = set(string)
  default     = []

  validation {
    condition = alltrue([
      for member in var.load_balancer_service_user_members :
      can(regex("^(group|serviceAccount|user):[^[:space:]]+$", member))
    ])
    error_message = "load_balancer_service_user_members must contain explicit user, group, or serviceAccount IAM members."
  }
}

variable "openai_action_address_group_name" {
  description = "Optional reviewed Cloud Armor Enterprise address group containing the current ChatGPT-integration ranges. Null disables the network allowlist."
  type        = string
  default     = null

  validation {
    condition = (
      var.openai_action_address_group_name == null
      || can(regex("^[a-z][a-z0-9-]{0,62}$", var.openai_action_address_group_name))
    )
    error_message = "openai_action_address_group_name must be null or a valid address-group name."
  }
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
