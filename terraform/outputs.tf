# ---------------------------------------------------------------------------
# Terraform Outputs
# ---------------------------------------------------------------------------

output "api_endpoint" {
  description = "HTTP API Gateway endpoint URL"
  value       = aws_apigatewayv2_api.main.api_endpoint
}

output "s3_bucket_name" {
  description = "Data lake S3 bucket name"
  value       = aws_s3_bucket.data_lake.bucket
}

output "cognito_user_pool_id" {
  description = "Cognito User Pool ID"
  value       = aws_cognito_user_pool.main.id
}

output "cognito_user_pool_client_id" {
  description = "Cognito User Pool Client ID for frontend"
  value       = aws_cognito_user_pool_client.web.id
}

output "dynamodb_tables" {
  description = "DynamoDB table names"
  value = {
    stations      = aws_dynamodb_table.stations.name
    prices        = aws_dynamodb_table.prices.name
    predictions   = aws_dynamodb_table.predictions.name
    subscriptions = aws_dynamodb_table.subscriptions.name
  }
}

output "sns_alerts_topic_arn" {
  description = "SNS topic ARN for admin alerts"
  value       = aws_sns_topic.admin_alerts.arn
}

output "sqs_dlq_url" {
  description = "Dead-Letter Queue URL for failed events"
  value       = aws_sqs_queue.pipeline_dlq.url
}
