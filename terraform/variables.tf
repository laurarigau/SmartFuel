# ============================================================================
# SmartFuel — Input Variables
# ============================================================================

# ---------------------------------------------------------------------------
# General
# ---------------------------------------------------------------------------
variable "project_name" {
  description = "Name prefix for all resources"
  type        = string
  default     = "smartfuel"
}

variable "environment" {
  description = "Deployment environment (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "eu-west-1"
}

# ---------------------------------------------------------------------------
# S3
# ---------------------------------------------------------------------------
variable "s3_bucket_name" {
  description = "Name of the S3 data-lake bucket"
  type        = string
  default     = "smartfuel-data"
}

# ---------------------------------------------------------------------------
# DynamoDB table names
# ---------------------------------------------------------------------------
variable "dynamodb_stations_table" {
  description = "DynamoDB table name for fuel stations"
  type        = string
  default     = "smartfuel-stations"
}

variable "dynamodb_prices_table" {
  description = "DynamoDB table name for price snapshots"
  type        = string
  default     = "smartfuel-prices"
}

variable "dynamodb_predictions_table" {
  description = "DynamoDB table name for price predictions"
  type        = string
  default     = "smartfuel-predictions"
}

variable "dynamodb_subscriptions_table" {
  description = "DynamoDB table name for user alert subscriptions"
  type        = string
  default     = "smartfuel-subscriptions"
}

# ---------------------------------------------------------------------------
# Lambda
# ---------------------------------------------------------------------------
variable "lambda_runtime" {
  description = "Python runtime version for all Lambda functions"
  type        = string
  default     = "python3.12"
}

variable "lambda_timeout" {
  description = "Default timeout in seconds for Lambda functions"
  type        = number
  default     = 120
}

variable "lambda_memory" {
  description = "Default memory in MB for Lambda functions"
  type        = number
  default     = 256
}

# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------
variable "admin_email" {
  description = "Email address for admin SNS notifications and SES sender"
  type        = string
}

# ---------------------------------------------------------------------------
# Cognito
# ---------------------------------------------------------------------------
variable "cognito_callback_urls" {
  description = "Allowed callback URLs for Cognito hosted UI"
  type        = list(string)
  default     = ["http://localhost:3000/callback"]
}

variable "cognito_logout_urls" {
  description = "Allowed logout URLs for Cognito hosted UI"
  type        = list(string)
  default     = ["http://localhost:3000/"]
}

# ---------------------------------------------------------------------------
# Amplify
# ---------------------------------------------------------------------------
variable "amplify_repository_url" {
  description = "Git repository URL for the Amplify frontend app"
  type        = string
  default     = "https://github.com/placeholder/smartfuel-frontend"
}

variable "amplify_branch" {
  description = "Git branch to deploy from"
  type        = string
  default     = "main"
}
