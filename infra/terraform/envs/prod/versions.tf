terraform {
  # Cross-variable input validation used by the operational safeguards needs
  # Terraform 1.9 or later.
  required_version = ">= 1.9.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 7.5, < 8.0"
    }
  }
}
