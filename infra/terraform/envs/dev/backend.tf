terraform {
  backend "gcs" {
    bucket = "UNSPECIFIED_PROJECT_ID-tf-state"
    prefix = "wiki-app/dev"
  }
}
