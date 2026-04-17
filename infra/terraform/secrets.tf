# ── Secrets Manager ───────────────────────────────────────────────────────────
# One JSON secret holds all app config. ECS tasks pull it at startup via
# the execution role. Rotate by updating the secret value (not the ARN).

resource "aws_secretsmanager_secret" "app" {
  name        = "kwgrowth/${var.environment}/app"
  description = "Runtime config for Kuwait WhatsApp Growth Engine"
}

resource "aws_secretsmanager_secret_version" "app" {
  secret_id = aws_secretsmanager_secret.app.id
  secret_string = jsonencode({
    APP_ENV            = var.environment
    APP_SECRET_KEY     = var.app_secret
    JWT_SECRET_KEY     = var.jwt_secret
    DATABASE_URL       = "postgresql+asyncpg://app_user:${var.app_db_password}@${aws_db_instance.main.endpoint}/kwgrowth"
    MIGRATION_DATABASE_URL = "postgresql+asyncpg://kwgrowth:${var.db_password}@${aws_db_instance.main.endpoint}/kwgrowth"
    REDIS_URL          = "rediss://${aws_elasticache_replication_group.main.primary_endpoint_address}:6379/0"
    CELERY_BROKER_URL  = "rediss://${aws_elasticache_replication_group.main.primary_endpoint_address}:6379/1"
    CELERY_RESULT_BACKEND = "rediss://${aws_elasticache_replication_group.main.primary_endpoint_address}:6379/2"
    S3_ENDPOINT_URL    = "https://s3.me-south-1.amazonaws.com"
    S3_BUCKET_NAME     = aws_s3_bucket.media.id
    S3_REGION          = "me-south-1"
    SENTRY_DSN         = var.sentry_dsn
    TAP_SECRET_KEY     = var.tap_secret_key
    TAP_WEBHOOK_SECRET = var.tap_webhook_secret
    WHATSAPP_CLOUD_API_TOKEN         = var.whatsapp_token
    WHATSAPP_CLOUD_API_PHONE_NUMBER_ID = var.whatsapp_phone_number_id
    ANTHROPIC_API_KEY  = var.anthropic_api_key
    ALLOWED_ORIGINS    = "https://${var.domain}"
    APP_DOMAIN         = "https://${var.domain}"
  })
}

output "secret_arn" {
  value       = aws_secretsmanager_secret.app.arn
  description = "ARN of the app secrets bundle (used by ECS task definitions)"
}
