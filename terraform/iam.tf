# ============================================================================
# SmartFuel — IAM Roles and Policies (Least Privilege)
# ============================================================================

# ---------------------------------------------------------------------------
# Shared: Lambda assume-role policy
# ---------------------------------------------------------------------------
data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

# ---------------------------------------------------------------------------
# Shared: Step Functions assume-role policy
# ---------------------------------------------------------------------------
data "aws_iam_policy_document" "sfn_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["states.amazonaws.com"]
    }
  }
}

# ---------------------------------------------------------------------------
# Shared: EventBridge assume-role policy
# ---------------------------------------------------------------------------
data "aws_iam_policy_document" "eventbridge_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["events.amazonaws.com"]
    }
  }
}

# ============================================================================
# 1. Ingest Lambda Role — s3:PutObject on raw/, CloudWatch Logs
# ============================================================================
resource "aws_iam_role" "ingest_lambda" {
  name               = "${var.project_name}-${var.environment}-ingest-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json

  tags = { Name = "${var.project_name}-ingest-lambda-role" }
}

data "aws_iam_policy_document" "ingest_lambda" {
  statement {
    sid       = "S3PutRaw"
    effect    = "Allow"
    actions   = ["s3:PutObject"]
    resources = ["${aws_s3_bucket.data_lake.arn}/raw/*"]
  }

  statement {
    sid    = "CloudWatchLogs"
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    resources = ["arn:aws:logs:${local.region}:${local.account_id}:log-group:/aws/lambda/${var.project_name}-${var.environment}-ingest:*"]
  }
}

resource "aws_iam_role_policy" "ingest_lambda" {
  name   = "${var.project_name}-${var.environment}-ingest-lambda-policy"
  role   = aws_iam_role.ingest_lambda.id
  policy = data.aws_iam_policy_document.ingest_lambda.json
}

# ============================================================================
# 2. Validate Lambda Role — s3:GetObject raw/, s3:PutObject quarantine/,
#    sns:Publish, CloudWatch Logs
# ============================================================================
resource "aws_iam_role" "validate_lambda" {
  name               = "${var.project_name}-${var.environment}-validate-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json

  tags = { Name = "${var.project_name}-validate-lambda-role" }
}

data "aws_iam_policy_document" "validate_lambda" {
  statement {
    sid       = "S3GetRaw"
    effect    = "Allow"
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.data_lake.arn}/raw/*"]
  }

  statement {
    sid       = "S3PutQuarantine"
    effect    = "Allow"
    actions   = ["s3:PutObject", "s3:CopyObject"]
    resources = ["${aws_s3_bucket.data_lake.arn}/quarantine/*"]
  }

  statement {
    sid       = "SNSPublish"
    effect    = "Allow"
    actions   = ["sns:Publish"]
    resources = [aws_sns_topic.admin_alerts.arn]
  }

  statement {
    sid    = "CloudWatchLogs"
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    resources = ["arn:aws:logs:${local.region}:${local.account_id}:log-group:/aws/lambda/${var.project_name}-${var.environment}-validate:*"]
  }
}

resource "aws_iam_role_policy" "validate_lambda" {
  name   = "${var.project_name}-${var.environment}-validate-lambda-policy"
  role   = aws_iam_role.validate_lambda.id
  policy = data.aws_iam_policy_document.validate_lambda.json
}

# ============================================================================
# 3. Clean Lambda Role — s3:GetObject raw/, s3:PutObject clean/,
#    CloudWatch Logs
# ============================================================================
resource "aws_iam_role" "clean_lambda" {
  name               = "${var.project_name}-${var.environment}-clean-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json

  tags = { Name = "${var.project_name}-clean-lambda-role" }
}

data "aws_iam_policy_document" "clean_lambda" {
  statement {
    sid       = "S3GetRaw"
    effect    = "Allow"
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.data_lake.arn}/raw/*"]
  }

  statement {
    sid       = "S3PutClean"
    effect    = "Allow"
    actions   = ["s3:PutObject"]
    resources = ["${aws_s3_bucket.data_lake.arn}/clean/*"]
  }

  statement {
    sid    = "CloudWatchLogs"
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    resources = ["arn:aws:logs:${local.region}:${local.account_id}:log-group:/aws/lambda/${var.project_name}-${var.environment}-clean:*"]
  }
}

resource "aws_iam_role_policy" "clean_lambda" {
  name   = "${var.project_name}-${var.environment}-clean-lambda-policy"
  role   = aws_iam_role.clean_lambda.id
  policy = data.aws_iam_policy_document.clean_lambda.json
}

# ============================================================================
# 4. Save Prices Lambda Role — dynamodb:PutItem/UpdateItem on
#    stations + prices, CloudWatch Logs
# ============================================================================
resource "aws_iam_role" "save_prices_lambda" {
  name               = "${var.project_name}-${var.environment}-save-prices-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json

  tags = { Name = "${var.project_name}-save-prices-lambda-role" }
}

data "aws_iam_policy_document" "save_prices_lambda" {
  statement {
    sid    = "DynamoDBWrite"
    effect = "Allow"
    actions = [
      "dynamodb:PutItem",
      "dynamodb:UpdateItem",
      "dynamodb:BatchWriteItem"
    ]
    resources = [
      aws_dynamodb_table.stations.arn,
      aws_dynamodb_table.prices.arn
    ]
  }

  statement {
    sid       = "S3GetClean"
    effect    = "Allow"
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.data_lake.arn}/clean/*"]
  }

  statement {
    sid    = "CloudWatchLogs"
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    resources = ["arn:aws:logs:${local.region}:${local.account_id}:log-group:/aws/lambda/${var.project_name}-${var.environment}-save-prices:*"]
  }
}

resource "aws_iam_role_policy" "save_prices_lambda" {
  name   = "${var.project_name}-${var.environment}-save-prices-lambda-policy"
  role   = aws_iam_role.save_prices_lambda.id
  policy = data.aws_iam_policy_document.save_prices_lambda.json
}

# ============================================================================
# 5. Predict Lambda Role — s3:GetObject models/, dynamodb:PutItem predictions,
#    CloudWatch Logs
# ============================================================================
resource "aws_iam_role" "predict_lambda" {
  name               = "${var.project_name}-${var.environment}-predict-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json

  tags = { Name = "${var.project_name}-predict-lambda-role" }
}

data "aws_iam_policy_document" "predict_lambda" {
  statement {
    sid       = "S3GetModels"
    effect    = "Allow"
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.data_lake.arn}/models/*"]
  }

  statement {
    sid    = "DynamoDBWrite"
    effect = "Allow"
    actions = [
      "dynamodb:PutItem",
      "dynamodb:BatchWriteItem"
    ]
    resources = [aws_dynamodb_table.predictions.arn]
  }

  statement {
    sid    = "DynamoDBReadPrices"
    effect = "Allow"
    actions = [
      "dynamodb:Query",
      "dynamodb:GetItem"
    ]
    resources = [
      aws_dynamodb_table.prices.arn,
      "${aws_dynamodb_table.prices.arn}/index/*"
    ]
  }

  statement {
    sid    = "CloudWatchLogs"
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    resources = ["arn:aws:logs:${local.region}:${local.account_id}:log-group:/aws/lambda/${var.project_name}-${var.environment}-predict:*"]
  }
}

resource "aws_iam_role_policy" "predict_lambda" {
  name   = "${var.project_name}-${var.environment}-predict-lambda-policy"
  role   = aws_iam_role.predict_lambda.id
  policy = data.aws_iam_policy_document.predict_lambda.json
}

# ============================================================================
# 6. Alerts Lambda Role — dynamodb:GetItem subscriptions, ses:SendEmail,
#    DynamoDB Streams, CloudWatch Logs
# ============================================================================
resource "aws_iam_role" "alerts_lambda" {
  name               = "${var.project_name}-${var.environment}-alerts-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json

  tags = { Name = "${var.project_name}-alerts-lambda-role" }
}

data "aws_iam_policy_document" "alerts_lambda" {
  statement {
    sid    = "DynamoDBRead"
    effect = "Allow"
    actions = [
      "dynamodb:GetItem",
      "dynamodb:Query"
    ]
    resources = [
      aws_dynamodb_table.subscriptions.arn,
      "${aws_dynamodb_table.subscriptions.arn}/index/*"
    ]
  }

  statement {
    sid    = "DynamoDBStreams"
    effect = "Allow"
    actions = [
      "dynamodb:GetRecords",
      "dynamodb:GetShardIterator",
      "dynamodb:DescribeStream",
      "dynamodb:ListStreams"
    ]
    resources = [aws_dynamodb_table.prices.stream_arn]
  }

  statement {
    sid       = "SESSend"
    effect    = "Allow"
    actions   = ["ses:SendEmail", "ses:SendRawEmail"]
    resources = ["*"]
  }

  statement {
    sid    = "CloudWatchLogs"
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    resources = ["arn:aws:logs:${local.region}:${local.account_id}:log-group:/aws/lambda/${var.project_name}-${var.environment}-alerts:*"]
  }
}

resource "aws_iam_role_policy" "alerts_lambda" {
  name   = "${var.project_name}-${var.environment}-alerts-lambda-policy"
  role   = aws_iam_role.alerts_lambda.id
  policy = data.aws_iam_policy_document.alerts_lambda.json
}

# ============================================================================
# 7. Retrain Lambda Role — s3:GetObject/PutObject models+clean,
#    athena:*, glue:*, CloudWatch Logs
# ============================================================================
resource "aws_iam_role" "retrain_lambda" {
  name               = "${var.project_name}-${var.environment}-retrain-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json

  tags = { Name = "${var.project_name}-retrain-lambda-role" }
}

data "aws_iam_policy_document" "retrain_lambda" {
  statement {
    sid    = "S3ReadWrite"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:ListBucket"
    ]
    resources = [
      aws_s3_bucket.data_lake.arn,
      "${aws_s3_bucket.data_lake.arn}/models/*",
      "${aws_s3_bucket.data_lake.arn}/clean/*"
    ]
  }

  statement {
    sid    = "AthenaAccess"
    effect = "Allow"
    actions = [
      "athena:StartQueryExecution",
      "athena:GetQueryExecution",
      "athena:GetQueryResults",
      "athena:StopQueryExecution"
    ]
    resources = ["arn:aws:athena:${local.region}:${local.account_id}:workgroup/*"]
  }

  statement {
    sid    = "GlueAccess"
    effect = "Allow"
    actions = [
      "glue:GetTable",
      "glue:GetTables",
      "glue:GetDatabase",
      "glue:GetDatabases",
      "glue:GetPartitions"
    ]
    resources = ["*"]
  }

  statement {
    sid    = "AthenaResultsBucket"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:GetBucketLocation",
      "s3:ListBucket"
    ]
    resources = [
      "arn:aws:s3:::aws-athena-query-results-${local.account_id}-${local.region}",
      "arn:aws:s3:::aws-athena-query-results-${local.account_id}-${local.region}/*"
    ]
  }

  statement {
    sid    = "CloudWatchLogs"
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    resources = ["arn:aws:logs:${local.region}:${local.account_id}:log-group:/aws/lambda/${var.project_name}-${var.environment}-retrain:*"]
  }
}

resource "aws_iam_role_policy" "retrain_lambda" {
  name   = "${var.project_name}-${var.environment}-retrain-lambda-policy"
  role   = aws_iam_role.retrain_lambda.id
  policy = data.aws_iam_policy_document.retrain_lambda.json
}

# ============================================================================
# 8. API Lambda Role — dynamodb:Query/GetItem on all tables,
#    CloudWatch Logs
# ============================================================================
resource "aws_iam_role" "api_lambda" {
  name               = "${var.project_name}-${var.environment}-api-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json

  tags = { Name = "${var.project_name}-api-lambda-role" }
}

data "aws_iam_policy_document" "api_lambda" {
  statement {
    sid    = "DynamoDBRead"
    effect = "Allow"
    actions = [
      "dynamodb:GetItem",
      "dynamodb:Query",
      "dynamodb:Scan",
      "dynamodb:BatchGetItem"
    ]
    resources = [
      aws_dynamodb_table.stations.arn,
      "${aws_dynamodb_table.stations.arn}/index/*",
      aws_dynamodb_table.prices.arn,
      "${aws_dynamodb_table.prices.arn}/index/*",
      aws_dynamodb_table.predictions.arn,
      "${aws_dynamodb_table.predictions.arn}/index/*",
      aws_dynamodb_table.subscriptions.arn,
      "${aws_dynamodb_table.subscriptions.arn}/index/*"
    ]
  }

  statement {
    sid    = "DynamoDBWriteSubscriptions"
    effect = "Allow"
    actions = [
      "dynamodb:PutItem",
      "dynamodb:DeleteItem"
    ]
    resources = [aws_dynamodb_table.subscriptions.arn]
  }

  statement {
    sid    = "CloudWatchLogs"
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    resources = ["arn:aws:logs:${local.region}:${local.account_id}:log-group:/aws/lambda/${var.project_name}-${var.environment}-api:*"]
  }
}

resource "aws_iam_role_policy" "api_lambda" {
  name   = "${var.project_name}-${var.environment}-api-lambda-policy"
  role   = aws_iam_role.api_lambda.id
  policy = data.aws_iam_policy_document.api_lambda.json
}

# ============================================================================
# 9. Step Functions Execution Role
# ============================================================================
resource "aws_iam_role" "step_functions" {
  name               = "${var.project_name}-${var.environment}-sfn-role"
  assume_role_policy = data.aws_iam_policy_document.sfn_assume_role.json

  tags = { Name = "${var.project_name}-sfn-role" }
}

data "aws_iam_policy_document" "step_functions" {
  statement {
    sid    = "InvokeLambdas"
    effect = "Allow"
    actions = [
      "lambda:InvokeFunction"
    ]
    resources = [
      aws_lambda_function.validate.arn,
      aws_lambda_function.clean.arn,
      aws_lambda_function.save_prices.arn,
      aws_lambda_function.predict.arn,
      aws_lambda_function.retrain.arn
    ]
  }

  statement {
    sid    = "SQSSendDLQ"
    effect = "Allow"
    actions = [
      "sqs:SendMessage"
    ]
    resources = [aws_sqs_queue.pipeline_dlq.arn]
  }

  statement {
    sid    = "SNSPublish"
    effect = "Allow"
    actions = [
      "sns:Publish"
    ]
    resources = [aws_sns_topic.admin_alerts.arn]
  }

  statement {
    sid    = "CloudWatchLogs"
    effect = "Allow"
    actions = [
      "logs:CreateLogDelivery",
      "logs:GetLogDelivery",
      "logs:UpdateLogDelivery",
      "logs:DeleteLogDelivery",
      "logs:ListLogDeliveries",
      "logs:PutResourcePolicy",
      "logs:DescribeResourcePolicies",
      "logs:DescribeLogGroups"
    ]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "step_functions" {
  name   = "${var.project_name}-${var.environment}-sfn-policy"
  role   = aws_iam_role.step_functions.id
  policy = data.aws_iam_policy_document.step_functions.json
}

# ============================================================================
# 10. EventBridge Role — to start Step Functions and invoke Lambda
# ============================================================================
resource "aws_iam_role" "eventbridge" {
  name               = "${var.project_name}-${var.environment}-eventbridge-role"
  assume_role_policy = data.aws_iam_policy_document.eventbridge_assume_role.json

  tags = { Name = "${var.project_name}-eventbridge-role" }
}

data "aws_iam_policy_document" "eventbridge" {
  statement {
    sid    = "StartStepFunctions"
    effect = "Allow"
    actions = [
      "states:StartExecution"
    ]
    resources = [
      aws_sfn_state_machine.processing.arn,
      aws_sfn_state_machine.retraining.arn
    ]
  }

  statement {
    sid    = "InvokeLambda"
    effect = "Allow"
    actions = [
      "lambda:InvokeFunction"
    ]
    resources = [aws_lambda_function.ingest.arn]
  }
}

resource "aws_iam_role_policy" "eventbridge" {
  name   = "${var.project_name}-${var.environment}-eventbridge-policy"
  role   = aws_iam_role.eventbridge.id
  policy = data.aws_iam_policy_document.eventbridge.json
}
