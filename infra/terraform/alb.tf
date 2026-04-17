# ── ALB Listeners + Target Groups ─────────────────────────────────────────────
# Routes:
#   /v1/*   → API (port 8000)
#   /ws     → API (WebSocket, port 8000)
#   /health → API
#   /metrics → API
#   /*      → Frontend (port 3000)

# ── Target Groups ─────────────────────────────────────────────────────────────

resource "aws_lb_target_group" "api" {
  name        = "kwgrowth-api-${var.environment}"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = module.vpc.vpc_id
  target_type = "ip"

  health_check {
    path                = "/health"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    interval            = 15
    timeout             = 5
    matcher             = "200"
  }

  stickiness {
    type    = "lb_cookie"
    enabled = false
  }
}

resource "aws_lb_target_group" "frontend" {
  name        = "kwgrowth-fe-${var.environment}"
  port        = 3000
  protocol    = "HTTP"
  vpc_id      = module.vpc.vpc_id
  target_type = "ip"

  health_check {
    path                = "/"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    interval            = 30
    timeout             = 5
    matcher             = "200"
  }
}

# ── HTTPS Listener (port 443) ─────────────────────────────────────────────────

resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.main.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = aws_acm_certificate.main.arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.frontend.arn
  }
}

# API routes: /v1/*, /health*, /metrics, /docs, /redoc, /ws
resource "aws_lb_listener_rule" "api" {
  listener_arn = aws_lb_listener.https.arn
  priority     = 100

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }

  condition {
    path_pattern { values = ["/v1/*", "/health", "/health/*", "/metrics", "/metrics/*", "/docs", "/redoc", "/ws"] }
  }
}

# ── HTTP → HTTPS Redirect ─────────────────────────────────────────────────────

resource "aws_lb_listener" "http_redirect" {
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type = "redirect"
    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}

# ── ACM Certificate ───────────────────────────────────────────────────────────

resource "aws_acm_certificate" "main" {
  domain_name       = var.domain
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }
}

output "acm_validation_records" {
  value       = aws_acm_certificate.main.domain_validation_options
  description = "Create these DNS records to validate the ACM cert"
}
