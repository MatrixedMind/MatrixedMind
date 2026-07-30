output "artifact_registry_repository" {
  description = "Production Artifact Registry Docker repository resource name."
  value       = module.artifact_registry.name
}

output "container_image_prefix" {
  description = "Prefix for production MatrixedMind container image tags."
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${module.artifact_registry.repository_id}/matrixedmind"
}

output "runtime_service_account_email" {
  description = "Production Cloud Run runtime service account email."
  value       = google_service_account.runtime.email
}

output "github_deployer_service_account_email" {
  description = "Production GitHub Actions deployer service account email."
  value       = google_service_account.github_deployer.email
}

output "workload_identity_provider" {
  description = "Production Workload Identity Provider resource for GitHub Actions auth."
  value       = google_iam_workload_identity_pool_provider.github.name
}

output "runtime_secret_ids" {
  description = "Production Secret Manager entries that require owner-provided versions."
  value       = sort(values(module.runtime_secrets.secret_ids))
}

output "firestore_database" {
  description = "Production Firestore Enterprise MongoDB-compatible database resource."
  value       = google_firestore_database.mongo_compatible.id
}

output "cloud_run_service_uri" {
  description = "Production Cloud Run service URI when enable_cloud_run_service is true."
  value       = var.enable_cloud_run_service ? module.cloud_run_service[0].uri : null
}

output "cloud_run_serverless_neg_id" {
  description = "Production-project serverless NEG when external-load-balancer mode is enabled."
  value = (
    var.enable_cloud_run_service
    ? module.cloud_run_service[0].serverless_neg_id
    : null
  )
}

output "cloud_run_load_balancer_backend_service_self_link" {
  description = "Fully qualified production backend-service reference for the separate edge project's URL map."
  value = (
    var.enable_cloud_run_service
    ? module.cloud_run_service[0].load_balancer_backend_service_self_link
    : null
  )
}

output "openai_action_allowlist_security_policy_id" {
  description = "Optional production Cloud Armor source policy when a reviewed address group is configured."
  value = (
    var.enable_cloud_run_service
    ? module.cloud_run_service[0].action_allowlist_security_policy_id
    : null
  )
}
