output "dns_authorization_records" {
  description = "CNAME records the domain owners must add before the DNS-authorized certificates can become ACTIVE."
  value = {
    existing_site = google_certificate_manager_dns_authorization.existing_site.dns_resource_record[0]
    matrixedmind  = google_certificate_manager_dns_authorization.matrixedmind.dns_resource_record[0]
  }
}

output "certificate_names" {
  description = "DNS-authorized Certificate Manager certificates that must both become ACTIVE before frontend migration."
  value = {
    existing_site = google_certificate_manager_certificate.existing_site.name
    matrixedmind  = google_certificate_manager_certificate.matrixedmind.name
  }
}

output "shared_url_map_self_link" {
  description = "Prepared shared URL map containing the existing-site and MatrixedMind host routes."
  value       = google_compute_url_map.shared.self_link
}

output "shared_https_proxy_self_link" {
  description = "Prepared HTTPS proxy containing both hostname certificates."
  value       = google_compute_target_https_proxy.shared.self_link
}

output "migrated_frontend_managed" {
  description = "Whether the already-migrated existing backend and forwarding rules are managed by this root."
  value       = var.manage_migrated_frontend
}
