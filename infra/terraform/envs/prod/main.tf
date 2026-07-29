provider "google" {
  project               = var.project_id
  region                = var.region
  billing_project       = var.project_id
  user_project_override = true
}

locals {
  required_services = toset([
    "artifactregistry.googleapis.com",
    "cloudbuild.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "compute.googleapis.com",
    "firestore.googleapis.com",
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
    "run.googleapis.com",
    "secretmanager.googleapis.com",
    "sts.googleapis.com",
  ])

  runtime_secrets = {
    APP_SECRET_KEY = {
      secret_id = "matrixedmind-prod-app-secret-key"
      version   = var.app_secret_key_version
    }
    LLM_TOKEN_PEPPER = {
      secret_id = "matrixedmind-prod-llm-token-pepper"
      version   = var.llm_token_pepper_version
    }
  }

  firestore_oidc_uri = "mongodb://${google_firestore_database.mongo_compatible.uid}.${google_firestore_database.mongo_compatible.location_id}.firestore.goog:443/${google_firestore_database.mongo_compatible.name}?loadBalanced=true&tls=true&retryWrites=false&authMechanism=MONGODB-OIDC&authMechanismProperties=ENVIRONMENT:gcp,TOKEN_RESOURCE:FIRESTORE"
}

resource "terraform_data" "invocation_contract" {
  input = var.cloud_run_invocation_mode

  lifecycle {
    precondition {
      condition = (
        !var.enable_cloud_run_service
        || var.cloud_run_invocation_mode != "external_load_balancer"
        || length(var.edge_load_balancer_service_user_members) > 0
      )
      error_message = "External-load-balancer mode requires at least one explicit edge load-balancer service-user member."
    }
  }
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
  display_name = "MatrixedMind production runtime"

  depends_on = [google_project_service.required]
}

resource "google_service_account" "github_deployer" {
  project      = var.project_id
  account_id   = var.github_deployer_service_account_id
  display_name = "MatrixedMind production GitHub Actions deployer"

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
  workload_identity_pool_id = "matrixedmind-prod-github"
  display_name              = "MatrixedMind production GitHub"
  description               = "Allows the configured GitHub repository to deploy MatrixedMind production."

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

  project_id                         = var.project_id
  name                               = var.cloud_run_service_name
  location                           = var.region
  container_image                    = var.container_image
  service_account_email              = google_service_account.runtime.email
  invocation_mode                    = var.cloud_run_invocation_mode
  external_load_balancer_scheme      = "EXTERNAL_MANAGED"
  load_balancer_backend_service_name = var.load_balancer_backend_service_name
  load_balancer_service_user_members = var.edge_load_balancer_service_user_members
  openai_action_address_group_name   = var.openai_action_address_group_name
  invoker_members = [
    "serviceAccount:${var.github_deployer_service_account_id}@${var.project_id}.iam.gserviceaccount.com",
  ]
  environment_variables = {
    APP_ENV                         = "production"
    AUTH_MODE                       = "production"
    MARKDOWN_IMAGE_SOURCE_ALLOWLIST = var.markdown_image_source_allowlist
    MONGO_URI                       = local.firestore_oidc_uri
    MONGO_ENSURE_INDEXES            = "false"
    SOURCE_REPOSITORY_URL           = var.source_repository_url
  }
  secret_environment_variables = module.runtime_secrets.secret_env

  depends_on = [
    terraform_data.invocation_contract,
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
