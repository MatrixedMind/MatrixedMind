mock_provider "google" {}

variables {
  project_id            = "example-project"
  name                  = "matrixedmind-example"
  location              = "us-west1"
  container_image       = "us-west1-docker.pkg.dev/example-project/example/matrixedmind:test"
  service_account_email = "runtime@example-project.iam.gserviceaccount.com"
  environment_variables = {
    APP_ENV = "production"
  }
  secret_environment_variables = {
    APP_SECRET_KEY = {
      secret_id = "app-secret-key"
      version   = "1"
    }
  }
}

run "private_staging_mode" {
  command = plan

  variables {
    invocation_mode = "private"
  }

  assert {
    condition     = google_cloud_run_v2_service.this.ingress == "INGRESS_TRAFFIC_ALL"
    error_message = "Private staging must retain normal ingress while IAM blocks public callers."
  }

  assert {
    condition     = length(google_cloud_run_v2_service_iam_member.public_invoker) == 0
    error_message = "Private staging must not grant allUsers the Cloud Run invoker role."
  }

  assert {
    condition     = length(google_compute_region_network_endpoint_group.load_balancer) == 0
    error_message = "Private staging must not create a serverless load-balancer NEG."
  }

  assert {
    condition     = length(google_compute_backend_service.load_balancer) == 0
    error_message = "Private staging must not create a load-balancer backend service."
  }

  assert {
    condition     = length(google_project_iam_member.load_balancer_service_user) == 0
    error_message = "Private staging must not grant cross-project backend-service access."
  }
}

run "direct_public_mode" {
  command = plan

  variables {
    invocation_mode = "direct"
  }

  assert {
    condition     = google_cloud_run_v2_service.this.ingress == "INGRESS_TRAFFIC_ALL"
    error_message = "Direct mode must accept requests through the direct Cloud Run URL."
  }

  assert {
    condition     = length(google_cloud_run_v2_service_iam_member.public_invoker) == 1
    error_message = "Direct mode must grant public platform invocation."
  }

  assert {
    condition     = length(google_compute_region_network_endpoint_group.load_balancer) == 0
    error_message = "Direct mode must not create load-balancer integration resources."
  }

  assert {
    condition     = length(google_compute_backend_service.load_balancer) == 0
    error_message = "Direct mode must not create a load-balancer backend service."
  }

  assert {
    condition     = length(google_project_iam_member.load_balancer_service_user) == 0
    error_message = "Direct mode must not grant cross-project backend-service access."
  }
}

run "external_load_balancer_mode" {
  command = plan

  variables {
    invocation_mode = "external_load_balancer"
    load_balancer_service_user_members = [
      "serviceAccount:edge-admin@edge-example.iam.gserviceaccount.com",
    ]
  }

  assert {
    condition = (
      google_cloud_run_v2_service.this.ingress
      == "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER"
    )
    error_message = "Load-balancer mode must reject direct public Cloud Run ingress."
  }

  assert {
    condition     = length(google_cloud_run_v2_service_iam_member.public_invoker) == 1
    error_message = "The external load balancer still needs unauthenticated platform invocation."
  }

  assert {
    condition     = length(google_compute_region_network_endpoint_group.load_balancer) == 1
    error_message = "Load-balancer mode must create the serverless NEG beside Cloud Run."
  }

  assert {
    condition     = length(google_compute_backend_service.load_balancer) == 1
    error_message = "Load-balancer mode must create its backend for the shared URL map."
  }

  assert {
    condition = (
      google_compute_backend_service.load_balancer[0].project == "example-project"
      && google_compute_region_network_endpoint_group.load_balancer[0].project == "example-project"
    )
    error_message = "Cloud Run's backend service and serverless NEG must stay together in the application project."
  }

  assert {
    condition     = google_compute_backend_service.load_balancer[0].load_balancing_scheme == "EXTERNAL_MANAGED"
    error_message = "Cross-project service referencing requires the global external managed backend scheme."
  }

  assert {
    condition     = length(google_compute_security_policy.action_allowlist) == 0
    error_message = "A null address-group reference must leave the optional Cloud Armor policy disabled."
  }

  assert {
    condition     = length(google_project_iam_member.load_balancer_service_user) == 1
    error_message = "The application project must grant its configured edge administrator permission to reference the backend."
  }

  assert {
    condition = (
      google_project_iam_member.load_balancer_service_user[
        "serviceAccount:edge-admin@edge-example.iam.gserviceaccount.com"
      ].role == "roles/compute.loadBalancerServiceUser"
    )
    error_message = "Cross-project attachment must use the dedicated load-balancer service-user role."
  }
}

run "external_load_balancer_mode_with_action_allowlist" {
  command = plan

  variables {
    invocation_mode                  = "external_load_balancer"
    openai_action_address_group_name = "chatgpt-integration-egress"
  }

  assert {
    condition     = length(google_compute_security_policy.action_allowlist) == 1
    error_message = "A reviewed address group must enable the optional Cloud Armor policy."
  }

  assert {
    condition = anytrue([
      for rule in google_compute_security_policy.action_allowlist[0].rule :
      rule.action == "deny(403)" && rule.priority == 1100
    ])
    error_message = "The policy must deny other sources from /api/llm/* after the allow rule."
  }
}

run "invalid_mode" {
  command = plan

  variables {
    invocation_mode = "direct_and_load_balancer"
  }

  expect_failures = [var.invocation_mode]
}

run "invalid_action_address_group_name" {
  command = plan

  variables {
    invocation_mode                  = "external_load_balancer"
    openai_action_address_group_name = "Invalid/Name"
  }

  expect_failures = [var.openai_action_address_group_name]
}

run "invalid_load_balancer_service_user_member" {
  command = plan

  variables {
    invocation_mode = "external_load_balancer"
    load_balancer_service_user_members = [
      "allUsers",
    ]
  }

  expect_failures = [var.load_balancer_service_user_members]
}
