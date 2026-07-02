provider "google" {
  project = var.project_id
  region  = var.region
}

data "google_project" "current" {
  project_id = var.project_id
}

locals {
  required_services = toset([
    "artifactregistry.googleapis.com",
    "billingbudgets.googleapis.com",
    "cloudbuild.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "firestore.googleapis.com",
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
    "run.googleapis.com",
    "secretmanager.googleapis.com",
    "sts.googleapis.com",
  ])

  runtime_secret_ids = toset([
    "matrixedmind-dev-mongo-uri",
    "matrixedmind-dev-app-secret-key",
    "matrixedmind-dev-llm-token-pepper",
  ])
}

resource "google_project_service" "required" {
  for_each = local.required_services

  project = var.project_id
  service = each.value

  disable_on_destroy = false
}

resource "google_artifact_registry_repository" "containers" {
  project       = var.project_id
  location      = var.region
  repository_id = var.artifact_registry_repository_id
  description   = "MatrixedMind container images"
  format        = "DOCKER"

  depends_on = [google_project_service.required]
}

resource "google_service_account" "runtime" {
  project      = var.project_id
  account_id   = var.runtime_service_account_id
  display_name = "MatrixedMind dev runtime"

  depends_on = [google_project_service.required]
}

resource "google_service_account" "github_deployer" {
  project      = var.project_id
  account_id   = var.github_deployer_service_account_id
  display_name = "MatrixedMind dev GitHub Actions deployer"

  depends_on = [google_project_service.required]
}

resource "google_secret_manager_secret" "runtime" {
  for_each = local.runtime_secret_ids

  project   = var.project_id
  secret_id = each.value

  replication {
    auto {}
  }

  depends_on = [google_project_service.required]
}

resource "google_project_iam_member" "runtime_secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = google_service_account.runtime.member
}

resource "google_project_iam_member" "github_artifact_registry_writer" {
  project = var.project_id
  role    = "roles/artifactregistry.writer"
  member  = google_service_account.github_deployer.member
}

resource "google_project_iam_member" "github_run_admin" {
  project = var.project_id
  role    = "roles/run.admin"
  member  = google_service_account.github_deployer.member
}

resource "google_service_account_iam_member" "github_can_act_as_runtime" {
  service_account_id = google_service_account.runtime.name
  role               = "roles/iam.serviceAccountUser"
  member             = google_service_account.github_deployer.member
}

resource "google_firestore_database" "mongo_compatible" {
  project     = var.project_id
  name        = var.firestore_database_id
  location_id = var.firestore_location_id

  type                                = "FIRESTORE_NATIVE"
  database_edition                    = "ENTERPRISE"
  mongodb_compatible_data_access_mode = "DATA_ACCESS_MODE_ENABLED"
  firestore_data_access_mode          = "DATA_ACCESS_MODE_DISABLED"
  realtime_updates_mode               = "REALTIME_UPDATES_MODE_DISABLED"
  point_in_time_recovery_enablement   = "POINT_IN_TIME_RECOVERY_ENABLED"
  delete_protection_state             = "DELETE_PROTECTION_ENABLED"
  deletion_policy                     = "ABANDON"

  depends_on = [google_project_service.required]
}

resource "google_iam_workload_identity_pool" "github" {
  project                   = var.project_id
  workload_identity_pool_id = "matrixedmind-dev-github"
  display_name              = "MatrixedMind dev GitHub"
  description               = "Allows the configured GitHub repository to deploy MatrixedMind dev."

  depends_on = [google_project_service.required]
}

resource "google_iam_workload_identity_pool_provider" "github" {
  project                            = var.project_id
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "github"
  display_name                       = "GitHub Actions"

  attribute_mapping = {
    "google.subject"             = "assertion.sub"
    "attribute.actor"            = "assertion.actor"
    "attribute.repository"       = "assertion.repository"
    "attribute.repository_owner" = "assertion.repository_owner"
    "attribute.ref"              = "assertion.ref"
  }

  attribute_condition = "assertion.repository == '${var.github_repository}'"

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

resource "google_service_account_iam_member" "github_workload_identity_user" {
  service_account_id = google_service_account.github_deployer.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/${var.github_repository}"
}

resource "google_cloud_run_v2_service" "app" {
  count = var.enable_cloud_run_service ? 1 : 0

  project             = var.project_id
  name                = var.cloud_run_service_name
  location            = var.region
  ingress             = "INGRESS_TRAFFIC_ALL"
  deletion_protection = true

  template {
    service_account = google_service_account.runtime.email

    containers {
      image = var.container_image

      ports {
        container_port = 8080
      }

      env {
        name  = "APP_ENV"
        value = "cloud-dev"
      }

      env {
        name = "MONGO_URI"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.runtime["matrixedmind-dev-mongo-uri"].secret_id
            version = "latest"
          }
        }
      }
    }
  }

  depends_on = [
    google_artifact_registry_repository.containers,
    google_firestore_database.mongo_compatible,
    google_project_iam_member.runtime_secret_accessor,
  ]
}

resource "google_cloud_run_v2_service_iam_member" "public_invoker" {
  count = var.enable_cloud_run_service && var.allow_unauthenticated_cloud_run ? 1 : 0

  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.app[0].name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_billing_budget" "dev" {
  count = var.billing_account_id != "" && var.billing_budget_amount_units != null ? 1 : 0

  billing_account = var.billing_account_id
  display_name    = "MatrixedMind dev"

  budget_filter {
    projects = ["projects/${data.google_project.current.number}"]
  }

  amount {
    specified_amount {
      currency_code = "USD"
      units         = tostring(var.billing_budget_amount_units)
    }
  }

  threshold_rules {
    threshold_percent = 0.5
  }

  threshold_rules {
    threshold_percent = 0.9
  }

  threshold_rules {
    threshold_percent = 1.0
  }

  depends_on = [google_project_service.required]
}
