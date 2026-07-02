variable "project_id" {
  description = "GCP project ID for the MatrixedMind dev Cloud MVP environment."
  type        = string
}

variable "region" {
  description = "Primary GCP region for Cloud Run and Artifact Registry."
  type        = string
  default     = "us-central1"
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
  default     = "matrixedmind-dev-github-deployer"
}

variable "github_repository" {
  description = "GitHub repository allowed to use Workload Identity Federation, in owner/repo form."
  type        = string
}

variable "firestore_database_id" {
  description = "Firestore Enterprise MongoDB-compatible database ID."
  type        = string
  default     = "matrixedmind-dev"
}

variable "firestore_location_id" {
  description = "Firestore database location. Choose a supported Firestore location for the project."
  type        = string
  default     = "nam5"
}

variable "enable_cloud_run_service" {
  description = "Create the Cloud Run service. Enable after the container image and secret values exist."
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
}

variable "allow_unauthenticated_cloud_run" {
  description = "Grant allUsers Cloud Run invoker. Keep false until app-level auth protects sensitive routes."
  type        = bool
  default     = false
}

variable "billing_account_id" {
  description = "Billing account resource ID, for example billingAccounts/000000-000000-000000. Leave empty to skip budget creation."
  type        = string
  default     = ""
}

variable "billing_budget_amount_units" {
  description = "Monthly budget amount in whole USD units. Set null to skip budget creation."
  type        = number
  default     = null
}
