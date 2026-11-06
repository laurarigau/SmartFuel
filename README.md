# SmartFuel — Cloud-Native Fuel Price Forecasting & Alerting

> **Project for Cloud Solutions Course**  
> **Team:** Carla Escassi, Marc Farràs, Laura Rigau, Marta Palet  
> **Target Architecture:** AWS Serverless (Lambda, Step Functions, DynamoDB, S3, EventBridge, API Gateway, Cognito, Amplify)  
> **Budget:** ~$50 (100% pay-per-use serverless)

---

## 📋 Overview

Fuel prices in Spain fluctuate significantly day-to-day and between neighboring stations. **SmartFuel** is an end-to-end, serverless system that:

1. **Ingests** open data 4 times daily from the Spanish Ministry for the Ecological Transition (11,400+ stations).
2. **Validates & Cleans** data snapshots and persists them to an S3 data lake.
3. **Detects price changes** between consecutive snapshots.
4. **Predicts short-term price trends** (whether prices will rise or drop/remain stable over the next 3 days).
5. **Notifies users** via Amazon SES when monitored stations drop below their target price or experience significant price reductions.
6. **Visualizes** national fuel stations and predictions through an interactive map interface.

---

## 🏛️ System Architecture

```text
                                 [ Ministry REST API ]
                                          │
                            EventBridge Schedule (4x/day)
                                          │
                                          ▼
                                 [ Lambda: Ingest ]
                                          │
                                          ▼
                                   [ S3: raw/ ]
                                          │
                                   EventBridge Rule
                                          │
                                          ▼
                      ┌───────────────────────────────────────┐
                      │    Step Functions: Processing Flow    │
                      │                                       │
                      │  1. Lambda: Validate                  │
                      │     ├── Valid? ──► Clean              │
                      │     └── Invalid? ──► S3 quarantine/   │
                      │                     + SNS Admin Alert │
                      │  2. Lambda: Clean                     │
                      │     ├── S3: clean/ (Parquet / CSV)    │
                      │     └── Detect Price Changes          │
                      │                                       │
                      │  3. Parallel Execution:               │
                      │     ├── Lambda: Save Prices (DynamoDB)│
                      │     └── Lambda: Predict (DynamoDB)    │
                      │                                       │
                      │  * Errors routed to SQS DLQ (14-day)  │
                      └──────────────────┬────────────────────┘
                                         │
                         DynamoDB Streams (on price insert)
                                         │
                                         ▼
                               [ Lambda: Alerts ]
                                         │
                                         ▼
                                [ SES Email Alerts ]
```

### Weekly Retraining Flow (Step Functions)
- **Athena** queries historical price trends in S3.
- **Lambda: Retrain** trains a new model, evaluates it against the current baseline ("price stays same").
- If the candidate model outperforms the baseline, it is promoted to production; otherwise, admins are notified via SNS.

---

## 📁 Repository Structure

```text
SmartFuel/
├── data/
│   ├── raw/                 # Raw JSON snapshots from Ministry API
│   ├── processed/           # Cleaned CSV datasets
│   ├── parquet/             # Columnar Parquet data lake
│   ├── models/              # Persisted ML model artefacts (.joblib / .pkl)
│   ├── quarantine/          # Failed validation payloads
│   └── subscriptions.json   # Local user alert subscriptions
├── frontend/                # Static Single-Page App (Amplify hosting)
│   ├── index.html           # Leaflet map, search, and detail drawers
│   ├── css/style.css        # Responsive styling
│   └── js/
│       ├── app.js           # Main application controller
│       ├── map.js           # Leaflet map + MarkerCluster integration
│       ├── charts.js        # 30-day price trend charts (Chart.js)
│       └── auth.js          # Authentication state & Cognito stub
├── lambdas/                 # AWS Lambda handlers (deployable packages)
│   ├── ingest/              # API data fetching
│   ├── validate/            # JSON schema & station count checks
│   ├── clean/               # Standardisation & change detection
│   ├── save_prices/         # DynamoDB batch writes
│   ├── predict/             # Inference against latest snapshot
│   ├── alerts/              # Stream-triggered email notifications
│   ├── retrain/             # Weekly Athena training & evaluation
│   └── api/                 # HTTP API Gateway route handlers
├── stepfunctions/           # Amazon State Language (ASL) JSON definitions
│   ├── processing_workflow.asl.json
│   └── retraining_workflow.asl.json
├── src/                     # Core reusable Python business logic
│   ├── pipeline/            # ingest.py, validate.py, clean.py, changes.py
│   ├── ml/                  # features.py, train.py, predict.py
│   ├── alerts/              # alerts.py
│   ├── api/                 # router.py
│   └── utils/               # config.py, logger.py
├── terraform/               # Complete Infrastructure as Code
│   ├── main.tf, providers.tf, variables.tf, outputs.tf
│   ├── s3.tf, dynamodb.tf, lambda.tf, iam.tf
│   ├── step_functions.tf, eventbridge.tf, api_gateway.tf
│   ├── cognito.tf, sns.tf, sqs.tf, ses.tf, cloudwatch.tf, amplify.tf
├── tests/                   # Automated unit test suite (unittest)
├── run_pipeline.py          # Local end-to-end pipeline orchestrator
└── requirements.txt         # Python project dependencies
```

---

## 🚀 Local Development & Testing

All business logic runs locally **without requiring AWS credentials or deployment**.

### 1. Run the Automated Test Suite

```bash
python3 -m unittest discover -s tests -p "test_*.py"
```

All 15 tests cover:
- Ingestion with mock API payloads
- Schema and station-count validation + quarantine routing
- Decimal conversions, geohash generation, and cleaning
- Price change detection and percentage calculation
- User target price and drop threshold alerts
- ML feature lag and rolling calculation

### 2. Run the Local Pipeline

```bash
# Full pipeline with real data from Spanish Ministry API:
python3 run_pipeline.py

# Skip ingestion (use existing local snapshot):
python3 run_pipeline.py --skip-ingest

# Run individual steps:
python3 run_pipeline.py --step ingest
python3 run_pipeline.py --step validate
python3 run_pipeline.py --step clean
python3 run_pipeline.py --step changes
python3 run_pipeline.py --step predict
python3 run_pipeline.py --step train
```

### 3. Preview the Frontend Map

Launch a local web server inside `frontend/`:

```bash
python3 -m http.server 8080 --directory frontend
```

Open [http://localhost:8080](http://localhost:8080) to explore the map with marker clustering, price cards, and prediction indicators.

---

## ☁️ AWS Deployment (When Ready)

The `terraform/` directory defines all required cloud resources for `eu-west-1`:

```bash
cd terraform
terraform init
terraform plan
terraform apply
```

Resources created:
- **S3 Data Lake:** Encrypted bucket with raw, clean, and model prefixes + Glacier lifecycle (90 days).
- **DynamoDB:** 4 on-demand tables (`stations`, `prices`, `predictions`, `subscriptions`) with geohash GSI and DynamoDB Streams enabled.
- **IAM:** Least-privilege roles per Lambda function.
- **Step Functions:** Main processing workflow + weekly retraining state machines.
- **EventBridge:** 4x/day cron + S3 object creation triggers.
- **API Gateway:** HTTP API with CORS, JWT authorizer, and throttling.
- **Cognito:** User Pool with email sign-up and JWT claims.
- **Monitoring:** CloudWatch alarms on Lambda errors and DLQ messages + SNS admin topic.
