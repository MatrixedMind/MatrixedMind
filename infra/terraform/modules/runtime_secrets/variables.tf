variable "project_id" {
  description = "GCP project that owns the secrets."
  type        = string
}

variable "accessor_member" {
  description = "IAM member allowed to read secret payloads."
  type        = string
}

variable "secrets" {
  description = "Runtime secrets keyed by Cloud Run environment variable name."
  type = map(object({
    secret_id = string
    version   = string
  }))
}
