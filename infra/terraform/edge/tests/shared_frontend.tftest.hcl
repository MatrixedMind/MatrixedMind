mock_provider "google" {}

variables {
  edge_project_id                        = "edge-example"
  existing_hostname                      = "existing.example.com"
  matrixedmind_hostname                  = "matrixedmind.example.com"
  static_ip_address                      = "203.0.113.10"
  existing_serverless_neg_self_link      = "https://www.googleapis.com/compute/v1/projects/edge-example/regions/us-central1/networkEndpointGroups/existing-site"
  existing_backend_service_self_link     = "https://www.googleapis.com/compute/v1/projects/edge-example/global/backendServices/existing-site"
  existing_backend_service_name          = "existing-site"
  existing_https_forwarding_rule_name    = "existing-site-https"
  existing_http_forwarding_rule_name     = "existing-site-http"
  matrixedmind_backend_service_self_link = "https://www.googleapis.com/compute/v1/projects/production-example/global/backendServices/matrixedmind-prod-backend"
}

run "non_disruptive_preparation" {
  command = plan

  assert {
    condition = (
      length(google_compute_backend_service.existing_site) == 0
      && length(google_compute_global_forwarding_rule.https) == 0
      && length(google_compute_global_forwarding_rule.http) == 0
    )
    error_message = "Preparation must not adopt or mutate the existing backend or forwarding rules."
  }

  assert {
    condition = anytrue([
      for rule in google_compute_url_map.shared.host_rule :
      contains(rule.hosts, "existing.example.com") && rule.path_matcher == "existing-site"
    ])
    error_message = "The shared URL map must preserve the existing hostname."
  }

  assert {
    condition = anytrue([
      for rule in google_compute_url_map.shared.host_rule :
      contains(rule.hosts, "matrixedmind.example.com") && rule.path_matcher == "matrixedmind"
    ])
    error_message = "The shared URL map must route the MatrixedMind hostname separately."
  }

  assert {
    condition = (
      google_certificate_manager_certificate.existing_site.managed[0].domains[0] == "existing.example.com"
      && google_certificate_manager_certificate.matrixedmind.managed[0].domains[0] == "matrixedmind.example.com"
      && google_certificate_manager_certificate_map_entry.existing_site.hostname == "existing.example.com"
      && google_certificate_manager_certificate_map_entry.matrixedmind.hostname == "matrixedmind.example.com"
    )
    error_message = "Preparation must provision DNS-authorized certificates and exact SNI mappings for both hostnames."
  }
}

run "migrated_frontend_adoption" {
  command = plan

  variables {
    manage_migrated_frontend      = true
    frontend_migration_confirmed  = true
    certificates_active_confirmed = true
  }

  assert {
    condition = (
      length(google_compute_backend_service.existing_site) == 1
      && google_compute_backend_service.existing_site[0].load_balancing_scheme == "EXTERNAL_MANAGED"
      && google_compute_backend_service.existing_site[0].connection_draining_timeout_sec == 0
      && alltrue([
        for backend in google_compute_backend_service.existing_site[0].backend :
        backend.balancing_mode == "UTILIZATION" && backend.capacity_scaler == 0
      ])
    )
    error_message = "Final adoption must preserve the migrated backend's live EXTERNAL_MANAGED settings."
  }

  assert {
    condition = (
      length(google_compute_global_forwarding_rule.https) == 1
      && google_compute_global_forwarding_rule.https[0].load_balancing_scheme == "EXTERNAL_MANAGED"
      && google_compute_global_forwarding_rule.https[0].ip_address == "203.0.113.10"
    )
    error_message = "HTTPS cutover must reuse the explicit static IP with EXTERNAL_MANAGED."
  }

  assert {
    condition = (
      length(google_compute_global_forwarding_rule.http) == 1
      && google_compute_global_forwarding_rule.http[0].load_balancing_scheme == "EXTERNAL_MANAGED"
      && google_compute_global_forwarding_rule.http[0].ip_address == "203.0.113.10"
    )
    error_message = "HTTP redirect cutover must reuse the explicit static IP with EXTERNAL_MANAGED."
  }
}

run "adoption_requires_confirmation" {
  command = plan

  variables {
    manage_migrated_frontend = true
  }

  expect_failures = [terraform_data.frontend_adoption_contract]
}
