terraform {
  backend "gcs" {
    bucket = "moderator-terraform-state"
  }

  required_providers {
    google = {
      version = "~> 4.35.0"
    }
  }
}

provider "google" {
  project = "prep-telegram-bots"
  region  = "europe-west3"
}