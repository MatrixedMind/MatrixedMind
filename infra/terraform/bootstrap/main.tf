provider "google" {
  project = var.project_id
  region  = var.region
}

resource "google_project_service" "storage" {
  project = var.project_id
  service = "storage.googleapis.com"

  disable_on_destroy = false
}

resource "google_storage_bucket" "tf_state" {
  name     = var.tf_state_bucket_name
  project  = var.project_id
  location = var.tf_state_bucket_location

  public_access_prevention    = "enforced"
  uniform_bucket_level_access = true
  force_destroy               = false

  versioning {
    enabled = true
  }

  depends_on = [google_project_service.storage]
}
