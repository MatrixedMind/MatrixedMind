output "tf_state_bucket_name" {
  description = "GCS bucket name to pass to environment terraform init commands."
  value       = google_storage_bucket.tf_state.name
}
