resource "google_secret_manager_secret" "this" {
  for_each = var.secrets

  project   = var.project_id
  secret_id = each.value.secret_id

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_iam_member" "accessor" {
  for_each = var.secrets

  project   = var.project_id
  secret_id = google_secret_manager_secret.this[each.key].secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = var.accessor_member
}
