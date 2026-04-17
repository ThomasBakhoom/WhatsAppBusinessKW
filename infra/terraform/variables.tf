# ── Shared Variables ──────────────────────────────────────────────────────────
# Override per-environment via terraform.tfvars or -var flags.

variable "environment" {
  description = "Environment name (staging or production)"
  type        = string
  default     = "production"
  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "Must be staging or production."
  }
}

variable "domain" {
  description = "Primary app domain (used for ALB cert + CORS)"
  type        = string
  default     = "app.kwgrowth.com"
}

variable "db_password" {
  description = "Master password for the RDS instance"
  type        = string
  sensitive   = true
}

variable "app_db_password" {
  description = "Password for the runtime app_user role (non-superuser, RLS enforced)"
  type        = string
  sensitive   = true
}

variable "jwt_secret" {
  description = "JWT signing key (≥32 chars)"
  type        = string
  sensitive   = true
}

variable "app_secret" {
  description = "Application secret key (≥32 chars)"
  type        = string
  sensitive   = true
}

variable "sentry_dsn" {
  description = "Sentry DSN (leave empty to disable)"
  type        = string
  default     = ""
}

variable "tap_secret_key" {
  description = "Tap Payments secret key"
  type        = string
  default     = ""
  sensitive   = true
}

variable "tap_webhook_secret" {
  description = "Tap Payments webhook signature secret"
  type        = string
  default     = ""
  sensitive   = true
}

variable "whatsapp_token" {
  description = "WhatsApp Cloud API access token"
  type        = string
  default     = ""
  sensitive   = true
}

variable "whatsapp_phone_number_id" {
  description = "WhatsApp Cloud API phone number ID"
  type        = string
  default     = ""
}

variable "anthropic_api_key" {
  description = "Anthropic API key for Claude"
  type        = string
  default     = ""
  sensitive   = true
}

# ── Sizing ────────────────────────────────────────────────────────────────────

variable "api_cpu" {
  description = "API task CPU (Fargate units)"
  type        = number
  default     = 512
}

variable "api_memory" {
  description = "API task memory (MB)"
  type        = number
  default     = 1024
}

variable "worker_cpu" {
  description = "Celery worker task CPU"
  type        = number
  default     = 512
}

variable "worker_memory" {
  description = "Celery worker task memory (MB)"
  type        = number
  default     = 1024
}
