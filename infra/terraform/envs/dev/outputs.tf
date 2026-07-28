output "artifact_registry_repository" {
  description = "Artifact Registry Docker repository resource name."
  value       = module.artifact_registry.name
}

output "container_image_prefix" {
  description = "Prefix for MatrixedMind container image tags."
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${module.artifact_registry.repository_id}/matrixedmind"
}

output "runtime_service_account_email" {
  description = "Cloud Run runtime service account email."
  value       = google_service_account.runtime.email
}

output "firestore_spike_service_account_email" {
  description = "Cloud Run Job service account for Firestore compatibility verification."
  value       = google_service_account.firestore_spike.email
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
  value       = sort(values(module.runtime_secrets.secret_ids))
}

output "firestore_database" {
  description = "Firestore Enterprise MongoDB-compatible database resource."
  value       = google_firestore_database.mongo_compatible.id
}

output "cloud_run_service_uri" {
  description = "Cloud Run service URI when enable_cloud_run_service is true."
  value       = var.enable_cloud_run_service ? module.cloud_run_service[0].uri : null
}

output "firestore_spike_job_name" {
  description = "Firestore compatibility Cloud Run Job name when enabled."
  value       = var.enable_firestore_spike_job ? google_cloud_run_v2_job.firestore_spike[0].name : null
}
