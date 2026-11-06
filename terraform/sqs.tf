# ---------------------------------------------------------------------------
# Amazon SQS Dead-Letter Queue (DLQ) for failed pipeline events
# ---------------------------------------------------------------------------

resource "aws_sqs_queue" "pipeline_dlq" {
  name                      = "${var.project_name}-pipeline-dlq-${var.environment}"
  message_retention_seconds = 1209600 # 14 days

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# Policy allowing Step Functions and Lambda to send failed messages to DLQ
resource "aws_sqs_queue_policy" "dlq_policy" {
  queue_url = aws_sqs_queue.pipeline_dlq.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowStepFunctionsAndLambdaToSend"
        Effect = "Allow"
        Principal = {
          Service = ["states.amazonaws.com", "lambda.amazonaws.com"]
        }
        Action   = "sqs:SendMessage"
        Resource = aws_sqs_queue.pipeline_dlq.arn
      }
    ]
  })
}
