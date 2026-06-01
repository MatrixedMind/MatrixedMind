terraform {
  backend "gcs" {
    bucket = "UNSPECIFIED_PROJECT_ID-tf-state"
    prefix = "matrixed-mind/dev"
  }
}
