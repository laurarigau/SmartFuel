# ---------------------------------------------------------------------------
# Amazon SES Email Identity for Sending User Alerts
# Note: SES is initially in sandbox mode; only verified emails can receive alerts.
# ---------------------------------------------------------------------------

resource "aws_ses_email_identity" "admin_sender" {
  email = var.admin_email
}
