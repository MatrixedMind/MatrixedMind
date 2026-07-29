terraform {
  backend "gcs" {
    prefix = "matrixed-mind/prod"
  }
}
