variable "edge_project_id" {
  description = "GCP project ID that owns the shared external Application Load Balancer."
  type        = string
}

variable "region" {
  description = "Default provider region; shared frontend resources remain global."
  type        = string
  default     = "us-central1"
}

variable "impersonate_service_account" {
  description = "Optional keyless edge administrator service account impersonated by the Google provider."
  type        = string
  default     = null
}

variable "resource_name_prefix" {
  description = "Name prefix for the prepared global external managed frontend resources."
  type        = string
  default     = "matrixedmind-shared"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{0,47}[a-z0-9]$", var.resource_name_prefix))
    error_message = "resource_name_prefix must be a valid lowercase GCP resource prefix between 2 and 49 characters."
  }
}

variable "existing_hostname" {
  description = "Existing hostname that must remain routed to its current application."
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+$", var.existing_hostname))
    error_message = "existing_hostname must be a lowercase fully qualified domain name."
  }
}

variable "matrixedmind_hostname" {
  description = "Custom hostname routed to the production MatrixedMind backend."
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+$", var.matrixedmind_hostname))
    error_message = "matrixedmind_hostname must be a lowercase fully qualified domain name."
  }
}

variable "static_ip_address" {
  description = "Existing global static IPv4 address reused by the shared frontend."
  type        = string

  validation {
    condition     = can(regex("^[0-9]{1,3}(\\.[0-9]{1,3}){3}$", var.static_ip_address))
    error_message = "static_ip_address must be an explicit IPv4 address."
  }
}

variable "existing_serverless_neg_self_link" {
  description = "Fully qualified self-link for the existing application's serverless NEG."
  type        = string

  validation {
    condition     = can(regex("^https://www.googleapis.com/compute/v1/projects/[^/]+/regions/[^/]+/networkEndpointGroups/[^/]+$", var.existing_serverless_neg_self_link))
    error_message = "existing_serverless_neg_self_link must be a fully qualified regional NEG self-link."
  }
}

variable "existing_backend_service_self_link" {
  description = "Fully qualified self-link for the existing application's current global backend service."
  type        = string

  validation {
    condition     = can(regex("^https://www.googleapis.com/compute/v1/projects/[^/]+/global/backendServices/[^/]+$", var.existing_backend_service_self_link))
    error_message = "existing_backend_service_self_link must be a fully qualified global backend-service self-link."
  }
}

variable "existing_backend_service_name" {
  description = "Name of the existing global backend service adopted after its in-place migration."
  type        = string
}

variable "existing_https_forwarding_rule_name" {
  description = "Name of the existing HTTPS forwarding rule adopted after its in-place migration."
  type        = string
}

variable "existing_http_forwarding_rule_name" {
  description = "Name of the existing HTTP forwarding rule adopted after its in-place migration."
  type        = string
}

variable "matrixedmind_backend_service_self_link" {
  description = "Fully qualified production-project EXTERNAL_MANAGED backend-service self-link."
  type        = string

  validation {
    condition     = can(regex("^https://www.googleapis.com/compute/v1/projects/[^/]+/global/backendServices/[^/]+$", var.matrixedmind_backend_service_self_link))
    error_message = "matrixedmind_backend_service_self_link must be a fully qualified global backend-service self-link."
  }
}

variable "manage_migrated_frontend" {
  description = "Adopt the existing backend and forwarding rules after their separately approved in-place EXTERNAL_MANAGED migration."
  type        = bool
  default     = false
}

variable "frontend_migration_confirmed" {
  description = "Explicit operator confirmation that Google's staged in-place backend and forwarding-rule migration completed successfully."
  type        = bool
  default     = false
}

variable "certificates_active_confirmed" {
  description = "Explicit operator confirmation that both DNS-authorized Certificate Manager certificates are ACTIVE."
  type        = bool
  default     = false
}
