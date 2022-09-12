data "google_pubsub_topic" "horoscopes" {
  name = "horoscopes"
}

resource "google_pubsub_subscription" "horoscopes" {
  name  = "moderator-horoscopes"
  topic = data.google_pubsub_topic.horoscopes.id

  enable_exactly_once_delivery = true

  expiration_policy {
    ttl = ""
  }

  retry_policy {
    minimum_backoff = "30s"
    maximum_backoff = "600s"
  }
}
