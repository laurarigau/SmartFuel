# ---------------------------------------------------------------------------
# CloudWatch Alarms & Monitoring
# ---------------------------------------------------------------------------

# Alarm on DLQ messages (pipeline failures)
resource "aws_cloudwatch_metric_alarm" "dlq_not_empty" {
  alarm_name          = "${var.project_name}-dlq-has-messages-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = 300
  statistic           = "Maximum"
  threshold           = 0
  alarm_description   = "Triggered when any message enters the pipeline Dead-Letter Queue"
  alarm_actions       = [aws_sns_topic.admin_alerts.arn]

  dimensions = {
    QueueName = aws_sqs_queue.pipeline_dlq.name
  }

  tags = {
    Project     = var.project_name
    Environment = var.environment
  }
}

# Alarm on Lambda function errors
resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  alarm_name          = "${var.project_name}-lambda-high-errors-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 5
  alarm_description   = "Triggered when Lambda functions exceed 5 errors in 5 minutes"
  alarm_actions       = [aws_sns_topic.admin_alerts.arn]

  tags = {
    Project     = var.project_name
    Environment = var.environment
  }
}
