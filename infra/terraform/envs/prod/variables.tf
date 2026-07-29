variable "project_id" {
  description = "GCP project ID for the MatrixedMind production application environment."
  type        = string
}

variable "region" {
  description = "Primary GCP region for production Cloud Run, Firestore, and Artifact Registry resources."
  type        = string
  default     = "us-west1"
}

variable "artifact_registry_repository_id" {
  description = "Production Artifact Registry Docker repository ID."
  type        = string
  default     = "matrixedmind"
}

variable "runtime_service_account_id" {
  description = "Production Cloud Run runtime service account ID."
  type        = string
  default     = "matrixedmind-prod-runtime"
}

variable "github_deployer_service_account_id" {
  description = "Production GitHub Actions deployer service account ID."
  type        = string
  default     = "matrixedmind-prod-deployer"
}

variable "github_repository" {
  description = "GitHub repository allowed to use production Workload Identity Federation, in owner/repo form."
  type        = string
}

variable "firestore_database_id" {
  description = "Production Firestore Enterprise MongoDB-compatible database ID."
  type        = string
  default     = "matrixedmind-prod"
}

variable "firestore_location_id" {
  description = "Production Firestore database location."
  type        = string
  default     = "us-west1"
}

variable "enable_cloud_run_service" {
  description = "Create the production Cloud Run service after its image and numbered secret versions exist."
  type        = bool
  default     = false
}

variable "cloud_run_service_name" {
  description = "Production Cloud Run service name."
  type        = string
  default     = "matrixedmind-prod"
}

variable "container_image" {
  description = "Initial production container image URI, required when enable_cloud_run_service is true."
  type        = string
  default     = ""

  validation {
    condition     = !var.enable_cloud_run_service || var.container_image != ""
    error_message = "container_image must be set when enable_cloud_run_service is true."
  }
}

variable "app_secret_key_version" {
  description = "Explicit production Secret Manager version for APP_SECRET_KEY."
  type        = string
  default     = "1"

  validation {
    condition     = can(regex("^[1-9][0-9]*$", var.app_secret_key_version))
    error_message = "app_secret_key_version must be an explicit positive numeric version."
  }
}

variable "llm_token_pepper_version" {
  description = "Explicit production Secret Manager version for LLM_TOKEN_PEPPER."
  type        = string
  default     = "1"

  validation {
    condition     = can(regex("^[1-9][0-9]*$", var.llm_token_pepper_version))
    error_message = "llm_token_pepper_version must be an explicit positive numeric version."
  }
}

variable "markdown_image_source_allowlist" {
  description = "Optional comma-separated exact or wildcard hosts allowed for rendered HTTPS Markdown images."
  type        = string
  default     = ""
}

variable "source_repository_url" {
  description = "Public HTTPS source repository used by the production AGPL source offer."
  type        = string
  default     = "https://github.com/MatrixedMind/MatrixedMind"

  validation {
    condition     = can(regex("^https://[^/?#]+(/[^?#]*)?$", var.source_repository_url))
    error_message = "source_repository_url must be a public HTTPS repository URL without query or fragment."
  }
}

variable "cloud_run_invocation_mode" {
  description = "Production Cloud Run mode: private staging or the cross-project external-load-balancer backend."
  type        = string
  default     = "private"

  validation {
    condition     = contains(["private", "external_load_balancer"], var.cloud_run_invocation_mode)
    error_message = "cloud_run_invocation_mode must be private or external_load_balancer in the production root."
  }
}

variable "load_balancer_backend_service_name" {
  description = "Optional production backend-service name; the backend remains in the production application project."
  type        = string
  default     = null
}

variable "edge_load_balancer_service_user_members" {
  description = "Explicit edge-project administrators allowed to attach the production backend service to a cross-project URL map."
  type        = set(string)
  default     = []

  validation {
    condition = alltrue([
      for member in var.edge_load_balancer_service_user_members :
      can(regex("^(group|serviceAccount|user):[^[:space:]]+$", member))
    ])
    error_message = "edge_load_balancer_service_user_members must contain explicit user, group, or serviceAccount IAM members."
  }
}

variable "openai_action_address_group_name" {
  description = "Optional reviewed production Cloud Armor Enterprise address group for ChatGPT-integration source ranges."
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
