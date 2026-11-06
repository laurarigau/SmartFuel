# ---------------------------------------------------------------------------
# Amazon SNS for Admin Alerts (Validation failures, model retraining status)
# ---------------------------------------------------------------------------

resource "aws_sns_topic" "admin_alerts" {
  name = "${var.project_name}-admin-alerts-${var.environment}"

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# Email subscription for the admin
resource "aws_sns_topic_subscription" "admin_email" {
  topic_arn = aws_sns_topic.admin_alerts.arn
  protocol  = "email"
  endpoint  = var.admin_email
}
