variable "project_id" {
  description = "GCP project ID for the MatrixedMind dev Cloud MVP environment."
  type        = string
}

variable "region" {
  description = "Primary GCP region for Cloud Run and Artifact Registry."
  type        = string
  default     = "us-west1"
}

variable "artifact_registry_repository_id" {
  description = "Artifact Registry Docker repository ID."
  type        = string
  default     = "matrixedmind"
}

variable "runtime_service_account_id" {
  description = "Runtime service account ID for Cloud Run."
  type        = string
  default     = "matrixedmind-dev-runtime"
}

variable "github_deployer_service_account_id" {
  description = "GitHub Actions deployer service account ID."
  type        = string
  default     = "matrixedmind-dev-deployer"
}

variable "firestore_spike_service_account_id" {
  description = "Service account ID for the GCP-hosted Firestore compatibility test job."
  type        = string
  default     = "matrixedmind-dev-fs-spike"
}

variable "github_repository" {
  description = "GitHub repository allowed to use Workload Identity Federation, in owner/repo form."
  type        = string
}

variable "firestore_database_id" {
  description = "Firestore Enterprise MongoDB-compatible database ID."
  type        = string
  default     = "matrixedmind-spike"
}

variable "firestore_location_id" {
  description = "Firestore database location. Choose a supported Firestore location for the project."
  type        = string
  default     = "us-west1"
}

variable "enable_cloud_run_service" {
  description = "Create the Cloud Run service. Enable after the application image exists."
  type        = bool
  default     = false
}

variable "cloud_run_service_name" {
  description = "Cloud Run service name."
  type        = string
  default     = "matrixedmind-dev"
}

variable "container_image" {
  description = "Container image URI for Cloud Run, required when enable_cloud_run_service is true."
  type        = string
  default     = ""

  validation {
    condition     = !var.enable_cloud_run_service || var.container_image != ""
    error_message = "container_image must be set when enable_cloud_run_service is true."
  }
}

variable "app_secret_key_version" {
  description = "Explicit Secret Manager version for APP_SECRET_KEY."
  type        = string
  default     = "1"

  validation {
    condition     = can(regex("^[1-9][0-9]*$", var.app_secret_key_version))
    error_message = "app_secret_key_version must be an explicit positive numeric version."
  }
}

variable "llm_token_pepper_version" {
  description = "Explicit Secret Manager version for LLM_TOKEN_PEPPER."
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
  description = "Public HTTPS source repository used by the hosted AGPL source offer."
  type        = string
  default     = "https://github.com/MatrixedMind/MatrixedMind"

  validation {
    condition     = can(regex("^https://[^/?#]+(/[^?#]*)?$", var.source_repository_url))
    error_message = "source_repository_url must be a public HTTPS repository URL without query or fragment."
  }
}

variable "enable_firestore_spike_job" {
  description = "Create the Cloud Run Job that runs the Firestore compatibility suite in GCP."
  type        = bool
  default     = false
}

variable "firestore_spike_job_name" {
  description = "Cloud Run Job name for Firestore MongoDB compatibility verification."
  type        = string
  default     = "matrixedmind-firestore-spike"
}

variable "firestore_spike_image" {
  description = "Test image URI containing the Firestore compatibility suite."
  type        = string
  default     = ""
}

variable "billing_account_id" {
  description = "Bare billing account ID, for example 000000-000000-000000. Leave empty to skip budget creation."
  type        = string
  default     = ""
}

variable "billing_budget_amount_units" {
  description = "Monthly budget amount in whole USD units. Set null to skip budget creation."
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
  description = "Optional development email destination for Terraform-managed MatrixedMind operational notifications. Supply only at apply time; Terraform state retains it."
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
  description = "Optional externally managed full Cloud Monitoring channel resource names for development alert policies."
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
  description = "Optional externally managed email Cloud Monitoring channel resource names for the development billing budget. Verify their email type with read-only discovery before apply."
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
  description = "Create the development billing budget only after its billing account, amount, and a managed or externally managed email notification channel are supplied."
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
