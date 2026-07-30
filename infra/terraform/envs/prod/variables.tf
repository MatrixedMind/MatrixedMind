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

variable "enable_observer_service_account" {
  description = "Create the keyless read-only production observer service account only through an approved operational plan."
  type        = bool
  default     = false
}

variable "observer_service_account_id" {
  description = "Service account ID for the production read-only observer."
  type        = string
  default     = "matrixedmind-prod-observer"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{4,28}[a-z0-9]$", var.observer_service_account_id))
    error_message = "observer_service_account_id must be a valid Google service-account ID."
  }
}

variable "observer_impersonator_member" {
  description = "User, group, or service-account IAM member permitted to impersonate the production observer without service-account keys."
  type        = string
  default     = null

  validation {
    condition = var.observer_impersonator_member == null || can(regex(
      "^(user|group|serviceAccount):[^[:space:]]+$",
      var.observer_impersonator_member,
    ))
    error_message = "observer_impersonator_member must be null or an explicit user, group, or serviceAccount IAM member."
  }
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

variable "llm_api_server_url" {
  description = "Canonical public HTTPS origin advertised by the hosted Custom GPT Action schema."
  type        = string
  default     = "https://matrixedmind.com"

  validation {
    condition     = can(regex("^https://[^/?#]+/?$", var.llm_api_server_url))
    error_message = "llm_api_server_url must be a public HTTPS origin without a path, query, or fragment."
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

variable "billing_account_id" {
  description = "Bare production billing account ID. Leave empty to keep the optional budget disabled."
  type        = string
  default     = ""
}

variable "billing_budget_amount_units" {
  description = "Monthly production budget amount in whole USD units. Set null to keep the optional budget disabled."
  type        = number
  default     = null

  validation {
    condition = var.billing_budget_amount_units == null || (
      var.billing_budget_amount_units > 0
      && floor(var.billing_budget_amount_units) == var.billing_budget_amount_units
    )
    error_message = "billing_budget_amount_units must be null or a positive whole number of USD units."
  }
}

variable "operational_notification_email" {
  description = "Optional production email destination for Terraform-managed MatrixedMind operational notifications. Supply only at apply time; Terraform state retains it."
  type        = string
  default     = null
  sensitive   = true

  validation {
    condition = var.operational_notification_email == null || (
      trimspace(var.operational_notification_email) != ""
      && !strcontains(var.operational_notification_email, "\n")
      && !strcontains(var.operational_notification_email, "\r")
      && can(regex("^[^@[:space:]]+@[^@[:space:]]+\\.[^@[:space:]]+$", var.operational_notification_email))
    )
    error_message = "operational_notification_email must be a single non-empty email address without line breaks."
  }
}

variable "external_operational_notification_channels" {
  description = "Optional externally managed full Cloud Monitoring channel resource names for production alert policies."
  type        = set(string)
  default     = []

  validation {
    condition = alltrue([
      for channel in var.external_operational_notification_channels :
      can(regex("^projects/[^/[:space:]]+/notificationChannels/[0-9]+$", channel))
    ])
    error_message = "external_operational_notification_channels must contain full Cloud Monitoring channel resource names."
  }
}

variable "external_budget_notification_channels" {
  description = "Optional externally managed email Cloud Monitoring channel resource names for the production billing budget. Verify their email type with read-only discovery before apply."
  type        = set(string)
  default     = []

  validation {
    condition = (
      alltrue([
        for channel in var.external_budget_notification_channels :
        can(regex("^projects/[^/[:space:]]+/notificationChannels/[0-9]+$", channel))
      ])
      && length(var.external_budget_notification_channels) + (var.operational_notification_email == null ? 0 : 1) <= 5
    )
    error_message = "external_budget_notification_channels must contain full email-channel resource names and, with the managed channel, total no more than five."
  }
}

variable "enable_billing_budget" {
  description = "Create the production billing budget only after its billing account, amount, and a managed or externally managed email notification channel are supplied."
  type        = bool
  default     = false

  validation {
    condition = (
      (
        var.enable_billing_budget
        && var.billing_account_id != ""
        && var.billing_budget_amount_units != null
        && (var.operational_notification_email != null || length(var.external_budget_notification_channels) > 0)
      )
      || (
        !var.enable_billing_budget
        && var.billing_account_id == ""
        && var.billing_budget_amount_units == null
      )
    )
    error_message = "When enable_billing_budget is true, set billing_account_id, billing_budget_amount_units, and a managed or external budget notification channel. When false, leave the budget inputs empty to avoid an unreviewed destruction plan."
  }
}

variable "enable_operational_alerting" {
  description = "Create Cloud Run health and error alert policies only after a managed or externally managed notification channel is supplied."
  type        = bool
  default     = false

  validation {
    condition     = !var.enable_operational_alerting || var.operational_notification_email != null || length(var.external_operational_notification_channels) > 0
    error_message = "operational_notification_email or external_operational_notification_channels must be set when enable_operational_alerting is true."
  }
}

variable "cloud_run_error_rate_threshold" {
  description = "Cloud Run 5xx request-rate threshold in requests per second."
  type        = number
  default     = 0.05

  validation {
    condition     = var.cloud_run_error_rate_threshold > 0
    error_message = "cloud_run_error_rate_threshold must be greater than zero."
  }
}

variable "cloud_run_latency_threshold_milliseconds" {
  description = "Cloud Run p99 request-latency threshold in milliseconds."
  type        = number
  default     = 10000

  validation {
    condition     = var.cloud_run_latency_threshold_milliseconds > 0
    error_message = "cloud_run_latency_threshold_milliseconds must be greater than zero."
  }
}
