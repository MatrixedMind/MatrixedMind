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
