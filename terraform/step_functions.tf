# ============================================================================
# SmartFuel — Step Functions State Machines
# ============================================================================

# ---------------------------------------------------------------------------
# 1. Processing Workflow
#    Triggered by new raw file in S3.
#    Validate → Clean → Parallel(SavePrices, Predict)
# ---------------------------------------------------------------------------
resource "aws_sfn_state_machine" "processing" {
  name     = "${var.project_name}-${var.environment}-processing-workflow"
  role_arn = aws_iam_role.step_functions.arn

  definition = templatefile("${path.module}/../stepfunctions/processing_workflow.asl.json", {
    validate_lambda_arn    = aws_lambda_function.validate.arn
    clean_lambda_arn       = aws_lambda_function.clean.arn
    save_prices_lambda_arn = aws_lambda_function.save_prices.arn
    predict_lambda_arn     = aws_lambda_function.predict.arn
    dlq_url                = aws_sqs_queue.dlq.url
    sns_topic_arn          = aws_sns_topic.admin_alerts.arn
  })

  logging_configuration {
    log_destination        = "${aws_cloudwatch_log_group.sfn_processing.arn}:*"
    include_execution_data = true
    level                  = "ERROR"
  }

  tags = {
    Name = "${var.project_name}-processing-workflow"
  }
}

resource "aws_cloudwatch_log_group" "sfn_processing" {
  name              = "/aws/states/${var.project_name}-${var.environment}-processing"
  retention_in_days = 14

  tags = {
    Name = "${var.project_name}-sfn-processing-logs"
  }
}

# ---------------------------------------------------------------------------
# 2. Retraining Workflow
#    Triggered weekly by EventBridge.
#    BuildTrainingData → TrainModel → EvaluateModel → Choice → Promote/Notify
# ---------------------------------------------------------------------------
resource "aws_sfn_state_machine" "retraining" {
  name     = "${var.project_name}-${var.environment}-retraining-workflow"
  role_arn = aws_iam_role.step_functions.arn

  definition = templatefile("${path.module}/../stepfunctions/retraining_workflow.asl.json", {
    retrain_lambda_arn = aws_lambda_function.retrain.arn
    sns_topic_arn      = aws_sns_topic.admin_alerts.arn
  })

  logging_configuration {
    log_destination        = "${aws_cloudwatch_log_group.sfn_retraining.arn}:*"
    include_execution_data = true
    level                  = "ERROR"
  }

  tags = {
    Name = "${var.project_name}-retraining-workflow"
  }
}

resource "aws_cloudwatch_log_group" "sfn_retraining" {
  name              = "/aws/states/${var.project_name}-${var.environment}-retraining"
  retention_in_days = 14

  tags = {
    Name = "${var.project_name}-sfn-retraining-logs"
  }
}
