output "name" {
  description = "Cloud Run service name."
  value       = google_cloud_run_v2_service.this.name
}

output "uri" {
  description = "Cloud Run service URI."
  value       = google_cloud_run_v2_service.this.uri
}

output "serverless_neg_id" {
  description = "Application-project serverless NEG backing MatrixedMind's load-balancer backend service."
  value = (
    var.invocation_mode == "external_load_balancer"
    ? google_compute_region_network_endpoint_group.load_balancer[0].id
    : null
  )
}

output "load_balancer_backend_service_self_link" {
  description = "Fully qualified application-project backend service reference for an external load balancer URL map."
  value = (
    var.invocation_mode == "external_load_balancer"
    ? google_compute_backend_service.load_balancer[0].self_link
    : null
  )
}

output "action_allowlist_security_policy_id" {
  description = "Optional Cloud Armor policy protecting /api/llm/* through a reviewed Enterprise address group."
  value = (
    var.invocation_mode == "external_load_balancer"
    && var.openai_action_address_group_name != null
    ? google_compute_security_policy.action_allowlist[0].id
    : null
  )
}
