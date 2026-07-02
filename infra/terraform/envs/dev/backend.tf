terraform {
  backend "gcs" {
    prefix = "matrixed-mind/dev"
  }
}
