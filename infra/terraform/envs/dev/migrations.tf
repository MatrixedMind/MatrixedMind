moved {
  from = google_artifact_registry_repository.containers
  to   = module.artifact_registry.google_artifact_registry_repository.this
}

moved {
  from = google_secret_manager_secret.runtime["matrixedmind-dev-app-secret-key"]
  to   = module.runtime_secrets.google_secret_manager_secret.this["APP_SECRET_KEY"]
}

moved {
  from = google_secret_manager_secret_iam_member.runtime_secret_accessor["matrixedmind-dev-app-secret-key"]
  to   = module.runtime_secrets.google_secret_manager_secret_iam_member.accessor["APP_SECRET_KEY"]
}

moved {
  from = google_cloud_run_v2_service.app[0]
  to   = module.cloud_run_service[0].google_cloud_run_v2_service.this
}

moved {
  from = google_cloud_run_v2_service_iam_member.public_invoker[0]
  to   = module.cloud_run_service[0].google_cloud_run_v2_service_iam_member.public_invoker[0]
}
