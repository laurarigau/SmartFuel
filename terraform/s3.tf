# ============================================================================
# SmartFuel — S3 Data Lake
# ============================================================================

resource "aws_s3_bucket" "data_lake" {
  bucket = "${var.s3_bucket_name}-${var.environment}-${local.account_id}"

  tags = {
    Name = "${var.project_name}-data-lake"
  }
}

# Versioning
resource "aws_s3_bucket_versioning" "data_lake" {
  bucket = aws_s3_bucket.data_lake.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Server-side encryption (AES-256)
resource "aws_s3_bucket_server_side_encryption_configuration" "data_lake" {
  bucket = aws_s3_bucket.data_lake.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

# Block all public access
resource "aws_s3_bucket_public_access_block" "data_lake" {
  bucket = aws_s3_bucket.data_lake.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Lifecycle: transition raw/ prefix to Glacier after 90 days
resource "aws_s3_bucket_lifecycle_configuration" "data_lake" {
  bucket = aws_s3_bucket.data_lake.id

  rule {
    id     = "archive-raw-data"
    status = "Enabled"

    filter {
      prefix = "raw/"
    }

    transition {
      days          = 90
      storage_class = "GLACIER"
    }
  }
}

# CORS configuration for frontend access
resource "aws_s3_bucket_cors_configuration" "data_lake" {
  bucket = aws_s3_bucket.data_lake.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "HEAD"]
    allowed_origins = ["*"]
    expose_headers  = ["ETag"]
    max_age_seconds = 3600
  }
}

# EventBridge notifications (for S3 → EventBridge → Step Functions)
resource "aws_s3_bucket_notification" "data_lake" {
  bucket      = aws_s3_bucket.data_lake.id
  eventbridge = true
}
