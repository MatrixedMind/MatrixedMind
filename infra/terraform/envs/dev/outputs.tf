output "artifact_registry_repository" {
  description = "Artifact Registry Docker repository resource name."
  value       = google_artifact_registry_repository.containers.name
}

output "container_image_prefix" {
  description = "Prefix for MatrixedMind container image tags."
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.containers.repository_id}/matrixedmind"
}

output "runtime_service_account_email" {
  description = "Cloud Run runtime service account email."
  value       = google_service_account.runtime.email
}

output "github_deployer_service_account_email" {
  description = "GitHub Actions deployer service account email."
  value       = google_service_account.github_deployer.email
}

output "workload_identity_provider" {
  description = "Workload Identity Provider resource for GitHub Actions auth."
  value       = google_iam_workload_identity_pool_provider.github.name
}

output "runtime_secret_ids" {
  description = "Secret Manager entries that require owner-provided versions."
  value       = sort([for secret in google_secret_manager_secret.runtime : secret.secret_id])
}

output "firestore_database" {
  description = "Firestore Enterprise MongoDB-compatible database resource."
  value       = google_firestore_database.mongo_compatible.id
}

output "cloud_run_service_uri" {
  description = "Cloud Run service URI when enable_cloud_run_service is true."
  value       = var.enable_cloud_run_service ? google_cloud_run_v2_service.app[0].uri : null
}
