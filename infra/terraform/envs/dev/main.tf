provider "google" {
  project               = var.project_id
  region                = var.region
  billing_project       = var.project_id
  user_project_override = true
}

data "google_project" "current" {
  project_id = var.project_id
}

locals {
  required_services = setunion(toset([
    "artifactregistry.googleapis.com",
    "cloudbuild.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "firestore.googleapis.com",
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
    "run.googleapis.com",
    "secretmanager.googleapis.com",
    "sts.googleapis.com",
  ]), var.enable_operational_alerting || var.enable_billing_budget ? toset(["monitoring.googleapis.com"]) : toset([]), var.enable_billing_budget ? toset(["billingbudgets.googleapis.com"]) : toset([]))

  runtime_secrets = {
    APP_SECRET_KEY = {
      secret_id = "matrixedmind-dev-app-secret-key"
      version   = var.app_secret_key_version
    }
    LLM_TOKEN_PEPPER = {
      secret_id = "matrixedmind-dev-llm-token-pepper"
      version   = var.llm_token_pepper_version
    }
  }

  firestore_oidc_uri = "mongodb://${google_firestore_database.mongo_compatible.uid}.${google_firestore_database.mongo_compatible.location_id}.firestore.goog:443/${google_firestore_database.mongo_compatible.name}?loadBalanced=true&tls=true&retryWrites=false&authMechanism=MONGODB-OIDC&authMechanismProperties=ENVIRONMENT:gcp,TOKEN_RESOURCE:FIRESTORE"
  # This service remains IAM-private. Its Cloud Run HTTPS URL is a stable canonical
  # origin for the schema setting required by the production runtime configuration.
  cloud_run_service_url = "https://${var.cloud_run_service_name}-${data.google_project.current.number}.${var.region}.run.app"

  operational_notification_channels = setunion(
    toset(google_monitoring_notification_channel.operational[*].name),
    var.external_operational_notification_channels,
  )
  budget_notification_channels = setunion(
    toset(google_monitoring_notification_channel.operational[*].name),
    var.external_budget_notification_channels,
  )
}

resource "google_project_service" "required" {
  for_each = local.required_services

  project = var.project_id
  service = each.value

  disable_on_destroy = false
}

module "artifact_registry" {
  source = "../../modules/artifact_registry"

  project_id    = var.project_id
  location      = var.region
  repository_id = var.artifact_registry_repository_id

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

resource "google_service_account" "firestore_spike" {
  project      = var.project_id
  account_id   = var.firestore_spike_service_account_id
  display_name = "MatrixedMind Firestore compatibility runner"

  depends_on = [google_project_service.required]
}

module "runtime_secrets" {
  source = "../../modules/runtime_secrets"

  project_id      = var.project_id
  accessor_member = google_service_account.runtime.member
  secrets         = local.runtime_secrets

  depends_on = [google_project_service.required]
}

resource "google_project_iam_member" "runtime_firestore_user" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = google_service_account.runtime.member
}

resource "google_project_iam_member" "firestore_spike_user" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = google_service_account.firestore_spike.member
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

# The pinned deploy workflow mints an ID token as this deployer account for its
# authenticated Cloud Run health and readiness checks. Preserve this binding
# until that workflow's token-minting path is separately verified and changed.
resource "google_service_account_iam_member" "github_can_mint_identity_token" {
  service_account_id = google_service_account.github_deployer.name
  role               = "roles/iam.serviceAccountTokenCreator"
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
  point_in_time_recovery_enablement   = "POINT_IN_TIME_RECOVERY_ENABLED"
  delete_protection_state             = "DELETE_PROTECTION_ENABLED"
  deletion_policy                     = "ABANDON"

  depends_on = [google_project_service.required]
}

resource "google_firestore_index" "records_space_slug_unique" {
  project     = var.project_id
  database    = google_firestore_database.mongo_compatible.name
  collection  = "records"
  api_scope   = "MONGODB_COMPATIBLE_API"
  query_scope = "COLLECTION_GROUP"
  density     = "DENSE"
  unique      = true

  fields {
    field_path = "space"
    order      = "ASCENDING"
  }

  fields {
    field_path = "slug"
    order      = "ASCENDING"
  }
}

resource "google_firestore_index" "records_space_parent" {
  project     = var.project_id
  database    = google_firestore_database.mongo_compatible.name
  collection  = "records"
  api_scope   = "MONGODB_COMPATIBLE_API"
  query_scope = "COLLECTION_GROUP"
  density     = "DENSE"

  fields {
    field_path = "space"
    order      = "ASCENDING"
  }

  fields {
    field_path = "parent_id"
    order      = "ASCENDING"
  }
}

resource "google_firestore_index" "llm_token_hash_unique" {
  project     = var.project_id
  database    = google_firestore_database.mongo_compatible.name
  collection  = "llm_api_tokens"
  api_scope   = "MONGODB_COMPATIBLE_API"
  query_scope = "COLLECTION_GROUP"
  density     = "DENSE"
  unique      = true

  fields {
    field_path = "token_hash"
    order      = "ASCENDING"
  }
}

resource "google_firestore_index" "audit_timestamp" {
  project     = var.project_id
  database    = google_firestore_database.mongo_compatible.name
  collection  = "audit_events"
  api_scope   = "MONGODB_COMPATIBLE_API"
  query_scope = "COLLECTION_GROUP"
  density     = "DENSE"

  fields {
    field_path = "timestamp"
    order      = "ASCENDING"
  }
}

resource "google_firestore_index" "audit_target" {
  project     = var.project_id
  database    = google_firestore_database.mongo_compatible.name
  collection  = "audit_events"
  api_scope   = "MONGODB_COMPATIBLE_API"
  query_scope = "COLLECTION_GROUP"
  density     = "DENSE"

  fields {
    field_path = "target_type"
    order      = "ASCENDING"
  }

  fields {
    field_path = "target_id"
    order      = "ASCENDING"
  }
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

module "cloud_run_service" {
  count = var.enable_cloud_run_service ? 1 : 0

  source = "../../modules/cloud_run_service"

  project_id            = var.project_id
  name                  = var.cloud_run_service_name
  location              = var.region
  container_image       = var.container_image
  service_account_email = google_service_account.runtime.email
  invocation_mode       = "private"
  invoker_members = [
    "serviceAccount:${var.github_deployer_service_account_id}@${var.project_id}.iam.gserviceaccount.com",
  ]
  environment_variables = {
    APP_ENV                         = "production"
    AUTH_MODE                       = "production"
    LLM_API_SERVER_URL              = local.cloud_run_service_url
    MARKDOWN_IMAGE_SOURCE_ALLOWLIST = var.markdown_image_source_allowlist
    MONGO_URI                       = local.firestore_oidc_uri
    MONGO_ENSURE_INDEXES            = "false"
    SOURCE_REPOSITORY_URL           = var.source_repository_url
  }
  secret_environment_variables = module.runtime_secrets.secret_env

  depends_on = [
    module.artifact_registry,
    google_firestore_index.audit_target,
    google_firestore_index.audit_timestamp,
    google_firestore_index.llm_token_hash_unique,
    google_firestore_index.records_space_parent,
    google_firestore_index.records_space_slug_unique,
    module.runtime_secrets,
    google_project_iam_member.runtime_firestore_user,
  ]
}

resource "google_cloud_run_v2_job" "firestore_spike" {
  count = var.enable_firestore_spike_job ? 1 : 0

  project  = var.project_id
  name     = var.firestore_spike_job_name
  location = var.region

  template {
    template {
      service_account = google_service_account.firestore_spike.email
      max_retries     = 0
      timeout         = "900s"

      containers {
        image   = var.firestore_spike_image
        command = ["uv"]
        args    = ["run", "pytest", "tests/firestore", "-rs"]

        env {
          name  = "FIRESTORE_MONGO_URI"
          value = local.firestore_oidc_uri
        }
      }
    }
  }

  lifecycle {
    precondition {
      condition     = var.firestore_spike_image != ""
      error_message = "firestore_spike_image must be set when enable_firestore_spike_job is true."
    }
  }

  depends_on = [
    module.artifact_registry,
    google_firestore_index.records_space_slug_unique,
    google_firestore_index.records_space_parent,
    google_project_iam_member.firestore_spike_user,
  ]
}

resource "google_monitoring_notification_channel" "operational" {
  count = (var.enable_operational_alerting || var.enable_billing_budget) && nonsensitive(var.operational_notification_email != null) ? 1 : 0

  project      = var.project_id
  display_name = "MatrixedMind development operations"
  type         = "email"
  labels = {
    email_address = var.operational_notification_email
  }

  # Do not force-delete a channel that may still be used outside this root.
  force_delete = false

  depends_on = [google_project_service.required]
}

resource "google_billing_budget" "dev" {
  count = var.enable_billing_budget ? 1 : 0

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

  all_updates_rule {
    disable_default_iam_recipients   = true
    monitoring_notification_channels = local.budget_notification_channels
  }

  depends_on = [google_project_service.required]
}

resource "google_monitoring_alert_policy" "cloud_run_error_rate" {
  count = var.enable_operational_alerting ? 1 : 0

  project               = var.project_id
  display_name          = "MatrixedMind dev Cloud Run 5xx error rate"
  combiner              = "OR"
  notification_channels = local.operational_notification_channels

  conditions {
    display_name = "Cloud Run 5xx requests exceed the configured rate"

    condition_threshold {
      filter          = "metric.type=\"run.googleapis.com/request_count\" AND resource.type=\"cloud_run_revision\" AND resource.label.\"service_name\"=\"${var.cloud_run_service_name}\" AND metric.label.\"response_code_class\"=\"5xx\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = var.cloud_run_error_rate_threshold

      aggregations {
        alignment_period     = "60s"
        per_series_aligner   = "ALIGN_RATE"
        cross_series_reducer = "REDUCE_SUM"
      }
    }
  }

  depends_on = [google_project_service.required]
}

resource "google_monitoring_alert_policy" "cloud_run_latency" {
  count = var.enable_operational_alerting ? 1 : 0

  project               = var.project_id
  display_name          = "MatrixedMind dev Cloud Run p99 request latency"
  combiner              = "OR"
  notification_channels = local.operational_notification_channels

  conditions {
    display_name = "Cloud Run p99 request latency exceeds the configured threshold"

    condition_threshold {
      filter          = "metric.type=\"run.googleapis.com/request_latencies\" AND resource.type=\"cloud_run_revision\" AND resource.label.\"service_name\"=\"${var.cloud_run_service_name}\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = var.cloud_run_latency_threshold_milliseconds

      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_PERCENTILE_99"
      }
    }
  }

  depends_on = [google_project_service.required]
}
