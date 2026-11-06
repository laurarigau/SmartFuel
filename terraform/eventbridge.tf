# ============================================================================
# SmartFuel — EventBridge Rules
# ============================================================================

# ---------------------------------------------------------------------------
# 1. Scheduled Ingest — 4x/day at 06:00, 10:00, 14:00, 18:00 UTC
# ---------------------------------------------------------------------------
resource "aws_cloudwatch_event_rule" "ingest_schedule" {
  name                = "${var.project_name}-${var.environment}-ingest-schedule"
  description         = "Triggers fuel price ingestion 4 times per day"
  schedule_expression = "cron(0 6,10,14,18 * * ? *)"

  tags = {
    Name = "${var.project_name}-ingest-schedule"
  }
}

resource "aws_cloudwatch_event_target" "ingest_lambda" {
  rule      = aws_cloudwatch_event_rule.ingest_schedule.name
  target_id = "${var.project_name}-ingest-lambda"
  arn       = aws_lambda_function.ingest.arn
}

resource "aws_lambda_permission" "eventbridge_ingest" {
  statement_id  = "AllowEventBridgeInvokeIngest"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ingest.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.ingest_schedule.arn
}

# ---------------------------------------------------------------------------
# 2. S3 New Object in raw/ → Processing Step Functions
# ---------------------------------------------------------------------------
resource "aws_cloudwatch_event_rule" "s3_raw_upload" {
  name        = "${var.project_name}-${var.environment}-s3-raw-upload"
  description = "Triggers processing workflow when new file arrives in raw/ prefix"

  event_pattern = jsonencode({
    source      = ["aws.s3"]
    detail-type = ["Object Created"]
    detail = {
      bucket = {
        name = [aws_s3_bucket.data_lake.id]
      }
      object = {
        key = [{
          prefix = "raw/"
        }]
      }
    }
  })

  tags = {
    Name = "${var.project_name}-s3-raw-upload"
  }
}

resource "aws_cloudwatch_event_target" "processing_sfn" {
  rule      = aws_cloudwatch_event_rule.s3_raw_upload.name
  target_id = "${var.project_name}-processing-sfn"
  arn       = aws_sfn_state_machine.processing.arn
  role_arn  = aws_iam_role.eventbridge.arn

  input_transformer {
    input_paths = {
      bucket = "$.detail.bucket.name"
      key    = "$.detail.object.key"
    }
    input_template = <<EOF
{
  "source_bucket": <bucket>,
  "source_key": <key>
}
EOF
  }
}

# ---------------------------------------------------------------------------
# 3. Weekly Retraining — Every Monday at 02:00 UTC
# ---------------------------------------------------------------------------
resource "aws_cloudwatch_event_rule" "retraining_schedule" {
  name                = "${var.project_name}-${var.environment}-retraining-schedule"
  description         = "Triggers weekly model retraining on Monday mornings"
  schedule_expression = "cron(0 2 ? * MON *)"

  tags = {
    Name = "${var.project_name}-retraining-schedule"
  }
}

resource "aws_cloudwatch_event_target" "retraining_sfn" {
  rule      = aws_cloudwatch_event_rule.retraining_schedule.name
  target_id = "${var.project_name}-retraining-sfn"
  arn       = aws_sfn_state_machine.retraining.arn
  role_arn  = aws_iam_role.eventbridge.arn

  input = jsonencode({
    trigger = "weekly_schedule"
  })
}
