# ---------------------------------------------------------------------------
# AWS Amplify App for Static Frontend Hosting
# ---------------------------------------------------------------------------

resource "aws_amplify_app" "frontend" {
  name       = "${var.project_name}-web-${var.environment}"
  repository = "https://github.com/placeholder/smartfuel" # Placeholder for Git repo

  build_spec = <<-EOT
    version: 1
    frontend:
      phases:
        build:
          commands: []
      artifacts:
        baseDirectory: frontend
        files:
          - '**/*'
      cache:
        paths: []
  EOT

  custom_rule {
    source = "/<*>"
    target = "/index.html"
    status = "200"
  }

  environment_variables = {
    ENV = var.environment
  }

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}
