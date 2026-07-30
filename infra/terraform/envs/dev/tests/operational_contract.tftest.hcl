mock_provider "google" {}

variables {
  project_id                                      = "development-example"
  github_repository                               = "example/matrixedmind"
  enable_billing_budget                           = false
  billing_account_id                              = ""
  billing_budget_amount_units                     = null
  billing_budget_monitoring_notification_channels = []
}

run "operational_defaults_are_disabled" {
  command = plan

  assert {
    condition = (
      length(google_monitoring_alert_policy.cloud_run_error_rate) == 0
      && length(google_monitoring_alert_policy.cloud_run_latency) == 0
      && length(google_billing_budget.dev) == 0
    )
    error_message = "Development operational alerting and billing must remain disabled by default."
  }
}

run "billing_budget_requires_reviewed_notification_channels" {
  command = plan

  variables {
    enable_billing_budget = true
  }

  expect_failures = [var.enable_billing_budget]
}

run "disabled_billing_budget_rejects_legacy_inputs" {
  command = plan

  variables {
    billing_account_id          = "000000-000000-000000"
    billing_budget_amount_units = 50
  }

  expect_failures = [var.enable_billing_budget]
}
