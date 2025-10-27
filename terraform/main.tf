provider "google" {
  project = var.project_id
  region  = var.region
}

#
# Enable required services/APIs
#
resource "google_project_service" "run_api" {
  project = var.project_id
  service = "run.googleapis.com"
}

resource "google_project_service" "artifact_api" {
  project = var.project_id
  service = "artifactregistry.googleapis.com"
}

resource "google_project_service" "storage_api" {
  project = var.project_id
  service = "storage.googleapis.com"
}

resource "google_project_service" "secretmanager_api" {
  project = var.project_id
  service = "secretmanager.googleapis.com"
}

#
# GCS bucket for notes
#
resource "google_storage_bucket" "notes_bucket" {
  name          = var.bucket_name
  location      = var.region
  force_destroy = false

  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"

  versioning {
    enabled = true
  }
}

#
# Service account for Cloud Run
#
resource "google_service_account" "notes_sa" {
  account_id   = "${var.service_name}-sa"
  display_name = "Service Account for MatrixedMind Notes API"
}

#
# Secret Manager secret for the API key
#
resource "google_secret_manager_secret" "notes_api_key" {
  secret_id = "${var.service_name}-notes-api-key"
  replication {
    automatic = true
  }
}

resource "google_secret_manager_secret_version" "notes_api_key" {
  secret      = google_secret_manager_secret.notes_api_key.id
  secret_data = var.api_key
}

resource "google_secret_manager_secret_iam_member" "notes_api_key_accessor" {
  project   = google_secret_manager_secret.notes_api_key.project
  secret_id = google_secret_manager_secret.notes_api_key.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.notes_sa.email}"
}

#
# IAM binding: allow service account to read/write objects in the bucket
#
resource "google_storage_bucket_iam_member" "notes_rw" {
  bucket = google_storage_bucket.notes_bucket.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.notes_sa.email}"
}

#
# Artifact Registry repository (for container images)
#
resource "google_artifact_registry_repository" "notes_repo" {
  location       = var.region
  repository_id  = "${var.service_name}-repo"
  description    = "Container images for MatrixedMind"
  format         = "DOCKER"
}

#
# Cloud Run service
#
resource "google_cloud_run_service" "notes_service" {
  name     = var.service_name
  location = var.region

  template {
    spec {
      service_account_name = google_service_account.notes_sa.email

      containers {
        image = var.container_image

        env {
          name  = "NOTES_API_KEY"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.notes_api_key.secret_id
              version = "latest"
            }
          }
        }

        env {
          name  = "NOTES_BUCKET"
          value = google_storage_bucket.notes_bucket.name
        }

        env {
          name  = "PORT"
          value = "8080"
        }
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }

  autogenerate_revision_name = true
}

#
# Make Cloud Run publicly invokable
#
resource "google_cloud_run_service_iam_member" "invoker" {
  location = google_cloud_run_service.notes_service.location
  service  = google_cloud_run_service.notes_service.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
