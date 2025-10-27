output "cloud_run_url" {
  description = "Base URL of the deployed Cloud Run service"
  value       = google_cloud_run_service.notes_service.status[0].url
}

output "service_account_email" {
  description = "Service account used by Cloud Run"
  value       = google_service_account.notes_sa.email
}

output "bucket_name" {
  description = "Name of the GCS bucket for notes"
  value       = google_storage_bucket.notes_bucket.name
}
