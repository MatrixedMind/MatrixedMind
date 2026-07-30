provider "google" {
  project                     = var.edge_project_id
  region                      = var.region
  impersonate_service_account = var.impersonate_service_account
}

resource "terraform_data" "frontend_adoption_contract" {
  input = var.manage_migrated_frontend

  lifecycle {
    precondition {
      condition = (
        !var.manage_migrated_frontend
        || (var.frontend_migration_confirmed && var.certificates_active_confirmed)
      )
      error_message = "Frontend adoption requires explicit confirmation that both certificates are ACTIVE and the existing backend and forwarding rules completed Google's in-place EXTERNAL_MANAGED migration."
    }
  }
}

resource "google_compute_backend_service" "existing_site" {
  count = var.manage_migrated_frontend ? 1 : 0

  project                         = var.edge_project_id
  name                            = var.existing_backend_service_name
  protocol                        = "HTTP"
  load_balancing_scheme           = "EXTERNAL_MANAGED"
  connection_draining_timeout_sec = 0

  backend {
    group           = var.existing_serverless_neg_self_link
    balancing_mode  = "UTILIZATION"
    capacity_scaler = 0
  }
}

resource "google_certificate_manager_dns_authorization" "existing_site" {
  project = var.edge_project_id
  name    = "${var.resource_name_prefix}-existing-dns-auth"
  domain  = var.existing_hostname
  type    = "FIXED_RECORD"
}

resource "google_certificate_manager_dns_authorization" "matrixedmind" {
  project = var.edge_project_id
  name    = "${var.resource_name_prefix}-matrixedmind-dns-auth"
  domain  = var.matrixedmind_hostname
  type    = "FIXED_RECORD"
}

resource "google_certificate_manager_certificate" "existing_site" {
  project = var.edge_project_id
  name    = "${var.resource_name_prefix}-existing-certificate"

  managed {
    domains            = [var.existing_hostname]
    dns_authorizations = [google_certificate_manager_dns_authorization.existing_site.id]
  }
}

resource "google_certificate_manager_certificate" "matrixedmind" {
  project = var.edge_project_id
  name    = "${var.resource_name_prefix}-matrixedmind-certificate"

  managed {
    domains            = [var.matrixedmind_hostname]
    dns_authorizations = [google_certificate_manager_dns_authorization.matrixedmind.id]
  }
}

resource "google_certificate_manager_certificate_map" "shared" {
  project = var.edge_project_id
  name    = "${var.resource_name_prefix}-certificate-map"
}

resource "google_certificate_manager_certificate_map_entry" "existing_site" {
  project      = var.edge_project_id
  name         = "${var.resource_name_prefix}-existing-entry"
  map          = google_certificate_manager_certificate_map.shared.name
  certificates = [google_certificate_manager_certificate.existing_site.id]
  hostname     = var.existing_hostname
}

resource "google_certificate_manager_certificate_map_entry" "matrixedmind" {
  project      = var.edge_project_id
  name         = "${var.resource_name_prefix}-matrixedmind-entry"
  map          = google_certificate_manager_certificate_map.shared.name
  certificates = [google_certificate_manager_certificate.matrixedmind.id]
  hostname     = var.matrixedmind_hostname
}

locals {
  existing_backend_service_self_link = var.manage_migrated_frontend ? google_compute_backend_service.existing_site[0].self_link : var.existing_backend_service_self_link
}

resource "google_compute_url_map" "shared" {
  project         = var.edge_project_id
  name            = "${var.resource_name_prefix}-url-map"
  default_service = local.existing_backend_service_self_link

  host_rule {
    hosts        = [var.existing_hostname]
    path_matcher = "existing-site"
  }

  path_matcher {
    name            = "existing-site"
    default_service = local.existing_backend_service_self_link
  }

  host_rule {
    hosts        = [var.matrixedmind_hostname]
    path_matcher = "matrixedmind"
  }

  path_matcher {
    name            = "matrixedmind"
    default_service = var.matrixedmind_backend_service_self_link
  }
}

resource "google_compute_target_https_proxy" "shared" {
  project         = var.edge_project_id
  name            = "${var.resource_name_prefix}-https-proxy"
  url_map         = google_compute_url_map.shared.self_link
  certificate_map = "//certificatemanager.googleapis.com/${google_certificate_manager_certificate_map.shared.id}"

  depends_on = [
    google_certificate_manager_certificate_map_entry.existing_site,
    google_certificate_manager_certificate_map_entry.matrixedmind,
  ]
}

resource "google_compute_url_map" "https_redirect" {
  project = var.edge_project_id
  name    = "${var.resource_name_prefix}-redirect-url-map"

  default_url_redirect {
    https_redirect         = true
    redirect_response_code = "MOVED_PERMANENTLY_DEFAULT"
    strip_query            = false
  }
}

resource "google_compute_target_http_proxy" "https_redirect" {
  project = var.edge_project_id
  name    = "${var.resource_name_prefix}-http-proxy"
  url_map = google_compute_url_map.https_redirect.self_link
}

resource "google_compute_global_forwarding_rule" "https" {
  count = var.manage_migrated_frontend ? 1 : 0

  project               = var.edge_project_id
  name                  = var.existing_https_forwarding_rule_name
  ip_address            = var.static_ip_address
  port_range            = "443"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  target                = google_compute_target_https_proxy.shared.self_link

  depends_on = [terraform_data.frontend_adoption_contract]
}

resource "google_compute_global_forwarding_rule" "http" {
  count = var.manage_migrated_frontend ? 1 : 0

  project               = var.edge_project_id
  name                  = var.existing_http_forwarding_rule_name
  ip_address            = var.static_ip_address
  port_range            = "80"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  target                = google_compute_target_http_proxy.https_redirect.self_link

  depends_on = [terraform_data.frontend_adoption_contract]
}
