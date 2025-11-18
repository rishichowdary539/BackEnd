# Lambda Function Trigger Flow

## How the Backend Cron Job Triggers Lambda

The backend cron job **does NOT use the API Gateway URL**. Instead, it uses the **AWS SDK (boto3)** to directly invoke the Lambda function.

## Complete Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│  FastAPI Application Starts                                  │
│  (app/main.py - lifespan function)                          │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  start_scheduler()                                           │
│  (app/utils/scheduler.py)                                    │
│                                                               │
│  - Creates APScheduler BackgroundScheduler                   │
│  - Configures cron job: "1st of month at 6:00 AM UTC"        │
│  - Registers: monthly_reports_job()                          │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ (Waits for scheduled time)
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  Cron Trigger Fires                                           │
│  (APScheduler executes at scheduled time)                   │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  monthly_reports_job()                                       │
│  (app/utils/scheduler.py)                                    │
│                                                               │
│  - Logs: "Executing monthly reports job..."                  │
│  - Calls: trigger_monthly_reports()                         │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  trigger_monthly_reports()                                   │
│  (app/utils/lambda_scheduler.py)                             │
│                                                               │
│  - Logs: "Triggering monthly reports at {timestamp}"        │
│  - Calls: invoke_lambda_function()                          │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  invoke_lambda_function()                                    │
│  (app/utils/lambda_scheduler.py)                             │
│                                                               │
│  Uses boto3 Lambda client:                                   │
│  lambda_client.invoke(                                       │
│      FunctionName="smart-expense-monthly-reports",          │
│      InvocationType="RequestResponse",  # Synchronous        │
│      Payload=json.dumps({})                                  │
│  )                                                           │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ AWS SDK Direct Invocation
                       │ (NOT through API Gateway)
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  AWS Lambda Function                                          │
│  (lambda/lambda_handler.py)                                  │
│                                                               │
│  - Processes all users                                       │
│  - Generates expense reports                                 │
│  - Uploads to S3                                             │
│  - Returns response                                          │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  Response returned to backend                                │
│  - Success/Error logged                                      │
│  - Job marked as complete                                    │
└─────────────────────────────────────────────────────────────┘
```

## Key Points

### 1. **Direct AWS SDK Invocation (NOT API Gateway)**

The backend uses **boto3 Lambda client** to directly invoke the Lambda function:

```python
# app/utils/lambda_scheduler.py
lambda_client = boto3.client("lambda", region_name=AWS_REGION)

response = lambda_client.invoke(
    FunctionName=LAMBDA_FUNCTION_NAME,
    InvocationType="RequestResponse",  # Synchronous
    Payload=json.dumps(payload).encode('utf-8')
)
```

**Why this approach?**
- ✅ More efficient (no API Gateway overhead)
- ✅ Lower latency (direct invocation)
- ✅ Better error handling (direct response)
- ✅ No API Gateway costs
- ✅ Works within AWS VPC (if needed)

### 2. **API Gateway is for External Access**

The API Gateway endpoint (`/lambda/reports`) is for:
- External services/webhooks
- Manual triggers from outside AWS
- Frontend applications
- Third-party integrations

**NOT used by:**
- Backend cron job (uses SDK)
- Internal services (use SDK)

### 3. **Two Different Invocation Methods**

| Method | Used By | How It Works |
|--------|---------|--------------|
| **AWS SDK (boto3)** | Backend cron job | Direct Lambda invocation via `lambda_client.invoke()` |
| **API Gateway** | External clients | HTTP POST → API Gateway → Lambda (AWS_PROXY) |

## Code Flow Details

### Step 1: Scheduler Initialization
```python
# app/main.py
@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()  # Called when FastAPI starts
    yield
    stop_scheduler()   # Called when FastAPI shuts down
```

### Step 2: Cron Job Setup
```python
# app/utils/scheduler.py
scheduler.add_job(
    monthly_reports_job,  # Function to execute
    trigger=CronTrigger(
        day=1,      # 1st of month
        hour=6,     # 6 AM
        minute=0    # 0 minutes
    ),
    id="monthly_expense_reports"
)
```

### Step 3: Lambda Invocation
```python
# app/utils/lambda_scheduler.py
def invoke_lambda_function(payload: Optional[dict] = None) -> dict:
    response = lambda_client.invoke(
        FunctionName=LAMBDA_FUNCTION_NAME,
        InvocationType="RequestResponse",
        Payload=json.dumps(payload).encode('utf-8')
    )
    # Process response...
```

## Configuration

### Environment Variables

```bash
# Lambda function name
LAMBDA_FUNCTION_NAME=smart-expense-monthly-reports

# AWS region
AWS_REGION=eu-west-1

# Cron schedule (day hour minute)
MONTHLY_REPORTS_CRON=1 6 0  # 1st of month at 6:00 AM UTC
```

### AWS Credentials Required

The backend EC2 instance needs AWS credentials to invoke Lambda:
- IAM Role attached to EC2 instance, OR
- AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables

**Required IAM Permissions:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "lambda:InvokeFunction"
      ],
      "Resource": "arn:aws:lambda:eu-west-1:*:function:smart-expense-monthly-reports"
    }
  ]
}
```

## Comparison: SDK vs API Gateway

### Backend Cron Job (SDK)
```python
# Direct invocation
lambda_client.invoke(FunctionName="...", ...)
```
- ✅ Fast, efficient
- ✅ Direct error handling
- ✅ No API Gateway dependency
- ✅ Lower cost
- ❌ Requires AWS credentials on EC2

### External Trigger (API Gateway)
```bash
curl -X POST https://{API_ID}.execute-api.eu-west-1.amazonaws.com/prod/lambda/reports
```
- ✅ Public access (no AWS credentials needed)
- ✅ HTTP-based (works from anywhere)
- ✅ Can add authentication/rate limiting
- ❌ Additional latency (API Gateway)
- ❌ API Gateway costs

## Summary

**The backend cron job triggers Lambda using:**
1. **APScheduler** → Runs cron job at scheduled time
2. **boto3 Lambda client** → Directly invokes Lambda function via AWS SDK
3. **NOT API Gateway** → API Gateway is only for external/public access

This is the standard pattern: internal services use SDK, external services use API Gateway.

