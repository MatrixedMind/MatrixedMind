mock_provider "google" {}

variables {
  project_id                                 = "development-example"
  github_repository                          = "example/matrixedmind"
  enable_billing_budget                      = false
  billing_account_id                         = ""
  billing_budget_amount_units                = null
  operational_notification_email             = null
  external_operational_notification_channels = []
  external_budget_notification_channels      = []
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

run "observer_is_keyless_and_read_only" {
  command = plan

  variables {
    enable_observer_service_account = true
    observer_impersonator_member    = "user:observer@example.test"
  }

  assert {
    condition = (
      length(google_service_account.observer) == 1
      && length(google_project_iam_member.observer_read_only) == 3
      && google_service_account_iam_member.observer_impersonator[0].role == "roles/iam.serviceAccountTokenCreator"
    )
    error_message = "The enabled observer must have only the approved read-only project roles and a keyless impersonator binding."
  }
}

run "observer_requires_an_impersonator" {
  command = plan

  variables {
    enable_observer_service_account = true
  }

  expect_failures = [google_service_account.observer]
}

run "billing_budget_requires_notification_destination" {
  command = plan

  variables {
    enable_billing_budget = true
  }

  expect_failures = [var.enable_billing_budget]
}

run "billing_budget_rejects_zero_amount" {
  command = plan

  variables {
    billing_budget_amount_units = 0
  }

  expect_failures = [var.billing_budget_amount_units]
}

run "billing_budget_rejects_fractional_amount" {
  command = plan

  variables {
    billing_budget_amount_units = 50.5
  }

  expect_failures = [var.billing_budget_amount_units]
}

run "managed_notification_channel_wires_alerts_and_budget" {
  command = plan

  variables {
    enable_operational_alerting    = true
    enable_billing_budget          = true
    billing_account_id             = "000000-000000-000000"
    billing_budget_amount_units    = 50
    operational_notification_email = "operations@example.test"
  }

  assert {
    condition = (
      length(google_monitoring_notification_channel.operational) == 1
      && length(google_monitoring_alert_policy.cloud_run_error_rate) == 1
      && length(google_monitoring_alert_policy.cloud_run_latency) == 1
      && length(google_billing_budget.dev) == 1
    )
    error_message = "A managed operational email channel must be created and used when alerts and the budget are enabled."
  }

  assert {
    condition = (
      length(google_monitoring_alert_policy.cloud_run_error_rate[0].notification_channels) == 1
      && length(google_monitoring_alert_policy.cloud_run_latency[0].notification_channels) == 1
      && length(google_billing_budget.dev[0].all_updates_rule[0].monitoring_notification_channels) == 1
    )
    error_message = "Managed channel names must be wired directly into both alert policies and the billing budget."
  }
}

run "external_operational_channel_is_a_reuse_path" {
  command = plan

  variables {
    enable_operational_alerting                = true
    external_operational_notification_channels = ["projects/development-example/notificationChannels/123456789"]
  }

  assert {
    condition = (
      length(google_monitoring_notification_channel.operational) == 0
      && length(google_monitoring_alert_policy.cloud_run_error_rate[0].notification_channels) == 1
      && contains(google_monitoring_alert_policy.cloud_run_error_rate[0].notification_channels, "projects/development-example/notificationChannels/123456789")
    )
    error_message = "An external operational channel must be reusable without creating a managed channel."
  }
}

run "budget_rejects_more_than_five_channels" {
  command = plan

  variables {
    operational_notification_email = "operations@example.test"
    external_budget_notification_channels = [
      "projects/development-example/notificationChannels/1",
      "projects/development-example/notificationChannels/2",
      "projects/development-example/notificationChannels/3",
      "projects/development-example/notificationChannels/4",
      "projects/development-example/notificationChannels/5",
    ]
  }

  expect_failures = [var.external_budget_notification_channels]
}

run "disabled_billing_budget_rejects_legacy_inputs" {
  command = plan

  variables {
    billing_account_id          = "000000-000000-000000"
    billing_budget_amount_units = 50
  }

  expect_failures = [var.enable_billing_budget]
}
