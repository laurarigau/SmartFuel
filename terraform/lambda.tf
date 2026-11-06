# ============================================================================
# SmartFuel — Lambda Functions
# ============================================================================

# ---------------------------------------------------------------------------
# Lambda Layer for shared dependencies (pandas, pyarrow, requests, etc.)
# ---------------------------------------------------------------------------
resource "aws_lambda_layer_version" "dependencies" {
  layer_name          = "${var.project_name}-${var.environment}-dependencies"
  description         = "Shared Python dependencies for SmartFuel Lambdas"
  compatible_runtimes = [var.lambda_runtime]
  filename            = "${path.module}/../packages/lambda_layer.zip"
  source_code_hash    = filebase64sha256("${path.module}/../packages/lambda_layer.zip")
}

# ---------------------------------------------------------------------------
# Lambda Layer for SmartFuel src code
# ---------------------------------------------------------------------------
resource "aws_lambda_layer_version" "src" {
  layer_name          = "${var.project_name}-${var.environment}-src"
  description         = "SmartFuel application source code"
  compatible_runtimes = [var.lambda_runtime]
  filename            = "${path.module}/../packages/src_layer.zip"
  source_code_hash    = filebase64sha256("${path.module}/../packages/src_layer.zip")
}

# ---------------------------------------------------------------------------
# Common environment variables for all Lambdas
# ---------------------------------------------------------------------------
locals {
  lambda_env_vars = {
    SMARTFUEL_ENV                  = "aws"
    SMARTFUEL_S3_BUCKET            = aws_s3_bucket.data_lake.id
    SMARTFUEL_DYNAMO_STATIONS      = aws_dynamodb_table.stations.name
    SMARTFUEL_DYNAMO_PRICES        = aws_dynamodb_table.prices.name
    SMARTFUEL_DYNAMO_PREDICTIONS   = aws_dynamodb_table.predictions.name
    SMARTFUEL_DYNAMO_SUBSCRIPTIONS = aws_dynamodb_table.subscriptions.name
    SMARTFUEL_SNS_TOPIC            = aws_sns_topic.admin_alerts.arn
    SMARTFUEL_SQS_DLQ              = aws_sqs_queue.pipeline_dlq.url
    SMARTFUEL_LOG_LEVEL            = "INFO"
    AWS_REGION_NAME                = var.aws_region
  }
}

# ============================================================================
# 1. Ingest Lambda
# ============================================================================
resource "aws_lambda_function" "ingest" {
  function_name = "${var.project_name}-${var.environment}-ingest"
  description   = "Fetches fuel price data from Spanish Ministry API and stores in S3"
  role          = aws_iam_role.ingest_lambda.arn
  handler       = "handler.handler"
  runtime       = var.lambda_runtime
  timeout       = var.lambda_timeout
  memory_size   = var.lambda_memory
  filename      = "${path.module}/../packages/ingest.zip"

  source_code_hash = filebase64sha256("${path.module}/../packages/ingest.zip")

  layers = [
    aws_lambda_layer_version.dependencies.arn,
    aws_lambda_layer_version.src.arn
  ]

  environment {
    variables = local.lambda_env_vars
  }

  tags = { Name = "${var.project_name}-ingest" }
}

# ============================================================================
# 2. Validate Lambda
# ============================================================================
resource "aws_lambda_function" "validate" {
  function_name = "${var.project_name}-${var.environment}-validate"
  description   = "Validates raw fuel price data; quarantines invalid files"
  role          = aws_iam_role.validate_lambda.arn
  handler       = "handler.handler"
  runtime       = var.lambda_runtime
  timeout       = var.lambda_timeout
  memory_size   = var.lambda_memory
  filename      = "${path.module}/../packages/validate.zip"

  source_code_hash = filebase64sha256("${path.module}/../packages/validate.zip")

  layers = [
    aws_lambda_layer_version.dependencies.arn,
    aws_lambda_layer_version.src.arn
  ]

  environment {
    variables = local.lambda_env_vars
  }

  tags = { Name = "${var.project_name}-validate" }
}

# ============================================================================
# 3. Clean Lambda
# ============================================================================
resource "aws_lambda_function" "clean" {
  function_name = "${var.project_name}-${var.environment}-clean"
  description   = "Cleans raw data, converts to Parquet, detects price changes"
  role          = aws_iam_role.clean_lambda.arn
  handler       = "handler.handler"
  runtime       = var.lambda_runtime
  timeout       = 300
  memory_size   = 512
  filename      = "${path.module}/../packages/clean.zip"

  source_code_hash = filebase64sha256("${path.module}/../packages/clean.zip")

  layers = [
    aws_lambda_layer_version.dependencies.arn,
    aws_lambda_layer_version.src.arn
  ]

  environment {
    variables = local.lambda_env_vars
  }

  tags = { Name = "${var.project_name}-clean" }
}

# ============================================================================
# 4. Save Prices Lambda
# ============================================================================
resource "aws_lambda_function" "save_prices" {
  function_name = "${var.project_name}-${var.environment}-save-prices"
  description   = "Writes changed fuel prices to DynamoDB"
  role          = aws_iam_role.save_prices_lambda.arn
  handler       = "handler.handler"
  runtime       = var.lambda_runtime
  timeout       = 300
  memory_size   = 512
  filename      = "${path.module}/../packages/save_prices.zip"

  source_code_hash = filebase64sha256("${path.module}/../packages/save_prices.zip")

  layers = [
    aws_lambda_layer_version.dependencies.arn,
    aws_lambda_layer_version.src.arn
  ]

  environment {
    variables = local.lambda_env_vars
  }

  tags = { Name = "${var.project_name}-save-prices" }
}

# ============================================================================
# 5. Predict Lambda
# ============================================================================
resource "aws_lambda_function" "predict" {
  function_name = "${var.project_name}-${var.environment}-predict"
  description   = "Runs price prediction model and stores results"
  role          = aws_iam_role.predict_lambda.arn
  handler       = "handler.handler"
  runtime       = var.lambda_runtime
  timeout       = 300
  memory_size   = 512
  filename      = "${path.module}/../packages/predict.zip"

  source_code_hash = filebase64sha256("${path.module}/../packages/predict.zip")

  layers = [
    aws_lambda_layer_version.dependencies.arn,
    aws_lambda_layer_version.src.arn
  ]

  environment {
    variables = local.lambda_env_vars
  }

  tags = { Name = "${var.project_name}-predict" }
}

# ============================================================================
# 6. Alerts Lambda (triggered by DynamoDB Streams)
# ============================================================================
resource "aws_lambda_function" "alerts" {
  function_name = "${var.project_name}-${var.environment}-alerts"
  description   = "Processes DynamoDB Stream events to send price alert emails via SES"
  role          = aws_iam_role.alerts_lambda.arn
  handler       = "handler.handler"
  runtime       = var.lambda_runtime
  timeout       = 60
  memory_size   = 128
  filename      = "${path.module}/../packages/alerts.zip"

  source_code_hash = filebase64sha256("${path.module}/../packages/alerts.zip")

  layers = [
    aws_lambda_layer_version.dependencies.arn,
    aws_lambda_layer_version.src.arn
  ]

  environment {
    variables = merge(local.lambda_env_vars, {
      SES_SENDER_EMAIL = var.admin_email
    })
  }

  tags = { Name = "${var.project_name}-alerts" }
}

# DynamoDB Streams → Alerts Lambda event source mapping
resource "aws_lambda_event_source_mapping" "prices_stream" {
  event_source_arn  = aws_dynamodb_table.prices.stream_arn
  function_name     = aws_lambda_function.alerts.arn
  starting_position = "LATEST"
  batch_size        = 10

  filter_criteria {
    filter {
      pattern = jsonencode({
        eventName = ["INSERT", "MODIFY"]
      })
    }
  }
}

# ============================================================================
# 7. Retrain Lambda
# ============================================================================
resource "aws_lambda_function" "retrain" {
  function_name = "${var.project_name}-${var.environment}-retrain"
  description   = "Retrains the price prediction model with latest data"
  role          = aws_iam_role.retrain_lambda.arn
  handler       = "handler.handler"
  runtime       = var.lambda_runtime
  timeout       = 900
  memory_size   = 1024
  filename      = "${path.module}/../packages/retrain.zip"

  source_code_hash = filebase64sha256("${path.module}/../packages/retrain.zip")

  layers = [
    aws_lambda_layer_version.dependencies.arn,
    aws_lambda_layer_version.src.arn
  ]

  environment {
    variables = local.lambda_env_vars
  }

  tags = { Name = "${var.project_name}-retrain" }
}

# ============================================================================
# 8. API Lambda
# ============================================================================
resource "aws_lambda_function" "api" {
  function_name = "${var.project_name}-${var.environment}-api"
  description   = "HTTP API handler for stations, prices, predictions, and subscriptions"
  role          = aws_iam_role.api_lambda.arn
  handler       = "handler.handler"
  runtime       = var.lambda_runtime
  timeout       = 30
  memory_size   = 256
  filename      = "${path.module}/../packages/api.zip"

  source_code_hash = filebase64sha256("${path.module}/../packages/api.zip")

  layers = [
    aws_lambda_layer_version.dependencies.arn,
    aws_lambda_layer_version.src.arn
  ]

  environment {
    variables = merge(local.lambda_env_vars, {
      COGNITO_USER_POOL_ID = aws_cognito_user_pool.main.id
    })
  }

  tags = { Name = "${var.project_name}-api" }
}
