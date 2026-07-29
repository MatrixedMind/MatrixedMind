locals {
  ingress_by_invocation_mode = {
    private                = "INGRESS_TRAFFIC_ALL"
    direct                 = "INGRESS_TRAFFIC_ALL"
    external_load_balancer = "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER"
  }
  public_invocation = var.invocation_mode != "private"
  backend_service_name = coalesce(
    var.load_balancer_backend_service_name,
    "${var.name}-backend",
  )
  action_allowlist_expression = (
    var.openai_action_address_group_name == null
    ? null
    : format(
      "request.path.startsWith('/api/llm/') && evaluateAddressGroup('%s', origin.ip)",
      var.openai_action_address_group_name,
    )
  )
}

resource "google_cloud_run_v2_service" "this" {
  project             = var.project_id
  name                = var.name
  location            = var.location
  ingress             = local.ingress_by_invocation_mode[var.invocation_mode]
  deletion_protection = var.deletion_protection

  template {
    service_account = var.service_account_email

    scaling {
      min_instance_count = var.min_instance_count
      max_instance_count = var.max_instance_count
    }

    containers {
      image = var.container_image

      ports {
        container_port = 8080
      }

      startup_probe {
        initial_delay_seconds = 0
        timeout_seconds       = 5
        period_seconds        = 5
        failure_threshold     = 12

        http_get {
          path = "/health"
          port = 8080
        }
      }

      liveness_probe {
        initial_delay_seconds = 5
        timeout_seconds       = 5
        period_seconds        = 30
        failure_threshold     = 3

        http_get {
          path = "/health"
          port = 8080
        }
      }

      dynamic "env" {
        for_each = var.environment_variables

        content {
          name  = env.key
          value = env.value
        }
      }

      dynamic "env" {
        for_each = var.secret_environment_variables

        content {
          name = env.key

          value_source {
            secret_key_ref {
              secret  = env.value.secret_id
              version = env.value.version
            }
          }
        }
      }
    }
  }

  lifecycle {
    # Terraform owns service configuration; the deploy workflow owns immutable image revisions.
    ignore_changes = [template[0].containers[0].image]
  }
}

resource "google_cloud_run_v2_service_iam_member" "public_invoker" {
  count = local.public_invocation ? 1 : 0

  project  = var.project_id
  location = var.location
  name     = google_cloud_run_v2_service.this.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_compute_region_network_endpoint_group" "load_balancer" {
  count = var.invocation_mode == "external_load_balancer" ? 1 : 0

  project               = var.project_id
  name                  = "${var.name}-serverless-neg"
  region                = var.location
  network_endpoint_type = "SERVERLESS"

  cloud_run {
    service = google_cloud_run_v2_service.this.name
  }
}

resource "google_compute_security_policy" "action_allowlist" {
  count = (
    var.invocation_mode == "external_load_balancer"
    && var.openai_action_address_group_name != null
  ) ? 1 : 0

  project     = var.project_id
  name        = "${var.name}-action-allowlist"
  description = "Optional defense-in-depth source policy for MatrixedMind LLM API requests."

  rule {
    action      = "allow"
    priority    = 1000
    description = "Allow configured ChatGPT integration source ranges to the LLM API."

    match {
      expr {
        expression = local.action_allowlist_expression
      }
    }
  }

  rule {
    action      = "deny(403)"
    priority    = 1100
    description = "Reject other sources from the LLM API; bearer-token auth still applies."

    match {
      expr {
        expression = "request.path.startsWith('/api/llm/')"
      }
    }
  }

  rule {
    action      = "allow"
    priority    = 2147483647
    description = "Allow non-LLM paths to continue through application-level controls."

    match {
      versioned_expr = "SRC_IPS_V1"

      config {
        src_ip_ranges = ["*"]
      }
    }
  }
}

resource "google_compute_backend_service" "load_balancer" {
  count = var.invocation_mode == "external_load_balancer" ? 1 : 0

  project               = var.project_id
  name                  = local.backend_service_name
  protocol              = "HTTP"
  load_balancing_scheme = var.external_load_balancer_scheme
  security_policy = (
    var.openai_action_address_group_name != null
    ? google_compute_security_policy.action_allowlist[0].id
    : null
  )

  backend {
    group = google_compute_region_network_endpoint_group.load_balancer[0].id
  }
}

resource "google_project_iam_member" "load_balancer_service_user" {
  for_each = var.invocation_mode == "external_load_balancer" ? var.load_balancer_service_user_members : toset([])

  project = var.project_id
  role    = "roles/compute.loadBalancerServiceUser"
  member  = each.value
}

resource "google_cloud_run_v2_service_iam_member" "invoker" {
  for_each = var.invoker_members

  project  = var.project_id
  location = var.location
  name     = google_cloud_run_v2_service.this.name
  role     = "roles/run.invoker"
  member   = each.value
}
