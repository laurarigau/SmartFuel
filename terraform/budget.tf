# ============================================================================
# SmartFuel — AWS Budget & Cost Alert
# ============================================================================
# Enforces the ~$50 budget specified in the Project Draft.
# Sends an email notification to the administrator if forecast or actual
# costs exceed the configured threshold.
# ============================================================================

resource "aws_budgets_budget" "monthly_budget" {
  name              = "${var.project_name}-monthly-budget-${var.environment}"
  budget_type       = "COST"
  limit_amount      = "50"
  limit_unit        = "USD"
  time_unit         = "MONTHLY"
  time_period_start = "2026-01-01_00:00"

  # Alert at 80% of budget ($40)
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.admin_email]
  }

  # Forecast alert if expected to exceed 100% of budget ($50)
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    notification_type          = "FORECASTED"
    subscriber_email_addresses = [var.admin_email]
  }
}
