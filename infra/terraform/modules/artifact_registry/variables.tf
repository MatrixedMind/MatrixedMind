variable "project_id" {
  description = "GCP project that owns the repository."
  type        = string
}

variable "location" {
  description = "Artifact Registry location."
  type        = string
}

variable "repository_id" {
  description = "Artifact Registry repository ID."
  type        = string
}

variable "description" {
  description = "Artifact Registry repository description."
  type        = string
  default     = "MatrixedMind container images"
}
