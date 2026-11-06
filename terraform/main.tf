# ============================================================================
# SmartFuel — Main Terraform Configuration
# ============================================================================
# Serverless fuel price forecasting and alerts system for Spain.
# Architecture: Lambda + Step Functions + DynamoDB + S3 + API Gateway +
#               Cognito + Amplify + EventBridge + SES + SNS + SQS
#
# This file contains the terraform block and data sources used by other files.
# All resources are defined in dedicated files (s3.tf, dynamodb.tf, etc.).
# ============================================================================

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Local backend for development.
  # Uncomment the S3 backend below for shared state in production.
  #
  # backend "s3" {
  #   bucket         = "smartfuel-terraform-state"
  #   key            = "state/terraform.tfstate"
  #   region         = "eu-west-1"
  #   dynamodb_table = "smartfuel-terraform-locks"
  #   encrypt        = true
  # }
}

# Current AWS account and region data sources
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# Common tags applied to every resource via default_tags in the provider
locals {
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }

  account_id = data.aws_caller_identity.current.account_id
  region     = data.aws_region.current.name
}
