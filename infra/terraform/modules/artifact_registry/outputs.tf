output "name" {
  description = "Artifact Registry repository resource name."
  value       = google_artifact_registry_repository.this.name
}

output "repository_id" {
  description = "Artifact Registry repository ID."
  value       = google_artifact_registry_repository.this.repository_id
}
