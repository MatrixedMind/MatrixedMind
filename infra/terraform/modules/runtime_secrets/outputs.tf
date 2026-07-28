output "secret_ids" {
  description = "Runtime secrets keyed by Cloud Run environment variable name."
  value = {
    for env_name, secret in google_secret_manager_secret.this : env_name => secret.secret_id
  }
}

output "secret_env" {
  description = "Cloud Run secret environment configuration with explicit versions."
  value = {
    for env_name, secret in google_secret_manager_secret.this : env_name => {
      secret_id = secret.secret_id
      version   = var.secrets[env_name].version
    }
  }
}
