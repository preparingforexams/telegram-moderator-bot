resource "google_service_account" "service_account" {
  account_id   = "moderator-bot"
  display_name = "Moderator Bot"
}

resource "google_project_iam_member" "service_account_publisher" {
  project = google_service_account.service_account.project
  role    = "projects/prep-telegram-bots/roles/pubsubConsumer"
  member  = "serviceAccount:${google_service_account.service_account.email}"
}
