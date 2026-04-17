# ── CloudWatch Log Group ──────────────────────────────────────────────────────

resource "aws_cloudwatch_log_group" "app" {
  name              = "/ecs/kwgrowth-${var.environment}"
  retention_in_days = 30
}

# ── Shared container environment (pulled from Secrets Manager) ────────────────

locals {
  # All ECS containers share the same secrets bundle.
  secrets_from = [{
    name      = "APP_SECRETS"
    valueFrom = aws_secretsmanager_secret.app.arn
  }]

  # Common container-level log config for awslogs driver.
  log_config = {
    logDriver = "awslogs"
    options = {
      "awslogs-group"         = aws_cloudwatch_log_group.app.name
      "awslogs-region"        = "me-south-1"
      "awslogs-stream-prefix" = "ecs"
    }
  }
}

# ── API task + service ────────────────────────────────────────────────────────

resource "aws_ecs_task_definition" "api" {
  family                   = "kwgrowth-api"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.api_cpu
  memory                   = var.api_memory
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name      = "api"
    image     = "${aws_ecr_repository.api.repository_url}:${var.environment}"
    essential = true
    portMappings = [{ containerPort = 8000, protocol = "tcp" }]
    secrets      = local.secrets_from
    logConfiguration = local.log_config
    healthCheck = {
      command     = ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:8000/health')\""]
      interval    = 15
      timeout     = 5
      retries     = 3
      startPeriod = 30
    }
  }])
}

resource "aws_ecs_service" "api" {
  name            = "kwgrowth-api"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = 2
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = module.vpc.private_subnets
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.api.arn
    container_name   = "api"
    container_port   = 8000
  }

  deployment_minimum_healthy_percent = 50
  deployment_maximum_percent         = 200
  health_check_grace_period_seconds  = 60

  depends_on = [aws_lb_listener.https]
}

# ── Frontend task + service ───────────────────────────────────────────────────

resource "aws_ecs_task_definition" "frontend" {
  family                   = "kwgrowth-frontend"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = 256
  memory                   = 512
  execution_role_arn       = aws_iam_role.ecs_execution.arn

  container_definitions = jsonencode([{
    name      = "frontend"
    image     = "${aws_ecr_repository.frontend.repository_url}:${var.environment}"
    essential = true
    portMappings = [{ containerPort = 3000, protocol = "tcp" }]
    environment = [
      { name = "NEXT_PUBLIC_API_URL", value = "https://${var.domain}/v1" },
      { name = "NEXT_PUBLIC_WS_URL",  value = "wss://${var.domain}/ws" },
    ]
    logConfiguration = local.log_config
  }])
}

resource "aws_ecs_service" "frontend" {
  name            = "kwgrowth-frontend"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.frontend.arn
  desired_count   = 2
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = module.vpc.private_subnets
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.frontend.arn
    container_name   = "frontend"
    container_port   = 3000
  }

  depends_on = [aws_lb_listener.https]
}

# ── Celery Worker ─────────────────────────────────────────────────────────────

resource "aws_ecs_task_definition" "worker" {
  family                   = "kwgrowth-celery-worker"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.worker_cpu
  memory                   = var.worker_memory
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name      = "worker"
    image     = "${aws_ecr_repository.api.repository_url}:${var.environment}"
    essential = true
    command   = ["celery", "-A", "app.tasks.celery_app", "worker", "--loglevel=info",
                 "-Q", "default,messaging,automations,webhooks,analytics,imports,shipping,ai"]
    secrets          = local.secrets_from
    logConfiguration = local.log_config
  }])
}

resource "aws_ecs_service" "worker" {
  name            = "kwgrowth-celery-worker"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.worker.arn
  desired_count   = 2
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = module.vpc.private_subnets
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = false
  }
}

# ── Celery Beat ───────────────────────────────────────────────────────────────

resource "aws_ecs_task_definition" "beat" {
  family                   = "kwgrowth-celery-beat"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = 256
  memory                   = 512
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name      = "beat"
    image     = "${aws_ecr_repository.api.repository_url}:${var.environment}"
    essential = true
    command   = ["celery", "-A", "app.tasks.celery_app", "beat", "--loglevel=info"]
    secrets          = local.secrets_from
    logConfiguration = local.log_config
  }])
}

resource "aws_ecs_service" "beat" {
  name            = "kwgrowth-celery-beat"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.beat.arn
  desired_count   = 1  # Beat must be a singleton
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = module.vpc.private_subnets
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = false
  }
}

# ── Migration task (one-shot, no service) ─────────────────────────────────────
# deploy.yml runs this as a one-shot Fargate task before rolling services.

resource "aws_ecs_task_definition" "migrate" {
  family                   = "kwgrowth-migrate"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = 256
  memory                   = 512
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name      = "migrate"
    image     = "${aws_ecr_repository.api.repository_url}:${var.environment}"
    essential = true
    command   = ["alembic", "-c", "alembic/alembic.ini", "upgrade", "head"]
    secrets          = local.secrets_from
    logConfiguration = local.log_config
  }])
}
