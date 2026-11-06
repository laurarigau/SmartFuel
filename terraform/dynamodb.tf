# ============================================================================
# SmartFuel — DynamoDB Tables
# ============================================================================

# ---------------------------------------------------------------------------
# 1. Stations table
#    PK: station_id
#    GSI: geohash (PK) + station_id (SK) for geo queries
# ---------------------------------------------------------------------------
resource "aws_dynamodb_table" "stations" {
  name         = "${var.dynamodb_stations_table}-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "station_id"

  attribute {
    name = "station_id"
    type = "S"
  }

  attribute {
    name = "geohash"
    type = "S"
  }

  global_secondary_index {
    name            = "geohash-index"
    hash_key        = "geohash"
    range_key       = "station_id"
    projection_type = "ALL"
  }

  point_in_time_recovery {
    enabled = true
  }

  tags = {
    Name = "${var.project_name}-stations"
  }
}

# ---------------------------------------------------------------------------
# 2. Prices table
#    PK: station_id, SK: snapshot_date
#    GSI: snapshot_date (PK) for querying all prices on a given date
#    Streams enabled for alert triggering
# ---------------------------------------------------------------------------
resource "aws_dynamodb_table" "prices" {
  name         = "${var.dynamodb_prices_table}-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "station_id"
  range_key    = "snapshot_date"

  attribute {
    name = "station_id"
    type = "S"
  }

  attribute {
    name = "snapshot_date"
    type = "S"
  }

  global_secondary_index {
    name            = "snapshot-date-index"
    hash_key        = "snapshot_date"
    range_key       = "station_id"
    projection_type = "ALL"
  }

  stream_enabled   = true
  stream_view_type = "NEW_AND_OLD_IMAGES"

  point_in_time_recovery {
    enabled = true
  }

  tags = {
    Name = "${var.project_name}-prices"
  }
}

# ---------------------------------------------------------------------------
# 3. Predictions table
#    PK: station_id, SK: prediction_date
# ---------------------------------------------------------------------------
resource "aws_dynamodb_table" "predictions" {
  name         = "${var.dynamodb_predictions_table}-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "station_id"
  range_key    = "prediction_date"

  attribute {
    name = "station_id"
    type = "S"
  }

  attribute {
    name = "prediction_date"
    type = "S"
  }

  point_in_time_recovery {
    enabled = true
  }

  tags = {
    Name = "${var.project_name}-predictions"
  }
}

# ---------------------------------------------------------------------------
# 4. Subscriptions table
#    PK: user_id, SK: station_id#fuel_type
#    GSI: station_id (PK) for alert lookup by station
# ---------------------------------------------------------------------------
resource "aws_dynamodb_table" "subscriptions" {
  name         = "${var.dynamodb_subscriptions_table}-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "user_id"
  range_key    = "station_fuel"

  attribute {
    name = "user_id"
    type = "S"
  }

  attribute {
    name = "station_fuel"
    type = "S"
  }

  attribute {
    name = "station_id"
    type = "S"
  }

  global_secondary_index {
    name            = "station-id-index"
    hash_key        = "station_id"
    range_key       = "user_id"
    projection_type = "ALL"
  }

  point_in_time_recovery {
    enabled = true
  }

  tags = {
    Name = "${var.project_name}-subscriptions"
  }
}
