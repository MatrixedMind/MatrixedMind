mock_provider "google" {}

variables {
  project_id        = "production-example"
  github_repository = "example/matrixedmind"
}

run "private_foundation" {
  command = plan

  assert {
    condition     = var.cloud_run_invocation_mode == "private"
    error_message = "The production foundation must stage with private Cloud Run invocation."
  }

  assert {
    condition     = length(module.cloud_run_service) == 0
    error_message = "The production foundation must not create Cloud Run before it is explicitly enabled."
  }

  assert {
    condition = (
      length(google_monitoring_alert_policy.cloud_run_error_rate) == 0
      && length(google_monitoring_alert_policy.cloud_run_latency) == 0
      && length(google_billing_budget.prod) == 0
    )
    error_message = "Operational alerting and budgets must remain disabled until their explicit inputs are supplied."
  }
}

run "operational_alerting_requires_notification_channels" {
  command = plan

  variables {
    enable_operational_alerting = true
  }

  expect_failures = [var.enable_operational_alerting]
}

run "managed_notification_channel_wires_alerts_and_budget" {
  command = plan

  variables {
    enable_operational_alerting    = true
    enable_billing_budget          = true
    billing_account_id             = "000000-000000-000000"
    billing_budget_amount_units    = 100
    operational_notification_email = "operations@example.test"
  }

  assert {
    condition = (
      length(google_monitoring_notification_channel.operational) == 1
      && length(google_monitoring_alert_policy.cloud_run_error_rate) == 1
      && length(google_monitoring_alert_policy.cloud_run_latency) == 1
      && length(google_billing_budget.prod) == 1
    )
    error_message = "A managed operational email channel must be created and used when alerts and the budget are enabled."
  }

  assert {
    condition = (
      length(google_monitoring_alert_policy.cloud_run_error_rate[0].notification_channels) == 1
      && length(google_monitoring_alert_policy.cloud_run_latency[0].notification_channels) == 1
      && length(google_billing_budget.prod[0].all_updates_rule[0].monitoring_notification_channels) == 1
    )
    error_message = "Managed channel names must be wired directly into both alert policies and the billing budget."
  }
}

run "external_operational_channel_is_a_reuse_path" {
  command = plan

  variables {
    enable_operational_alerting                = true
    external_operational_notification_channels = ["projects/production-example/notificationChannels/123456789"]
  }

  assert {
    condition = (
      length(google_monitoring_notification_channel.operational) == 0
      && length(google_monitoring_alert_policy.cloud_run_error_rate[0].notification_channels) == 1
      && contains(google_monitoring_alert_policy.cloud_run_error_rate[0].notification_channels, "projects/production-example/notificationChannels/123456789")
    )
    error_message = "An external operational channel must be reusable without creating a managed channel."
  }
}

run "budget_rejects_more_than_five_channels" {
  command = plan

  variables {
    operational_notification_email = "operations@example.test"
    external_budget_notification_channels = [
      "projects/production-example/notificationChannels/1",
      "projects/production-example/notificationChannels/2",
      "projects/production-example/notificationChannels/3",
      "projects/production-example/notificationChannels/4",
      "projects/production-example/notificationChannels/5",
    ]
  }

  expect_failures = [var.external_budget_notification_channels]
}

run "disabled_billing_budget_rejects_legacy_inputs" {
  command = plan

  variables {
    billing_account_id          = "000000-000000-000000"
    billing_budget_amount_units = 100
  }

  expect_failures = [var.enable_billing_budget]
}

run "cross_project_backend" {
  command = plan

  variables {
    enable_cloud_run_service           = true
    container_image                    = "us-west1-docker.pkg.dev/production-example/matrixedmind/matrixedmind:test"
    cloud_run_invocation_mode          = "external_load_balancer"
    load_balancer_backend_service_name = "matrixedmind-prod-backend"
    edge_load_balancer_service_user_members = [
      "serviceAccount:edge-admin@edge-example.iam.gserviceaccount.com",
    ]
  }

  assert {
    condition     = length(module.cloud_run_service) == 1
    error_message = "The enabled production root must create exactly one Cloud Run service module."
  }

  assert {
    condition = (
      var.cloud_run_invocation_mode == "external_load_balancer"
      && length(var.edge_load_balancer_service_user_members) == 1
    )
    error_message = "The production cross-project mode must include an explicit edge service-user member."
  }
}

run "external_mode_requires_edge_member" {
  command = plan

  variables {
    enable_cloud_run_service  = true
    container_image           = "us-west1-docker.pkg.dev/production-example/matrixedmind/matrixedmind:test"
    cloud_run_invocation_mode = "external_load_balancer"
  }

  expect_failures = [terraform_data.invocation_contract]
}

run "direct_mode_is_not_an_official_production_mode" {
  command = plan

  variables {
    cloud_run_invocation_mode = "direct"
  }

  expect_failures = [var.cloud_run_invocation_mode]
}
